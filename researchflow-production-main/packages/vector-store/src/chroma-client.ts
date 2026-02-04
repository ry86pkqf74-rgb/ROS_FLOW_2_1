/**
 * ChromaDB Client for ResearchFlow RAG Pipeline
 * 
 * Provides persistent vector storage with collections for:
 * - research_papers: Published research and literature
 * - clinical_guidelines: CONSORT, TRIPOD, clinical standards
 * - irb_protocols: IRB templates and compliance documents
 * - statistical_methods: Statistical analysis references
 * 
 * @package @researchflow/vector-store
 * Linear Issue: ROS-81
 */

import { ChromaClient, Collection, IncludeEnum } from 'chromadb';
import type { DocumentMetadata, SearchResult, VectorDocument } from './types.js';
import { DocumentEmbedder } from './embedder.js';

export interface ChromaConfig {
  url: string;
  authToken?: string;
  tenant?: string;
  database?: string;
}

export type CollectionName = 
  | 'research_papers'
  | 'clinical_guidelines'
  | 'irb_protocols'
  | 'statistical_methods';

const COLLECTION_CONFIGS: Record<CollectionName, { description: string; metadata: Record<string, string> }> = {
  research_papers: {
    description: 'Published research papers, preprints, and literature for citation and synthesis',
    metadata: { domain: 'literature', version: '1.0' }
  },
  clinical_guidelines: {
    description: 'Clinical reporting guidelines including CONSORT, TRIPOD+AI, STROBE, PRISMA',
    metadata: { domain: 'compliance', version: '1.0' }
  },
  irb_protocols: {
    description: 'IRB protocol templates, consent forms, and regulatory compliance documents',
    metadata: { domain: 'regulatory', version: '1.0' }
  },
  statistical_methods: {
    description: 'Statistical analysis methods, formulas, and best practices references',
    metadata: { domain: 'methodology', version: '1.0' }
  }
};

export class ChromaVectorStore {
  private client: ChromaClient;
  private embedder: DocumentEmbedder;
  private collections: Map<CollectionName, Collection> = new Map();
  private initialized = false;

  constructor(config: ChromaConfig, embedder?: DocumentEmbedder) {
    this.client = new ChromaClient({
      path: config.url,
      auth: config.authToken ? {
        provider: 'token',
        credentials: config.authToken,
      } : undefined,
      tenant: config.tenant || 'default_tenant',
      database: config.database || 'default_database',
    });
    this.embedder = embedder || new DocumentEmbedder();
  }

  /**
   * Initialize all collections
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    console.log('[ChromaVectorStore] Initializing collections...');
    
    for (const [name, config] of Object.entries(COLLECTION_CONFIGS)) {
      try {
        const collection = await this.client.getOrCreateCollection({
          name,
          metadata: {
            ...config.metadata,
            description: config.description,
            created_at: new Date().toISOString(),
          },
        });
        this.collections.set(name as CollectionName, collection);
        console.log(`[ChromaVectorStore] Collection '${name}' ready`);
      } catch (error) {
        console.error(`[ChromaVectorStore] Failed to create collection '${name}':`, error);
        throw error;
      }
    }

    this.initialized = true;
    console.log('[ChromaVectorStore] All collections initialized');
  }

  /**
   * Get a specific collection
   */
  private getCollection(name: CollectionName): Collection {
    const collection = this.collections.get(name);
    if (!collection) {
      throw new Error(`Collection '${name}' not initialized. Call initialize() first.`);
    }
    return collection;
  }

  /**
   * Add a document to a collection
   */
  async addDocument(
    collectionName: CollectionName,
    doc: VectorDocument
  ): Promise<string> {
    const collection = this.getCollection(collectionName);
    const embedding = await this.embedder.embedSingle(doc.content);
    
    const id = doc.id || `${collectionName}_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    
    await collection.add({
      ids: [id],
      embeddings: [embedding],
      documents: [doc.content],
      metadatas: [{
        ...doc.metadata,
        indexed_at: new Date().toISOString(),
        content_hash: this.hashContent(doc.content),
      }],
    });

    return id;
  }

  /**
   * Add multiple documents in batch
   */
  async addDocuments(
    collectionName: CollectionName,
    docs: VectorDocument[]
  ): Promise<string[]> {
    if (docs.length === 0) return [];

    const collection = this.getCollection(collectionName);
    const contents = docs.map(d => d.content);
    const embeddings = await this.embedder.embed(contents);
    
    const ids = docs.map((doc, i) => 
      doc.id || `${collectionName}_${Date.now()}_${i}_${Math.random().toString(36).slice(2)}`
    );

    const metadatas = docs.map(doc => ({
      ...doc.metadata,
      indexed_at: new Date().toISOString(),
      content_hash: this.hashContent(doc.content),
    }));

    await collection.add({
      ids,
      embeddings,
      documents: contents,
      metadatas,
    });

    return ids;
  }

  /**
   * Search a collection with hybrid retrieval
   */
  async search(
    collectionName: CollectionName,
    query: string,
    options: {
      topK?: number;
      filter?: Record<string, string | number | boolean>;
      includeEmbeddings?: boolean;
    } = {}
  ): Promise<SearchResult[]> {
    const { topK = 10, filter, includeEmbeddings = false } = options;
    const collection = this.getCollection(collectionName);
    
    const queryEmbedding = await this.embedder.embedSingle(query);

    const include: IncludeEnum[] = ['documents', 'metadatas', 'distances'];
    if (includeEmbeddings) {
      include.push('embeddings');
    }

    const results = await collection.query({
      queryEmbeddings: [queryEmbedding],
      nResults: topK,
      where: filter as any,
      include,
    });

    if (!results.ids[0] || results.ids[0].length === 0) {
      return [];
    }

    return results.ids[0].map((id, i) => ({
      id,
      content: results.documents?.[0]?.[i] || '',
      metadata: (results.metadatas?.[0]?.[i] || {}) as DocumentMetadata,
      score: 1 - (results.distances?.[0]?.[i] || 0), // Convert distance to similarity
      embedding: results.embeddings?.[0]?.[i],
    }));
  }

  /**
   * Search across multiple collections
   */
  async searchMultiple(
    collectionNames: CollectionName[],
    query: string,
    options: { topK?: number; filter?: Record<string, string | number | boolean> } = {}
  ): Promise<Map<CollectionName, SearchResult[]>> {
    const results = new Map<CollectionName, SearchResult[]>();

    await Promise.all(
      collectionNames.map(async (name) => {
        const collectionResults = await this.search(name, query, options);
        results.set(name, collectionResults);
      })
    );

    return results;
  }

  /**
   * Get document by ID
   */
  async getDocument(
    collectionName: CollectionName,
    id: string
  ): Promise<VectorDocument | null> {
    const collection = this.getCollection(collectionName);
    
    const result = await collection.get({
      ids: [id],
      include: ['documents', 'metadatas'],
    });

    if (!result.ids[0]) {
      return null;
    }

    return {
      id: result.ids[0],
      content: result.documents?.[0] || '',
      metadata: (result.metadatas?.[0] || {}) as DocumentMetadata,
    };
  }

  /**
   * Delete document by ID
   */
  async deleteDocument(collectionName: CollectionName, id: string): Promise<void> {
    const collection = this.getCollection(collectionName);
    await collection.delete({ ids: [id] });
  }

  /**
   * Update document content
   */
  async updateDocument(
    collectionName: CollectionName,
    id: string,
    updates: { content?: string; metadata?: Partial<DocumentMetadata> }
  ): Promise<void> {
    const collection = this.getCollection(collectionName);
    const existing = await this.getDocument(collectionName, id);
    
    if (!existing) {
      throw new Error(`Document '${id}' not found in collection '${collectionName}'`);
    }

    const newContent = updates.content || existing.content;
    const newMetadata = { ...existing.metadata, ...updates.metadata };
    
    if (updates.content) {
      const embedding = await this.embedder.embedSingle(newContent);
      await collection.update({
        ids: [id],
        embeddings: [embedding],
        documents: [newContent],
        metadatas: [{
          ...newMetadata,
          updated_at: new Date().toISOString(),
          content_hash: this.hashContent(newContent),
        }],
      });
    } else {
      await collection.update({
        ids: [id],
        metadatas: [{
          ...newMetadata,
          updated_at: new Date().toISOString(),
        }],
      });
    }
  }

  /**
   * Get collection statistics
   */
  async getCollectionStats(collectionName: CollectionName): Promise<{
    name: string;
    count: number;
    metadata: Record<string, any>;
  }> {
    const collection = this.getCollection(collectionName);
    const count = await collection.count();
    
    return {
      name: collectionName,
      count,
      metadata: COLLECTION_CONFIGS[collectionName],
    };
  }

  /**
   * Get stats for all collections
   */
  async getAllStats(): Promise<Array<{ name: string; count: number; metadata: Record<string, any> }>> {
    const stats = await Promise.all(
      Array.from(this.collections.keys()).map(name => this.getCollectionStats(name))
    );
    return stats;
  }

  /**
   * Clear all documents from a collection
   */
  async clearCollection(collectionName: CollectionName): Promise<void> {
    const collection = this.getCollection(collectionName);
    // Get all IDs and delete them
    const allDocs = await collection.get();
    if (allDocs.ids.length > 0) {
      await collection.delete({ ids: allDocs.ids });
    }
  }

  /**
   * Simple content hash for deduplication
   */
  private hashContent(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString(16);
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ healthy: boolean; collections: number; error?: string }> {
    try {
      await this.client.heartbeat();
      return {
        healthy: true,
        collections: this.collections.size,
      };
    } catch (error) {
      return {
        healthy: false,
        collections: 0,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}

/**
 * Factory function for easy setup
 */
export async function createChromaVectorStore(
  config?: Partial<ChromaConfig>
): Promise<ChromaVectorStore> {
  const fullConfig: ChromaConfig = {
    url: config?.url || process.env.CHROMADB_URL || 'http://localhost:8000',
    authToken: config?.authToken || process.env.CHROMADB_AUTH_TOKEN,
    tenant: config?.tenant || 'default_tenant',
    database: config?.database || 'default_database',
  };

  const store = new ChromaVectorStore(fullConfig);
  await store.initialize();
  return store;
}

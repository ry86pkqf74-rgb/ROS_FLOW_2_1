/**
 * Hybrid Retriever for ResearchFlow RAG Pipeline
 * Combines semantic search with BM25 keyword matching
 * @package @researchflow/vector-store
 */

import type { SearchResult, VectorStoreConfig, DocumentMetadata } from './types.js';
import { DocumentEmbedder } from './embedder.js';

export interface RetrieverConfig {
  vectorStore: VectorStoreConfig;
  semanticWeight: number;  // 0-1, weight for semantic vs keyword
  topK: number;
}

const DEFAULT_RETRIEVER_CONFIG: RetrieverConfig = {
  vectorStore: { type: 'faiss', indexPath: './data/faiss_index' },
  semanticWeight: 0.7,
  topK: 10,
};

export class HybridRetriever {
  private embedder: DocumentEmbedder;
  private config: RetrieverConfig;
  private documents: Map<string, { content: string; metadata: DocumentMetadata }> = new Map();
  private embeddings: Map<string, number[]> = new Map();

  constructor(
    embedder: DocumentEmbedder,
    config: Partial<RetrieverConfig> = {}
  ) {
    this.embedder = embedder;
    this.config = { ...DEFAULT_RETRIEVER_CONFIG, ...config };
  }

  /**
   * Add document to the index
   */
  async addDocument(
    id: string,
    content: string,
    metadata: DocumentMetadata
  ): Promise<void> {
    const embedding = await this.embedder.embedSingle(content);
    this.documents.set(id, { content, metadata });
    this.embeddings.set(id, embedding);
  }

  /**
   * Add multiple documents in batch
   */
  async addDocuments(
    docs: Array<{ id: string; content: string; metadata: DocumentMetadata }>
  ): Promise<void> {
    const contents = docs.map(d => d.content);
    const embeddings = await this.embedder.embed(contents);
    
    docs.forEach((doc, i) => {
      this.documents.set(doc.id, { content: doc.content, metadata: doc.metadata });
      this.embeddings.set(doc.id, embeddings[i]);
    });
  }

  /**
   * Cosine similarity between two vectors
   */
  private cosineSimilarity(a: number[], b: number[]): number {
    let dotProduct = 0;
    let normA = 0;
    let normB = 0;
    
    for (let i = 0; i < a.length; i++) {
      dotProduct += a[i] * b[i];
      normA += a[i] * a[i];
      normB += b[i] * b[i];
    }
    
    return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
  }

  /**
   * BM25 keyword scoring
   */
  private bm25Score(query: string, document: string): number {
    const k1 = 1.5;
    const b = 0.75;
    const avgDocLength = 500;
    
    const queryTerms = query.toLowerCase().split(/\s+/);
    const docTerms = document.toLowerCase().split(/\s+/);
    const docLength = docTerms.length;
    
    let score = 0;
    const termFreq = new Map<string, number>();
    
    for (const term of docTerms) {
      termFreq.set(term, (termFreq.get(term) || 0) + 1);
    }
    
    for (const term of queryTerms) {
      const tf = termFreq.get(term) || 0;
      if (tf > 0) {
        const idf = Math.log((this.documents.size + 1) / (1 + 1));
        const tfNorm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (docLength / avgDocLength)));
        score += idf * tfNorm;
      }
    }
    
    return score;
  }

  /**
   * Hybrid search combining semantic and keyword
   */
  async search(
    query: string,
    options: { topK?: number; filter?: Partial<DocumentMetadata> } = {}
  ): Promise<SearchResult[]> {
    const { topK = this.config.topK, filter } = options;
    const { semanticWeight } = this.config;
    
    const queryEmbedding = await this.embedder.embedSingle(query);
    const scores: Array<{ id: string; score: number }> = [];
    
    for (const [id, embedding] of this.embeddings) {
      const doc = this.documents.get(id);
      if (!doc) continue;
      
      // Apply filter
      if (filter) {
        if (filter.docId && doc.metadata.docId !== filter.docId) continue;
        if (filter.source && doc.metadata.source !== filter.source) continue;
        if (filter.paperId && doc.metadata.paperId !== filter.paperId) continue;
      }
      
      const semanticScore = this.cosineSimilarity(queryEmbedding, embedding);
      const keywordScore = this.bm25Score(query, doc.content);
      
      // Normalize and combine scores
      const combinedScore = semanticWeight * semanticScore + (1 - semanticWeight) * (keywordScore / 10);
      
      scores.push({ id, score: combinedScore });
    }
    
    // Sort by score descending
    scores.sort((a, b) => b.score - a.score);
    
    // Return top K results
    return scores.slice(0, topK).map(({ id, score }) => {
      const doc = this.documents.get(id)!;
      return {
        id,
        score,
        content: doc.content,
        metadata: doc.metadata,
      };
    });
  }

  /**
   * Get document count
   */
  get size(): number {
    return this.documents.size;
  }
}

export default HybridRetriever;

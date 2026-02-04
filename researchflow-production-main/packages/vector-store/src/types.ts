/**
 * Vector Store Types for ResearchFlow RAG Pipeline
 * @package @researchflow/vector-store
 */

export interface VectorDocument {
  id: string;
  content: string;
  embedding?: number[];
  metadata: DocumentMetadata;
}

export interface DocumentMetadata {
  docId: string;
  chunkIndex: number;
  source: 'paper' | 'manifest' | 'guideline' | 'literature';
  paperId?: string;
  stage?: number;
  createdAt: Date;
}

export interface SearchResult {
  id: string;
  score: number;
  content: string;
  metadata: DocumentMetadata;
}

export interface EmbeddingConfig {
  model: string;
  dimensions: number;
  batchSize: number;
}

export interface VectorStoreConfig {
  type: 'faiss' | 'pinecone';
  indexPath?: string;        // For FAISS
  apiKey?: string;           // For Pinecone
  environment?: string;      // For Pinecone
  indexName?: string;        // For Pinecone
  namespace?: string;
}

export interface ChunkConfig {
  chunkSize: number;
  chunkOverlap: number;
  separators: string[];
}

export const DEFAULT_CHUNK_CONFIG: ChunkConfig = {
  chunkSize: 512,
  chunkOverlap: 50,
  separators: ['\n\n', '\n', '. ', ' '],
};

export const DEFAULT_EMBEDDING_CONFIG: EmbeddingConfig = {
  model: 'text-embedding-3-small',
  dimensions: 1536,
  batchSize: 100,
};

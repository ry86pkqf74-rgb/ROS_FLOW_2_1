/**
 * @researchflow/vector-store
 * Vector database integration for RAG pipelines
 *
 * Features:
 * - Document chunking and embedding
 * - Hybrid retrieval (semantic + BM25)
 * - FAISS local storage support
 * - Pinecone cloud integration
 * - ChromaDB integration with 4 research collections
 */

export { DocumentEmbedder } from './embedder.js';
export { HybridRetriever } from './retriever.js';
export {
  ChromaDBClient,
  createChromaClient,
  COLLECTION_NAMES,
  type CollectionName,
  type ChromaConfig,
  type DocumentPayload,
  type QueryResult,
} from './chroma-client.js';
export type {
  VectorDocument,
  DocumentMetadata,
  SearchResult,
  EmbeddingConfig,
  VectorStoreConfig,
  ChunkConfig,
} from './types.js';
export {
  DEFAULT_CHUNK_CONFIG,
  DEFAULT_EMBEDDING_CONFIG,
} from './types.js';

// Factory function for easy setup
import { DocumentEmbedder } from './embedder.js';
import { HybridRetriever, RetrieverConfig } from './retriever.js';

export function createVectorStore(config?: Partial<RetrieverConfig>) {
  const embedder = new DocumentEmbedder();
  const retriever = new HybridRetriever(embedder, config);
  return { embedder, retriever };
}

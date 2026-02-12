import { ChromaVectorStore, DocumentEmbedder, type SearchResult, type CollectionName } from '@researchflow/vector-store';

export interface RagContextItem {
  id: string;
  score: number;
  content: string;
  metadata: Record<string, unknown>;
}

export class PhaseRagService {
  private store: ChromaVectorStore | null = null;
  private ready = false;

  constructor() {
    const chromaUrl = process.env.CHROMA_URL || process.env.PHASE_RAG_CHROMA_URL;
    const openAiKey = process.env.OPENAI_API_KEY;

    // Only initialize if both pieces are available; otherwise fall back gracefully.
    if (chromaUrl && openAiKey) {
      const embedder = new DocumentEmbedder();
      this.store = new ChromaVectorStore({ url: chromaUrl }, embedder);
    }
  }

  /**
   * Initialize vector store lazily to avoid startup penalties.
   */
  async ensureReady() {
    if (this.ready || !this.store) return;
    try {
      await this.store.initialize();
      this.ready = true;
    } catch (error) {
      console.warn('[PhaseRagService] Vector store unavailable, continuing without RAG:', error);
      this.store = null;
    }
  }

  /**
   * Retrieve contextual passages for a phase query.
   */
  async retrieve(
    collection: string | undefined,
    query: string,
    options: { topK?: number } = {}
  ): Promise<RagContextItem[]> {
    if (!collection || !this.store) {
      return [];
    }

    await this.ensureReady();
    if (!this.store) return [];

    try {
      const results: SearchResult[] = await this.store.search(collection as CollectionName, query, {
        topK: options.topK ?? 5,
      });

      return results.map((r) => ({
        id: r.id || '',
        score: r.score ?? 0,
        content: r.content || '',
        metadata: r.metadata || {},
      }));
    } catch (error) {
      console.warn('[PhaseRagService] Retrieval failed, falling back to empty context:', error);
      return [];
    }
  }
}

export const phaseRagService = new PhaseRagService();

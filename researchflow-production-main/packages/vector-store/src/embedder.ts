/**
 * Document Embedder for ResearchFlow RAG Pipeline
 * Supports OpenAI and local sentence-transformers
 * @package @researchflow/vector-store
 */

import OpenAI from 'openai';

import type { EmbeddingConfig, ChunkConfig } from './types.js';
import { DEFAULT_CHUNK_CONFIG, DEFAULT_EMBEDDING_CONFIG } from './types.js';

export class DocumentEmbedder {
  private openai: OpenAI | null = null;
  private config: EmbeddingConfig;
  private chunkConfig: ChunkConfig;

  constructor(
    config: Partial<EmbeddingConfig> = {},
    chunkConfig: Partial<ChunkConfig> = {}
  ) {
    this.config = { ...DEFAULT_EMBEDDING_CONFIG, ...config };
    this.chunkConfig = { ...DEFAULT_CHUNK_CONFIG, ...chunkConfig };
    
    if (process.env.OPENAI_API_KEY) {
      this.openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
    }
  }

  /**
   * Split text into chunks for embedding
   */
  splitText(text: string): string[] {
    const { chunkSize, chunkOverlap, separators } = this.chunkConfig;
    const chunks: string[] = [];
    
    let currentChunk = '';
    const sentences = text.split(/(?<=[.!?])\s+/);
    
    for (const sentence of sentences) {
      if ((currentChunk + sentence).length > chunkSize && currentChunk) {
        chunks.push(currentChunk.trim());
        // Keep overlap
        const words = currentChunk.split(' ');
        const overlapWords = words.slice(-Math.floor(chunkOverlap / 5));
        currentChunk = overlapWords.join(' ') + ' ' + sentence;
      } else {
        currentChunk += (currentChunk ? ' ' : '') + sentence;
      }
    }
    
    if (currentChunk.trim()) {
      chunks.push(currentChunk.trim());
    }
    
    return chunks;
  }

  /**
   * Generate embeddings using OpenAI API
   */
  async embed(texts: string[]): Promise<number[][]> {
    if (!this.openai) {
      throw new Error('OpenAI client not initialized. Set OPENAI_API_KEY.');
    }

    const embeddings: number[][] = [];
    const { batchSize, model } = this.config;

    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      
      const response = await this.openai.embeddings.create({
        model,
        input: batch,
      });

      for (const item of response.data) {
        embeddings.push(item.embedding);
      }
    }

    return embeddings;
  }

  /**
   * Embed a single text
   */
  async embedSingle(text: string): Promise<number[]> {
    const [embedding] = await this.embed([text]);
    return embedding;
  }

  /**
   * Process a document: split and embed
   */
  async processDocument(
    docId: string,
    content: string,
    source: 'paper' | 'manifest' | 'guideline' | 'literature'
  ): Promise<{ chunks: string[]; embeddings: number[][] }> {
    const chunks = this.splitText(content);
    const embeddings = await this.embed(chunks);
    
    return { chunks, embeddings };
  }

  get dimensions(): number {
    return this.config.dimensions;
  }
}

export default DocumentEmbedder;

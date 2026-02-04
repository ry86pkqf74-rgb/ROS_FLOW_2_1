# ResearchFlow: RAG Pipeline Implementation Guide
## Phase 10: Retrieval Augmented Generation Architecture

**Last Updated**: 2026-01-30
**Version**: 1.0
**Package**: @researchflow/vector-store

---

## Table of Contents

1. [RAG Architecture Overview](#rag-architecture-overview)
2. [HybridRetriever Setup](#hybridretriever-setup)
3. [Embedding Configuration](#embedding-configuration)
4. [Vector Store Options](#vector-store-options)
5. [Query Optimization](#query-optimization)
6. [Integration Examples](#integration-examples)

---

## RAG Architecture Overview

ResearchFlow's RAG pipeline combines semantic search with keyword matching (BM25) for robust document retrieval. This hybrid approach improves recall and relevance over pure semantic search.

**Architecture Diagram**:

```
Query Input
    ↓
Document Embedding (OpenAI API)
    ↓
Hybrid Retriever
├── Semantic Search (Cosine Similarity)
│   ↓
│   Vector Store (FAISS/Pinecone)
│   ↓
│   Top-K by Similarity Score
│
└── Keyword Search (BM25)
    ↓
    Full-text Matching
    ↓
    Top-K by BM25 Score
    ↓
Result Fusion
└── Score Combination
    └── Confidence-weighted Results
```

### Key Components

**1. DocumentEmbedder**
- Splits documents into chunks with overlap
- Generates embeddings using OpenAI or local models
- Batch processing for efficiency

**2. HybridRetriever**
- Combines semantic and keyword search
- Configurable weighting between methods
- Similarity scoring (cosine, BM25)

**3. Vector Store**
- FAISS: Local, fast, all-in-memory
- Pinecone: Cloud-native, scalable

---

## HybridRetriever Setup

### Basic Initialization

```typescript
import { HybridRetriever, DocumentEmbedder } from '@researchflow/vector-store';

// Initialize embedder
const embedder = new DocumentEmbedder({
  model: 'text-embedding-3-small',
  dimensions: 1536,
  batchSize: 100
});

// Create hybrid retriever with semantic weighting
const retriever = new HybridRetriever(embedder, {
  vectorStore: {
    type: 'faiss',
    indexPath: './data/faiss_index'
  },
  semanticWeight: 0.7,  // 70% semantic, 30% keyword
  topK: 10
});
```

### Adding Documents

**Single Document**:
```typescript
await retriever.addDocument(
  'doc-1',
  'Content of the research paper...',
  {
    docId: 'arxiv-2024-12345',
    chunkIndex: 0,
    source: 'paper',
    paperId: 'arxiv-2024-12345',
    stage: 1,
    createdAt: new Date()
  }
);
```

**Batch Processing**:
```typescript
const documents = [
  {
    id: 'doc-1',
    content: 'Methods section content...',
    metadata: {
      docId: 'paper-1',
      chunkIndex: 0,
      source: 'paper',
      paperId: 'paper-1',
      stage: 1,
      createdAt: new Date()
    }
  },
  {
    id: 'doc-2',
    content: 'Results section content...',
    metadata: {
      docId: 'paper-1',
      chunkIndex: 1,
      source: 'paper',
      paperId: 'paper-1',
      stage: 1,
      createdAt: new Date()
    }
  }
];

await retriever.addDocuments(documents);
```

### Searching

**Basic Search**:
```typescript
const results = await retriever.search('What methods were used?');

// Results
[
  {
    id: 'doc-1',
    score: 0.92,
    content: 'The study employed a randomized controlled...',
    metadata: { ... }
  },
  {
    id: 'doc-2',
    score: 0.87,
    content: 'Participants were recruited from...',
    metadata: { ... }
  }
]
```

**Advanced Search with Filtering**:
```typescript
const results = await retriever.search('statistical analysis', {
  filters: {
    source: 'paper',
    minConfidence: 0.8
  },
  limit: 5
});
```

---

## Embedding Configuration

### DocumentEmbedder Options

```typescript
interface EmbeddingConfig {
  model: string;        // 'text-embedding-3-small' | 'text-embedding-3-large'
  dimensions: number;   // 1536 (small) or 3072 (large)
  batchSize: number;    // Process N documents at once
}

const config: EmbeddingConfig = {
  model: 'text-embedding-3-small',  // Fast and cost-effective
  dimensions: 1536,
  batchSize: 100
};

const embedder = new DocumentEmbedder(config);
```

### Text Chunking Strategy

```typescript
interface ChunkConfig {
  chunkSize: number;        // Characters per chunk
  chunkOverlap: number;     // Overlap for context preservation
  separators: string[];     // Split points (paragraph, sentence, word)
}

const chunkConfig: ChunkConfig = {
  chunkSize: 512,           // 512 characters per chunk
  chunkOverlap: 50,         // 50 char overlap between chunks
  separators: ['\n\n', '\n', '. ', ' ']  // Try harder breaks first
};

const embedder = new DocumentEmbedder({}, chunkConfig);
```

### Processing Pipeline

```typescript
// Process a full document
async function processResearchPaper(paperId: string, content: string) {
  const embedder = new DocumentEmbedder(
    { model: 'text-embedding-3-small', dimensions: 1536, batchSize: 100 },
    { chunkSize: 512, chunkOverlap: 50, separators: ['\n\n', '\n', '. '] }
  );
  
  const { chunks, embeddings } = await embedder.processDocument(
    paperId,
    content,
    'paper'
  );
  
  console.log(`Generated ${chunks.length} chunks with embeddings`);
  
  // Add to retriever
  for (let i = 0; i < chunks.length; i++) {
    await retriever.addDocument(
      `${paperId}-chunk-${i}`,
      chunks[i],
      {
        docId: paperId,
        chunkIndex: i,
        source: 'paper',
        paperId,
        stage: 1,
        createdAt: new Date()
      }
    );
  }
}
```

---

## Vector Store Options

### Option 1: FAISS (Local)

**Advantages**:
- No external dependencies
- Instant search
- Free (open source)
- All data stays local

**Disadvantages**:
- Limited to single machine
- No persistence by default
- Memory constrained

**Configuration**:
```typescript
const config = {
  type: 'faiss' as const,
  indexPath: './data/faiss_index'  // Local file path
};

const retriever = new HybridRetriever(embedder, {
  vectorStore: config,
  semanticWeight: 0.7,
  topK: 10
});
```

**Production Setup**:
```typescript
// Initialize with FAISS
const faissRetriever = new HybridRetriever(embedder, {
  vectorStore: {
    type: 'faiss',
    indexPath: process.env.FAISS_INDEX_PATH || './data/faiss_index'
  },
  semanticWeight: 0.7,
  topK: 10
});

// Periodic persistence
setInterval(async () => {
  await faissRetriever.save();
  console.log('FAISS index saved');
}, 60000);  // Every minute
```

### Option 2: Pinecone (Cloud)

**Advantages**:
- Fully managed service
- Automatic scaling
- Multi-user support
- Built-in filtering

**Disadvantages**:
- Monthly costs
- Network latency
- External dependency

**Configuration**:
```typescript
const config = {
  type: 'pinecone' as const,
  apiKey: process.env.PINECONE_API_KEY,
  environment: 'us-west-1',
  indexName: 'researchflow-papers',
  namespace: 'production'
};

const retriever = new HybridRetriever(embedder, {
  vectorStore: config,
  semanticWeight: 0.7,
  topK: 10
});
```

**Production Setup**:
```typescript
// Initialize with Pinecone
const pineconeRetriever = new HybridRetriever(embedder, {
  vectorStore: {
    type: 'pinecone',
    apiKey: process.env.PINECONE_API_KEY,
    environment: process.env.PINECONE_ENV,
    indexName: 'researchflow-papers',
    namespace: process.env.PINECONE_NAMESPACE
  },
  semanticWeight: 0.7,
  topK: 10
});

// Health check
async function healthCheck() {
  const indexStats = await pineconeRetriever.getIndexStats();
  console.log(`Total vectors: ${indexStats.totalCount}`);
  console.log(`Vector dimension: ${indexStats.dimension}`);
}
```

### Comparison Table

| Feature | FAISS | Pinecone |
|---------|-------|----------|
| Cost | Free | $0.70/1M vectors/month |
| Latency | <10ms | 50-200ms |
| Scaling | Manual (limited) | Automatic |
| Persistence | Manual | Automatic |
| Filtering | Basic | Advanced |
| Multi-tenancy | Manual | Native |
| Setup Complexity | Simple | Moderate |

---

## Query Optimization

### Semantic Weight Tuning

```typescript
// More semantic-focused (better for conceptual queries)
const semanticHeavy = new HybridRetriever(embedder, {
  vectorStore: config,
  semanticWeight: 0.85,  // 85% semantic, 15% keyword
  topK: 10
});

// Balanced (good default)
const balanced = new HybridRetriever(embedder, {
  vectorStore: config,
  semanticWeight: 0.7,   // 70% semantic, 30% keyword
  topK: 10
});

// Keyword-focused (exact match important)
const keywordHeavy = new HybridRetriever(embedder, {
  vectorStore: config,
  semanticWeight: 0.5,   // 50% semantic, 50% keyword
  topK: 10
});
```

### Query Preprocessing

```typescript
async function optimizedSearch(query: string, context?: string) {
  // Expand query with context if provided
  let expandedQuery = query;
  if (context) {
    expandedQuery = `${context}\n\nQuestion: ${query}`;
  }
  
  // Add boost keywords
  if (query.includes('methodology')) {
    expandedQuery += ' methods techniques procedures';
  }
  
  // Search with expanded query
  const results = await retriever.search(expandedQuery, {
    limit: 10
  });
  
  // Filter by confidence
  return results.filter(r => r.score > 0.7);
}
```

### Caching Strategy

```typescript
import NodeCache from 'node-cache';

const queryCache = new NodeCache({ stdTTL: 3600 });  // 1 hour TTL

async function cachedSearch(query: string) {
  const cacheKey = `query:${query}`;
  
  // Check cache first
  const cached = queryCache.get(cacheKey);
  if (cached) {
    console.log('Cache hit');
    return cached;
  }
  
  // Execute search
  const results = await retriever.search(query);
  
  // Cache results
  queryCache.set(cacheKey, results);
  
  return results;
}
```

### Batch Retrieval

```typescript
async function batchRetrieve(queries: string[]) {
  // Retrieve in parallel
  const results = await Promise.all(
    queries.map(q => retriever.search(q, { limit: 5 }))
  );
  
  // Deduplicate across results
  const seen = new Set();
  const deduplicated = [];
  
  for (const resultSet of results) {
    for (const result of resultSet) {
      if (!seen.has(result.id)) {
        seen.add(result.id);
        deduplicated.push(result);
      }
    }
  }
  
  return deduplicated.sort((a, b) => b.score - a.score);
}
```

---

## Integration Examples

### Example 1: Document Ingestion Pipeline

```typescript
async function ingestPapers(paperIds: string[]) {
  const embedder = new DocumentEmbedder({
    model: 'text-embedding-3-small',
    dimensions: 1536,
    batchSize: 50
  });
  
  const retriever = new HybridRetriever(embedder, {
    vectorStore: { type: 'faiss', indexPath: './data/faiss_index' },
    semanticWeight: 0.7,
    topK: 10
  });
  
  for (const paperId of paperIds) {
    // Fetch paper content
    const paper = await fetchPaper(paperId);
    
    // Process and embed
    const { chunks, embeddings } = await embedder.processDocument(
      paperId,
      paper.content,
      'paper'
    );
    
    // Add to vector store
    for (let i = 0; i < chunks.length; i++) {
      await retriever.addDocument(
        `${paperId}-${i}`,
        chunks[i],
        {
          docId: paperId,
          chunkIndex: i,
          source: 'paper',
          paperId,
          stage: 1,
          createdAt: new Date()
        }
      );
    }
    
    console.log(`Ingested ${paperId}: ${chunks.length} chunks`);
  }
}
```

### Example 2: Semantic Search with Reranking

```typescript
async function semanticSearchWithRerank(query: string) {
  // Initial retrieval
  const candidates = await retriever.search(query, { limit: 20 });
  
  // Rerank with Claude
  const reranked = await claudeClient.messages.create({
    model: 'claude-opus-4-5-20251101',
    max_tokens: 500,
    messages: [{
      role: 'user',
      content: `Rank these documents by relevance to: "${query}"\n\n` +
        candidates.map((c, i) => `${i+1}. ${c.content}`).join('\n')
    }]
  });
  
  // Apply reranking
  const rankedIds = parseRanking(reranked.content[0].text);
  return rankedIds.map(id => candidates.find(c => c.id === id));
}
```

### Example 3: Multi-Modal RAG

```typescript
async function multiModalRAG(query: string, imageUrl?: string) {
  let queryText = query;
  
  // If image provided, describe it first
  if (imageUrl) {
    const description = await describeImage(imageUrl);
    queryText = `${query}\n\nRelated image: ${description}`;
  }
  
  // Perform retrieval
  const results = await retriever.search(queryText, { limit: 5 });
  
  return results;
}
```

---

## Performance Considerations

### Embedding Costs

```
OpenAI Pricing:
- text-embedding-3-small: $0.02 per 1M tokens
- text-embedding-3-large: $0.13 per 1M tokens

Example costs:
- 1,000 documents × 500 tokens = 500K tokens
- Small model: $0.01
- Large model: $0.065
```

### Search Latency

```
Typical latencies:
- FAISS: 5-50ms (depends on dataset size)
- Pinecone: 100-500ms (network + processing)
- Embedding: 100-2000ms (depends on query length)
```

### Memory Usage

```
FAISS in-memory:
- Vector count × dimensions × 4 bytes
- 100K vectors × 1536 dims = ~600 MB
- 1M vectors × 1536 dims = ~6 GB
```

---

## Troubleshooting

### Low Retrieval Quality

1. Increase `semanticWeight` for better semantic matching
2. Adjust `chunkSize` and `chunkOverlap`
3. Use larger embedding model (`text-embedding-3-large`)
4. Implement query expansion/preprocessing

### Slow Searches

1. Reduce `topK` value
2. Use FAISS instead of Pinecone
3. Implement caching for common queries
4. Batch process multiple queries

### Memory Issues

1. Reduce `chunkSize` to create more, smaller chunks
2. Switch to Pinecone for cloud-based storage
3. Implement periodic cleanup/archival
4. Use smaller embedding model

---

*Documentation Version: 1.0 | Phase 10 Deliverable*

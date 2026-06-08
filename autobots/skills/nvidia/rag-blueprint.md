# NVIDIA RAG Blueprint

## Architecture Components
```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Ingestion   │────▶│   VectorDB    │────▶│  Retrieval   │
│  Pipeline    │     │  (Milvus)     │     │  Service     │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                     │
       ▼                   ▼                     ▼
  ┌─────────┐       ┌───────────┐         ┌───────────┐
  │ Embedding│       │  Index    │         │  Reranker  │
  │ Model    │       │  Manager  │         │  Service   │
  └─────────┘       └───────────┘         └───────────┘
```

## Ingestion Pipeline
```python
# Document chunking and embedding
from nemollm import EmbeddingModel

def ingest_document(doc_path: str, chunk_size: int = 512):
    text = load_document(doc_path)
    chunks = chunk_text(text, chunk_size)
    embeddings = EmbeddingModel.embed(chunks)
    store.insert(chunks, embeddings)
```

## Retrieval Flow
```python
def retrieve(query: str, top_k: int = 5):
    query_embedding = EmbeddingModel.embed([query])
    candidates = vector_db.search(query_embedding, top_k * 2)
    reranked = reranker.rerank(query, candidates)
    return reranked[:top_k]
```

## Key Configuration
- **Embedding Model**: `nvidia/nv-embedqa-e5-v5` or `nvidia/nv-embed-v1`
- **Vector DB**: Milvus (GPU-accelerated) or Qdrant
- **Chunk Size**: 512 tokens (adjust for document type)
- **Overlap**: 50 tokens for context continuity
- **Reranker**: `nvidia/nv-rerankqa-mistral-4b-v3`

## Quality Metrics
- **Recall@k**: Percentage of relevant docs in top-k results
- **MRR**: Mean Reciprocal Rank of first relevant result
- **Faithfulness**: RAGAS score for answer groundedness

# RAG Evaluation Framework

## RAGAS Metrics
```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

# Evaluation dataset format
eval_dataset = {
    "question": ["What is X?", "How does Y work?"],
    "answer": ["X is...", "Y works by..."],
    "contexts": [["context1", "context2"], ["context3"]],
    "ground_truth": ["Expected answer 1", "Expected answer 2"],
}

results = evaluate(eval_dataset, metrics=[
    faithfulness,      # Is answer grounded in context?
    answer_relevancy,  # Does answer address the question?
    context_precision,# Are retrieved contexts relevant?
    context_recall,   # Are all relevant contexts retrieved?
])
```

## Corpus Layout
```
corpus/
├── train.json          # Training/evaluation pairs
├── documents/          # Source documents
│   ├── doc1.txt
│   └── doc2.pdf
├── chunks/             # Pre-chunked text
│   └── chunks.jsonl
└── eval_results/       # Evaluation outputs
    └── baseline.json
```

## Test Categories
1. **Retrieval Quality**: Precision, recall, MRR of retrieved chunks
2. **Generation Quality**: Faithfulness, relevancy, coherence
3. **End-to-End**: Answer correctness vs ground truth
4. **Performance**: Latency, throughput, cost per query

## Benchmark Harness
```python
def run_benchmark(rag_pipeline, eval_dataset, metrics):
    results = []
    for item in eval_dataset:
        answer = rag_pipeline.query(item["question"])
        scores = compute_metrics(answer, item)
        results.append(scores)
    return aggregate_results(results)
```

# Dynamo Router Configuration

## Routing Modes

### Round-Robin
```python
def round_robin_route(request, backends):
    return backends[next_index % len(backends)]
```

### KV-Aware Routing
```python
def kv_aware_route(request, backends):
    # Route to backend with most matching KV cache
    query_prefix = extract_prefix(request)
    scores = [backend.kv_match_score(query_prefix) for backend in backends]
    return backends[scores.index(max(scores))]
```

### Least-Loaded
```python
def least_loaded_route(request, backends):
    return min(backends, key=lambda b: b.current_load)
```

### Device-Aware
```python
def device_aware_route(request, backends):
    # Prefer same device type as previous request
    device_type = request.context.get("device_type", "gpu")
    compatible = [b for b in backends if b.device_type == device_type]
    return least_loaded_route(request, compatible or backends)
```

## Router Configuration
```json
{
  "routing_strategy": "kv-aware",
  "health_check_interval": 10,
  "max_retries": 3,
  "timeout_seconds": 30,
  "fallback_strategy": "round-robin"
}
```

## Load Balancing Metrics
- **Queue Depth**: Number of pending requests per backend
- **GPU Utilization**: Current GPU memory/compute usage
- **KV Cache Hit Rate**: Cache efficiency for context reuse
- **Latency P99**: Tail latency for SLA compliance

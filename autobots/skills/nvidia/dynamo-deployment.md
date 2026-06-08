# NVIDIA Dynamo Deployment Recipes

## Recipe Structure
```yaml
# recipe.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <service-name>
spec:
  replicas: <count>
  template:
    spec:
      containers:
      - name: <container>
        image: <nvidia-image>
        resources:
          limits:
            nvidia.com/gpu: <gpu-count>
```

## Model Backend Configuration
```python
# Backend selection based on model size
BACKEND_CONFIGS = {
    "small": {"backend": "vllm", "tensor_parallel": 1},
    "medium": {"backend": "vllm", "tensor_parallel": 2},
    "large": {"backend": "triton", "tensor_parallel": 4},
    "xlarge": {"backend": "triton", "tensor_parallel": 8},
}
```

## Deployment Modes
- **Single GPU**: Model fits on one GPU, no distribution
- **Tensor Parallel**: Model split across GPUs on one node
- **Pipeline Parallel**: Model split across nodes
- **Expert Parallel**: Mixture-of-experts distribution

## Health Checks
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 5
```

## Scaling Rules
- **GPU Memory**: Scale when utilization > 85%
- **Queue Depth**: Scale when pending requests > 100
- **Latency**: Scale when p99 > target latency

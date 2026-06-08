# Physical AI Infrastructure Setup

## MicroK8s Quick Start
```bash
# Install MicroK8s
sudo snap install microk8s --classic
sudo usermod -aG microk8s $USER
microk8s status --wait-ready

# Enable addons
microk8s enable dns
microk8s enable storage
microk8s enable gpu
```

## GPU Node Configuration
```yaml
# gpu-node.yaml
apiVersion: v1
kind: Node
metadata:
  labels:
    nvidia.com/gpu.present: "true"
    nvidia.com/gpu.product: "NVIDIA-A100-SXM4-80GB"
spec:
  taints:
  - key: nvidia.com/gpu
    effect: NoSchedule
```

## Inference Deployment
```yaml
# inference-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nim-inference
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nim-inference
  template:
    spec:
      containers:
      - name: nim
        image: nvcr.io/nvidia/nim:latest
        resources:
          limits:
            nvidia.com/gpu: 1
        ports:
        - containerPort: 8080
        env:
        - name: NIM_MODEL
          value: "nvidia/nemotron-4-340b-instruct"
```

## OSMO Workflow
```python
from osmo import Workflow, Step

workflow = Workflow(
    name="training-pipeline",
    steps=[
        Step(name="curate", image="nemo-curator"),
        Step(name="train", image="nemo-training"),
        Step(name="evaluate", image="nemo-eval"),
        Step(name="deploy", image="nim-deploy"),
    ],
    dependencies=[
        ("curate", "train"),
        ("train", "evaluate"),
        ("evaluate", "deploy"),
    ],
)
```

## Scaling Rules
- **Horizontal**: Add GPU nodes when queue depth > 100
- **Vertical**: Upgrade GPU type when memory > 90%
- **Cluster**: Add nodes when utilization > 80% sustained

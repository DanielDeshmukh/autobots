# NeMo Automodel Training Recipes

## Recipe Structure
```yaml
# recipe.yaml
model:
  name: nemotron-4
  architecture: transformer
  hidden_size: 4096
  num_layers: 32
  num_heads: 32

training:
  max_epochs: 10
  learning_rate: 1e-4
  batch_size: 32
  gradient_accumulation_steps: 4
  warmup_steps: 1000
  weight_decay: 0.01

distributed:
  strategy: fsdp2
  tensor_parallel_size: 2
  pipeline_parallel_size: 1
  data_parallel_size: 4
```

## Distributed Strategies

### FSDP2 (Fully Sharded Data Parallel)
```yaml
distributed:
  strategy: fsdp2
  sharding_factor: 8
  activation_checkpointing: true
```

### Megatron FSDP
```yaml
distributed:
  strategy: megatron-fsdp
  tensor_parallel_size: 4
  pipeline_parallel_size: 2
  sequence_parallel: true
```

### DDP (Data Distributed Parallel)
```yaml
distributed:
  strategy: ddp
  sync_batch_norm: true
```

## Launch Command
```bash
# Single node
python -m torch.distributed.launch --nproc_per_node=4 train.py

# Multi node
python -m torch.distributed.launch \
  --nproc_per_node=4 \
  --nnodes=2 \
  --node_rank=0 \
  --master_addr="node0" \
  --master_port=29500 \
  train.py
```

## Checkpoint Loading
```python
# Resume from checkpoint
trainer.load_checkpoint("./checkpoints/epoch_5")

# Load pretrained model
model = AutoModelForCausalLM.from_pretrained("nvidia/nemotron-4-340b")
```

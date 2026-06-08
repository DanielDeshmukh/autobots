# Holoscan SDK Integration

## Pipeline Architecture
```
Input → Operator A → Operator B → Operator C → Output
         (Preprocess)  (Inference)  (Postprocess)
```

## Basic Operator
```python
from holoscan.core import Operator, Fragment

class MyOperator(Operator):
    def __init__(self, fragment, *args, **kwargs):
        super().__init__(fragment, *args, **kwargs)
        self.add_input_port("input")
        self.add_output_port("output")

    def compute(self, op_input, op_output):
        data = op_input.receive()
        processed = self.process(data)
        op_output.emit(processed)
```

## Video Analytics Pipeline
```python
from holoscan.operators import VideoDecoder, InferenceProcessor, Visualizer

# Define pipeline
pipeline = Fragment("video-analytics")
decoder = pipeline.add_operator(VideoDecoder)
inference = pipeline.add_operator(InferenceProcessor)
visualizer = pipeline.add_operator(Visualizer)

# Connect operators
decoder >> inference >> visualizer
```

## GStreamer Integration
```python
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

# GStreamer to Holoscan bridge
pipeline = Gst.parse_launch(
    "v4l2src ! videoconvert ! appsink"
)
```

## TensorRT Inference
```python
from holoscan.operators import TensorRTInference

inference = TensorRTInference(
    model_path="model.onnx",
    engine_cache_dir="./engine_cache",
    precision="fp16",
    max_batch_size=8,
)
```

## Edge Deployment
```python
# Optimize for edge devices
config = {
    "precision": "fp16",
    "enable_trt": True,
    "max_workspace_size": 1 << 30,  # 1GB
    "enable_cuda_graph": True,
}
```

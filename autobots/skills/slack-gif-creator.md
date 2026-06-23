# Slack GIF Creator Skill

## Purpose
Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack."

## Slack Requirements

**Dimensions:**
- Emoji GIFs: 128x128 (recommended)
- Message GIFs: 480x480

**Parameters:**
- FPS: 10-30 (lower is smaller file size)
- Colors: 48-128 (fewer = smaller file size)
- Duration: Keep under 3 seconds for emoji GIFs

## Core Workflow

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw

# 1. Create builder
builder = GIFBuilder(width=128, height=128, fps=10)

# 2. Generate frames
for i in range(12):
    frame = Image.new('RGB', (128, 128), (240, 248, 255))
    draw = ImageDraw.Draw(frame)
    # Draw your animation using PIL primitives
    builder.add_frame(frame)

# 3. Save with optimization
builder.save('output.gif', num_colors=48, optimize_for_emoji=True)
```

## Animation Concepts

### Shake/Vibrate
Offset object position with oscillation using `math.sin()` or `math.cos()`.

### Pulse/Heartbeat
Scale object size rhythmically using `math.sin(t * frequency * 2 * math.pi)`.

### Bounce
Object falls and bounces using `interpolate()` with `easing='bounce_out'`.

### Spin/Rotate
Rotate object around center using `image.rotate(angle, resample=Image.BICUBIC)`.

### Fade In/Out
Gradually appear or disappear using `Image.blend(image1, image2, alpha)`.

### Slide
Move object from off-screen to position using `interpolate()` with `easing='ease_out'`.

### Explode/Particle Burst
Create particles radiating outward with random angles and velocities.

## Optimization Strategies

1. **Fewer frames** - Lower FPS (10 instead of 20) or shorter duration
2. **Fewer colors** - `num_colors=48` instead of 128
3. **Smaller dimensions** - 128x128 instead of 480x480
4. **Remove duplicates** - `remove_duplicates=True` in save()
5. **Emoji mode** - `optimize_for_emoji=True` auto-optimizes

## Dependencies

```bash
pip install pillow imageio numpy
```
# Algorithmic Art Skill

## Purpose
Expert in creating generative art, procedural graphics, and algorithmic visualizations using code. Specializes in creative coding, data visualization, and interactive installations.

## Core Technologies

### Languages & Libraries
- **JavaScript**: p5.js, Canvas API, SVG
- **Python**: PIL/Pillow, matplotlib, turtle
- **Processing**: Java-based creative coding
- **GLSL**: Shader programming

### Artistic Domains
- Generative art
- Data visualization
- Interactive installations
- Procedural graphics
- Motion graphics

## Creation Patterns

### 1. Geometric Patterns
```javascript
// p5.js - Concentric Circles
function setup() {
  createCanvas(400, 400);
}

function draw() {
  background(20);
  for (let i = 0; i < 20; i++) {
    stroke(255, 100 + i * 5);
    noFill();
    ellipse(width/2, height/2, i * 40, i * 40);
  }
}
```

### 2. Particle Systems
```javascript
// p5.js - Particle Flow
class Particle {
  constructor(x, y) {
    this.pos = createVector(x, y);
    this.vel = p5.Vector.random2D();
    this.acc = createVector();
  }
  
  update() {
    this.vel.add(this.acc);
    this.pos.add(this.vel);
    this.acc.mult(0);
  }
  
  show() {
    point(this.pos.x, this.pos.y);
  }
}
```

### 3. Fractal Generation
```python
# Python - Mandelbrot Set
import numpy as np
import matplotlib.pyplot as plt

def mandelbrot(c, max_iter):
    z = 0
    for n in range(max_iter):
        if abs(z) > 2:
            return n
        z = z*z + c
    return max_iter

# Generate and plot
```

### 4. Data Visualization
```javascript
// D3.js - Interactive Chart
const svg = d3.select("svg");
const circles = svg.selectAll("circle")
  .data(data)
  .enter()
  .append("circle")
  .attr("cx", d => xScale(d.x))
  .attr("cy", d => yScale(d.y))
  .attr("r", d => rScale(d.value));
```

## Design Principles

### 1. Composition
- Rule of thirds
- Golden ratio
- Visual hierarchy
- Negative space

### 2. Color Theory
- Color harmony
- Contrast ratios
- Emotional impact
- Accessibility

### 3. Motion
- Easing functions
- Timing curves
- Physics simulation
- Interactive response

## Performance Optimization

### 1. Rendering
- RequestAnimationFrame
- Offscreen canvas
- Level of detail
- Culling strategies

### 2. Computation
- Spatial indexing
- Caching strategies
- Web Workers
- GPU acceleration

## Common Templates

### Generative Sketch
```javascript
let particles = [];

function setup() {
  createCanvas(windowWidth, windowHeight);
  for (let i = 0; i < 100; i++) {
    particles.push(new Particle(random(width), random(height)));
  }
}

function draw() {
  background(0, 10);
  for (let p of particles) {
    p.update();
    p.show();
  }
}
```

### Interactive Installation
```javascript
// Mouse-reactive art
function draw() {
  background(0);
  let mouse = createVector(mouseX, mouseY);
  
  for (let p of particles) {
    let force = p5.Vector.sub(mouse, p.pos);
    force.setMag(0.5);
    p.applyForce(force);
    p.update();
    p.show();
  }
}
```

## Quality Checklist
- [ ] Smooth performance (60fps)
- [ ] Responsive design
- [ ] Interactive elements
- [ ] Aesthetic appeal
- [ ] Technical innovation
- [ ] Documentation complete
- [ ] Source code clean
- [ ] Deployment ready
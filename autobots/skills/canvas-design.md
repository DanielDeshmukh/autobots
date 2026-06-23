# Canvas Design Skill

## Purpose
Expert in HTML5 Canvas, SVG, and graphics programming. Creates interactive visualizations, games, and graphical applications with modern web technologies.

## Core Technologies

### HTML5 Canvas
- 2D Context API
- WebGL for 3D
- OffscreenCanvas
- Image manipulation

### SVG
- Vector graphics
- Animations
- Interactive elements
- Responsive design

### Graphics Libraries
- Paper.js
- Fabric.js
- Three.js (3D)
- D3.js (data visualization)

## Canvas Operations

### 1. Basic Drawing
```javascript
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Rectangle
ctx.fillStyle = '#3498db';
ctx.fillRect(10, 10, 100, 100);

// Circle
ctx.beginPath();
ctx.arc(200, 200, 50, 0, Math.PI * 2);
ctx.fill();

// Line
ctx.beginPath();
ctx.moveTo(0, 0);
ctx.lineTo(300, 300);
ctx.stroke();
```

### 2. Animations
```javascript
let x = 0;
function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  ctx.fillStyle = '#e74c3c';
  ctx.fillRect(x, 100, 50, 50);
  
  x += 2;
  if (x > canvas.width) x = 0;
  
  requestAnimationFrame(animate);
}
animate();
```

### 3. Event Handling
```javascript
canvas.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  
  ctx.fillStyle = '#2ecc71';
  ctx.beginPath();
  ctx.arc(x, y, 20, 0, Math.PI * 2);
  ctx.fill();
});
```

## SVG Creation

### Basic Shapes
```svg
<svg width="400" height="300">
  <rect x="10" y="10" width="100" height="100" fill="#3498db"/>
  <circle cx="200" cy="150" r="50" fill="#e74c3c"/>
  <line x1="0" y1="0" x2="400" y2="300" stroke="#2ecc71" stroke-width="2"/>
</svg>
```

### Animations
```svg
<svg width="200" height="200">
  <circle cx="100" cy="100" r="30" fill="#e74c3c">
    <animate attributeName="r" values="30;50;30" dur="2s" repeatCount="indefinite"/>
  </circle>
</svg>
```

## Best Practices

### 1. Performance
- Use requestAnimationFrame
- Minimize state changes
- Batch drawing operations
- Use offscreen canvas for complex scenes

### 2. Responsiveness
- Scale canvas with device pixel ratio
- Handle window resize events
- Use viewBox for SVG

### 3. Accessibility
- Provide text alternatives
- Keyboard navigation
- Screen reader support

### 4. Code Organization
- Separate concerns
- Use classes for objects
- Modular architecture

## Common Patterns

### Game Loop
```javascript
class Game {
  constructor() {
    this.canvas = document.getElementById('game');
    this.ctx = this.canvas.getContext('2d');
    this.lastTime = 0;
    this.deltaTime = 0;
  }
  
  update(deltaTime) {
    // Update game state
  }
  
  render() {
    // Draw to canvas
  }
  
  gameLoop(timestamp) {
    this.deltaTime = timestamp - this.lastTime;
    this.lastTime = timestamp;
    
    this.update(this.deltaTime);
    this.render();
    
    requestAnimationFrame(this.gameLoop.bind(this));
  }
}
```

### Interactive Canvas
```javascript
class InteractiveCanvas {
  constructor() {
    this.elements = [];
    this.selectedElement = null;
    this.setupEventListeners();
  }
  
  setupEventListeners() {
    this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
    this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
    this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
  }
  
  onMouseDown(e) {
    // Handle selection
  }
  
  onMouseMove(e) {
    // Handle dragging
  }
  
  onMouseUp(e) {
    // Handle drop
  }
}
```

## Quality Checklist
- [ ] Smooth 60fps performance
- [ ] Responsive design
- [ ] Interactive elements work
- [ ] Cross-browser compatible
- [ ] Proper error handling
- [ ] Memory management
- [ ] Documentation complete
- [ ] Examples provided
# Web Artifacts Builder Skill

## Purpose
Expert in building interactive web artifacts, widgets, and components. Creates standalone, embeddable web elements with modern frameworks and best practices.

## Core Technologies

### Frontend Frameworks
- React/JSX
- Vue.js/SFC
- Svelte
- Web Components

### Styling Solutions
- CSS-in-JS (styled-components, Emotion)
- Tailwind CSS
- CSS Modules
- Scoped CSS

### Build Tools
- Vite
- Webpack
- Rollup
- esbuild

## Artifact Types

### 1. Interactive Widgets
```jsx
// React Widget
import React, { useState } from 'react';

export const Counter = () => {
  const [count, setCount] = useState(0);
  
  return (
    <div className="counter">
      <h2>Count: {count}</h2>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
};
```

### 2. Data Visualization
```jsx
// Chart Component
import React from 'react';
import { LineChart, Line, XAxis, YAxis } from 'recharts';

export const DataChart = ({ data }) => (
  <LineChart width={600} height={300} data={data}>
    <XAxis dataKey="name" />
    <YAxis />
    <Line type="monotone" dataKey="value" stroke="#8884d8" />
  </LineChart>
);
```

### 3. Form Components
```jsx
// Form with Validation
import React, { useState } from 'react';

export const ContactForm = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });
  const [errors, setErrors] = useState({});
  
  const validate = () => {
    const newErrors = {};
    if (!formData.name) newErrors.name = 'Name required';
    if (!formData.email) newErrors.email = 'Email required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (validate()) {
      // Submit logic
    }
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={formData.name}
        onChange={(e) => setFormData({...formData, name: e.target.value})}
      />
      {errors.name && <span>{errors.name}</span>}
      <button type="submit">Submit</button>
    </form>
  );
};
```

## Build Configuration

### Vite Config
```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: 'src/index.jsx',
      name: 'MyArtifact',
      fileName: 'my-artifact'
    },
    rollupOptions: {
      external: ['react', 'react-dom'],
      output: {
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM'
        }
      }
    }
  }
});
```

### Package.json
```json
{
  "name": "my-artifact",
  "version": "1.0.0",
  "main": "dist/my-artifact.umd.js",
  "module": "dist/my-artifact.es.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "peerDependencies": {
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  }
}
```

## Best Practices

### 1. Self-Contained
- Bundle all dependencies
- No external runtime requirements
- Proper UMD/ESM output

### 2. Responsive Design
- Mobile-first approach
- Flexible layouts
- Touch-friendly interactions

### 3. Accessibility
- ARIA labels
- Keyboard navigation
- Screen reader support

### 4. Performance
- Lazy loading
- Code splitting
- Optimized bundles

## Quality Checklist
- [ ] Self-contained bundle
- [ ] Responsive design
- [ ] Accessible (WCAG)
- [ ] Cross-browser compatible
- [ ] Proper error handling
- [ ] Documentation included
- [ ] Examples provided
- [ ] Performance optimized
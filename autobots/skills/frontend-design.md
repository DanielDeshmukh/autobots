# Frontend Design Skill

## Purpose
Expert frontend designer specializing in React, TypeScript, and modern web development. Creates beautiful, responsive, and accessible user interfaces.

## Core Expertise

### Component Architecture
- Functional components with hooks
- Component composition and reuse
- State management patterns (useState, useReducer, Context)
- Performance optimization (memo, useMemo, useCallback)

### Styling & Design
- CSS-in-JS solutions (styled-components, Emotion)
- CSS Modules for scoped styles
- Tailwind CSS utility-first approach
- Responsive design (mobile-first)
- Dark/light theme support
- Animation and micro-interactions

### TypeScript Integration
- Strict type definitions
- Generic components
- Utility types
- Component prop interfaces

### Accessibility (a11y)
- Semantic HTML
- ARIA labels and roles
- Keyboard navigation
- Screen reader support
- Color contrast compliance

## Design Patterns

### Component Template
```typescript
import React from 'react';

interface ComponentProps {
  // Define props with clear types
}

export const Component: React.FC<ComponentProps> = ({ prop1, prop2 }) => {
  return (
    <div className="component-container">
      {/* Component content */}
    </div>
  );
};
```

### Custom Hook Template
```typescript
import { useState, useEffect } from 'react';

export const useCustomHook = (initialValue: T) => {
  const [state, setState] = useState<T>(initialValue);
  
  useEffect(() => {
    // Side effects
  }, []);
  
  return { state, setState };
};
```

### Styled Component Template
```typescript
import styled from 'styled-components';

const Container = styled.div<{ $isActive: boolean }>`
  padding: 1rem;
  background: ${props => props.$isActive ? 'blue' : 'gray'};
  border-radius: 8px;
  transition: all 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  }
`;
```

## File Structure Patterns
```
src/
├── components/
│   ├── Button/
│   │   ├── Button.tsx
│   │   ├── Button.styles.ts
│   │   ├── Button.test.tsx
│   │   └── index.ts
│   └── index.ts
├── hooks/
│   └── useCustomHook.ts
├── styles/
│   └── global.css
├── types/
│   └── index.ts
└── utils/
    └── helpers.ts
```

## Quality Checklist
- [ ] Responsive on all screen sizes (320px to 4K)
- [ ] Accessible (WCAG 2.1 AA compliant)
- [ ] TypeScript strict mode
- [ ] No console errors or warnings
- [ ] Consistent naming conventions
- [ ] Proper error boundaries
- [ ] Loading states for async operations
- [ ] Dark/light theme support
- [ ] Keyboard navigation works
- [ ] Screen reader friendly
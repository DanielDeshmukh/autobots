# Theme Factory Skill

## Purpose
Expert in creating, managing, and implementing design systems and themes. Specializes in CSS architecture, design tokens, and theme customization for web applications.

## Core Concepts

### Design Tokens
- Colors
- Typography
- Spacing
- Shadows
- Borders
- Breakpoints

### Theme Architecture
- Light/Dark modes
- Component-level theming
- Responsive design
- Accessibility compliance

## Theme Structure

### CSS Custom Properties
```css
:root {
  /* Colors */
  --color-primary: #3498db;
  --color-secondary: #2ecc71;
  --color-accent: #e74c3c;
  
  /* Typography */
  --font-family: 'Inter', sans-serif;
  --font-size-base: 16px;
  --font-size-lg: 18px;
  --font-size-sm: 14px;
  
  /* Spacing */
  --spacing-xs: 4px;
  --spacing-sm: 8px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  
  /* Borders */
  --border-radius-sm: 4px;
  --border-radius-md: 8px;
  --border-radius-lg: 12px;
}

/* Dark Mode */
[data-theme="dark"] {
  --color-bg: #1a1a1a;
  --color-text: #ffffff;
  --color-primary: #5dade2;
}
```

### Theme Configuration
```javascript
const theme = {
  colors: {
    primary: {
      50: '#eff6ff',
      100: '#dbeafe',
      500: '#3b82f6',
      900: '#1e3a8a'
    }
  },
  typography: {
    fontFamily: {
      sans: ['Inter', 'sans-serif'],
      mono: ['Fira Code', 'monospace']
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem'
    }
  },
  spacing: {
    1: '0.25rem',
    2: '0.5rem',
    3: '0.75rem',
    4: '1rem'
  }
};
```

## Implementation Patterns

### 1. CSS-in-JS (styled-components)
```javascript
import styled from 'styled-components';

const Button = styled.button`
  background: ${props => props.theme.colors.primary};
  color: ${props => props.theme.colors.text};
  padding: ${props => props.theme.spacing[2]} ${props => props.theme.spacing[4]};
  border-radius: ${props => props.theme.borderRadius.md};
  font-size: ${props => props.theme.fontSize.base};
  
  &:hover {
    background: ${props => props.theme.colors.primaryDark};
  }
`;
```

### 2. Tailwind CSS
```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#3498db',
        secondary: '#2ecc71'
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif']
      }
    }
  }
}
```

### 3. CSS Modules
```css
/* Button.module.css */
.button {
  background: var(--color-primary);
  color: var(--color-text);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius-md);
}
```

## Best Practices

### 1. Design System
- Consistent naming conventions
- Token hierarchy (global → component)
- Version control
- Documentation

### 2. Performance
- Minimal CSS specificity
- Efficient selectors
- Lazy loading of themes
- Critical CSS inlining

### 3. Accessibility
- Sufficient color contrast
- Focus states
- Screen reader support
- Keyboard navigation

### 4. Maintainability
- Single source of truth
- Automated testing
- Design token validation
- Cross-browser compatibility

## Common Templates

### Theme Provider
```jsx
import React, { createContext, useContext } from 'react';

const ThemeContext = createContext();

export const ThemeProvider = ({ children, theme }) => {
  return (
    <ThemeContext.Provider value={theme}>
      <div data-theme={theme.mode}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
```

### Theme Switcher
```jsx
import React from 'react';
import { useTheme } from './ThemeProvider';

export const ThemeSwitcher = () => {
  const { theme, setTheme } = useTheme();
  
  return (
    <button onClick={() => setTheme({
      ...theme,
      mode: theme.mode === 'light' ? 'dark' : 'light'
    })}>
      Toggle Theme
    </button>
  );
};
```

## Quality Checklist
- [ ] Consistent design tokens
- [ ] Light/dark mode support
- [ ] Responsive design
- [ ] Accessible colors
- [ ] Performance optimized
- [ ] Documentation complete
- [ ] Cross-browser tested
- [ ] Version controlled
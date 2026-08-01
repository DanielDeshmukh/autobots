---
name: react-components
description: Generic React component patterns for autobot-swarm. Use when building UI components, managing state, or creating interactive elements. Provides import patterns, hook usage, prop types, and component composition.
---

# React Components Skill

## Import Patterns

```typescript
// React core
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";

// Types
import type { FC, ReactNode } from "react";

// Custom hooks
import { useCustomHook } from "../hooks/useCustomHook";

// Types from shared context
import type { TypeName } from "../types/TypeName";

// Utilities
import { utilityFunction } from "../utils/utilityFunction";
```

## Component Structure

```typescript
// Functional component with props
interface ComponentNameProps {
  requiredProp: string;
  optionalProp?: number;
  children?: ReactNode;
  onAction: (id: string) => void;
}

export const ComponentName: FC<ComponentNameProps> = ({
  requiredProp,
  optionalProp = 0,
  children,
  onAction,
}) => {
  // State
  const [state, setState] = useState<string>("");

  // Effects
  useEffect(() => {
    // Side effects here
  }, [dependency]);

  // Callbacks
  const handleClick = useCallback(() => {
    onAction(state);
  }, [onAction, state]);

  // Memoized values
  const memoizedValue = useMemo(() => {
    return expensiveCalculation(state);
  }, [state]);

  return (
    <div className="component-wrapper">
      {children}
    </div>
  );
};

export default ComponentName;
```

## Hook Patterns

```typescript
// Custom hook
export function useCustomHook(initialValue: string) {
  const [value, setValue] = useState(initialValue);

  const updateValue = useCallback((newValue: string) => {
    setValue(newValue);
  }, []);

  return { value, updateValue };
}
```

## Event Handlers

```typescript
// Click handler
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
  e.preventDefault();
  // Handle click
};

// Input handler
const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setValue(e.target.value);
};

// Form submit
const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  // Handle submit
};
```

## Common Patterns

```typescript
// Conditional rendering
{condition && <Component />}

// List rendering
{items.map((item) => (
  <Component key={item.id} {...item} />
))}

// Loading state
if (loading) return <div>Loading...</div>;

// Error boundary
if (error) return <div>Error: {error.message}</div>;
```

## Best Practices

1. Always use TypeScript for props and state
2. Use functional components with hooks
3. Keep components small and focused
4. Extract complex logic into custom hooks
5. Use memoization for expensive calculations
6. Handle loading and error states
7. Use proper key props for lists
8. Avoid inline functions in JSX when possible

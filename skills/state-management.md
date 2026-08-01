---
name: state-management
description: Generic state management patterns for autobot-swarm. Use when managing application state, handling complex state logic, or implementing state persistence. Provides React hooks, Context API, and state patterns.
---

# State Management Skill

## useState Patterns

```typescript
// Basic state
const [count, setCount] = useState<number>(0);

// Object state
const [user, setUser] = useState<User>({
  id: "",
  name: "",
  email: "",
});

// Array state
const [items, setItems] = useState<Item[]>([]);

// Lazy initialization
const [state, setState] = useState(() => {
  const saved = localStorage.getItem("state");
  return saved ? JSON.parse(saved) : initialValue;
});

// Functional updates
setCount((prev) => prev + 1);
setItems((prev) => [...prev, newItem]);
setUser((prev) => ({ ...prev, name: "John" }));
```

## useReducer Patterns

```typescript
// Action types
type GameAction =
  | { type: "MAKE_MOVE"; position: number }
  | { type: "RESET_GAME" }
  | { type: "SET_WINNER"; winner: string }
  | { type: "SET_DRAW" };

// Reducer function
function gameReducer(state: GameState, action: GameAction): GameState {
  switch (action.type) {
    case "MAKE_MOVE":
      return {
        ...state,
        board: state.board.map((cell, i) =>
          i === action.position ? state.currentPlayer : cell
        ),
        currentPlayer: state.currentPlayer === "X" ? "O" : "X",
      };
    case "RESET_GAME":
      return initialState;
    case "SET_WINNER":
      return { ...state, winner: action.winner };
    case "SET_DRAW":
      return { ...state, isDraw: true };
    default:
      return state;
  }
}

// Using reducer
const [state, dispatch] = useReducer(gameReducer, initialState);

// Dispatch actions
dispatch({ type: "MAKE_MOVE", position: 5 });
dispatch({ type: "RESET_GAME" });
```

## Context API Patterns

```typescript
// Create context
interface GameContextType {
  state: GameState;
  dispatch: React.Dispatch<GameAction>;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

// Provider component
function GameProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(gameReducer, initialState);

  return (
    <GameContext.Provider value={{ state, dispatch }}>
      {children}
    </GameContext.Provider>
  );
}

// Custom hook
function useGame(): GameContextType {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error("useGame must be used within a GameProvider");
  }
  return context;
}

// Using in component
function GameBoard() {
  const { state, dispatch } = useGame();
  return <div>{/* ... */}</div>;
}
```

## Custom Hook Patterns

```typescript
//useLocalStorage
function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      return initialValue;
    }
  });

  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore =
        value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(error);
    }
  };

  return [storedValue, setValue] as const;
}

//useDebounce
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

//useInterval
function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;

    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}
```

## State Persistence

```typescript
// Save to localStorage
useEffect(() => {
  localStorage.setItem("gameState", JSON.stringify(state));
}, [state]);

// Load from localStorage
useEffect(() => {
  const saved = localStorage.getItem("gameState");
  if (saved) {
    dispatch({ type: "LOAD_STATE", payload: JSON.parse(saved) });
  }
}, []);

// Save to URL params
useEffect(() => {
  const params = new URLSearchParams();
  params.set("board", JSON.stringify(state.board));
  window.history.replaceState({}, "", `?${params.toString()}`);
}, [state.board]);
```

## Best Practices

1. Keep state as simple as possible
2. Use useState for simple state, useReducer for complex state
3. Use Context API for shared state across components
4. Extract complex logic into custom hooks
5. Persist state when needed (localStorage, URL params)
6. Use functional updates for state that depends on previous state
7. Avoid deep nesting of state objects
8. Use TypeScript for type safety

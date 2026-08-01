---
name: testing-patterns
description: Generic testing patterns for autobot-swarm. Use when writing unit tests, integration tests, or end-to-end tests. Provides test patterns, mocking, and assertion patterns.
---

# Testing Patterns Skill

## Unit Testing

```typescript
// src/utils/gameLogic.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { checkWinner, isBoardFull, minimax } from "./gameLogic";

describe("checkWinner", () => {
  it("should return X when X wins horizontally", () => {
    const board = ["X", "X", "X", null, null, null, null, null, null];
    expect(checkWinner(board)).toBe("X");
  });

  it("should return O when O wins vertically", () => {
    const board = ["O", null, null, "O", null, null, "O", null, null];
    expect(checkWinner(board)).toBe("O");
  });

  it("should return null when no winner", () => {
    const board = ["X", "O", "X", null, null, null, null, null, null];
    expect(checkWinner(board)).toBeNull();
  });
});

describe("isBoardFull", () => {
  it("should return true when board is full", () => {
    const board = ["X", "O", "X", "O", "X", "O", "O", "X", "O"];
    expect(isBoardFull(board)).toBe(true);
  });

  it("should return false when board has empty cells", () => {
    const board = ["X", "O", "X", null, null, null, null, null, null];
    expect(isBoardFull(board)).toBe(false);
  });
});
```

## Component Testing

```typescript
// src/components/GameBoard.test.tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { GameBoard } from "./GameBoard";

describe("GameBoard", () => {
  it("should render the game board", () => {
    const board = Array(9).fill(null);
    render(<GameBoard board={board} onCellClick={vi.fn()} />);
    
    expect(screen.getAllByRole("button")).toHaveLength(9);
  });

  it("should call onCellClick when a cell is clicked", () => {
    const board = Array(9).fill(null);
    const onCellClick = vi.fn();
    render(<GameBoard board={board} onCellClick={onCellClick} />);
    
    fireEvent.click(screen.getAllByRole("button")[0]);
    expect(onCellClick).toHaveBeenCalledWith(0);
  });

  it("should display X and O markers", () => {
    const board = ["X", "O", null, null, "X", null, null, null, "O"];
    render(<GameBoard board={board} onCellClick={vi.fn()} />);
    
    expect(screen.getByText("X")).toBeInTheDocument();
    expect(screen.getByText("O")).toBeInTheDocument();
  });
});
```

## Mocking

```typescript
// Mock function
const mockFunction = vi.fn();
mockFunction.mockReturnValue(42);
mockFunction.mockResolvedValue({ data: "test" });

// Mock module
vi.mock("./module", () => ({
  function: vi.fn(),
}));

// Mock API call
vi.mock("../api", () => ({
  fetchUsers: vi.fn().mockResolvedValue([
    { id: "1", name: "John" },
    { id: "2", name: "Jane" },
  ]),
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });
```

## Async Testing

```typescript
describe("Async operations", () => {
  it("should fetch data", async () => {
    const data = await fetchData();
    expect(data).toBeDefined();
  });

  it("should handle errors", async () => {
    await expect(fetchData()).rejects.toThrow("Error");
  });

  it("should mock async function", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ data: "test" });
    const result = await mockFetch();
    expect(result).toEqual({ data: "test" });
  });
});
```

## Integration Testing

```typescript
// src/integration/game.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { GameEngine } from "./gameEngine";

describe("GameEngine Integration", () => {
  let engine: GameEngine;

  beforeEach(() => {
    engine = new GameEngine();
  });

  it("should play a complete game", () => {
    // Player X wins
    engine.makeMove(0); // X
    engine.makeMove(3); // O
    engine.makeMove(1); // X
    engine.makeMove(4); // O
    engine.makeMove(2); // X wins

    expect(engine.getWinner()).toBe("X");
    expect(engine.isGameOver()).toBe(true);
  });

  it("should detect draw", () => {
    // Draw game
    engine.makeMove(0); // X
    engine.makeMove(1); // O
    engine.makeMove(2); // X
    engine.makeMove(4); // O
    engine.makeMove(3); // X
    engine.makeMove(5); // O
    engine.makeMove(7); // X
    engine.makeMove(6); // O
    engine.makeMove(8); // X

    expect(engine.isDraw()).toBe(true);
    expect(engine.isGameOver()).toBe(true);
  });
});
```

## Test Utilities

```typescript
// src/test-utils.tsx
import { render, RenderOptions } from "@testing-library/react";
import { ReactElement } from "react";
import { GameProvider } from "../context/GameContext";

function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">
) {
  return render(ui, { wrapper: GameProvider, ...options });
}

export * from "@testing-library/react";
export { customRender as render };
```

## Best Practices

1. Write tests for all critical functionality
2. Use descriptive test names
3. Follow AAA pattern (Arrange-Act-Assert)
4. Mock external dependencies
5. Test edge cases and error conditions
6. Keep tests independent
7. Use beforeEach/afterEach for setup/cleanup
8. Aim for high test coverage

---
name: typescript-patterns
description: Generic TypeScript patterns for autobot-swarm. Use when defining types, interfaces, generics, or utility types. Provides type patterns, interfaces, and best practices.
---

# TypeScript Patterns Skill

## Basic Types

```typescript
// Primitive types
const name: string = "John";
const age: number = 30;
const isActive: boolean = true;
const items: string[] = ["a", "b", "c"];

// Object types
interface User {
  id: string;
  name: string;
  email: string;
  age?: number; // Optional
  readonly createdAt: Date; // Readonly
}

// Union types
type Status = "pending" | "active" | "completed";
type ID = string | number;

// Intersection types
type UserWithRole = User & { role: string };
```

## Interfaces

```typescript
// Basic interface
interface GameState {
  board: (string | null)[];
  currentPlayer: "X" | "O";
  winner: string | null;
  isDraw: boolean;
}

// Interface with methods
interface GameEngine {
  makeMove(position: number): void;
  resetGame(): void;
  checkWinner(): string | null;
  getScore(): { x: number; o: number };
}

// Extending interfaces
interface BaseEntity {
  id: string;
  createdAt: Date;
  updatedAt: Date;
}

interface User extends BaseEntity {
  name: string;
  email: string;
}

interface Post extends BaseEntity {
  title: string;
  content: string;
  authorId: string;
}
```

## Generics

```typescript
// Generic function
function identity<T>(arg: T): T {
  return arg;
}

// Generic interface
interface ApiResponse<T> {
  data: T;
  status: number;
  message: string;
}

// Generic class
class Repository<T> {
  private items: T[] = [];

  add(item: T): void {
    this.items.push(item);
  }

  getById(id: string): T | undefined {
    return this.items.find((item) => (item as any).id === id);
  }

  getAll(): T[] {
    return [...this.items];
  }
}

// Generic constraints
interface HasId {
  id: string;
}

function findById<T extends HasId>(items: T[], id: string): T | undefined {
  return items.find((item) => item.id === id);
}
```

## Utility Types

```typescript
// Partial - makes all properties optional
type PartialUser = Partial<User>;

// Required - makes all properties required
type RequiredUser = Required<User>;

// Pick - picks specific properties
type UserBasic = Pick<User, "id" | "name">;

// Omit - omits specific properties
type UserWithoutEmail = Omit<User, "email">;

// Record - creates object type
type UserRoles = Record<string, string[]>;

// Readonly - makes all properties readonly
type ReadonlyUser = Readonly<User>;

// Exclude - excludes types from union
type NonNullStatus = Exclude<Status, "pending">;

// Extract - extracts types from union
type ActiveStatus = Extract<Status, "active" | "completed">;

// ReturnType - gets return type of function
type GameEngineReturn = ReturnType<GameEngine["makeMove"]>;
```

## Type Guards

```typescript
// typeof guard
function isString(value: unknown): value is string {
  return typeof value === "string";
}

// instanceof guard
function isError(value: unknown): value is Error {
  return value instanceof Error;
}

// Custom type guard
function isUser(obj: unknown): obj is User {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "id" in obj &&
    "name" in obj &&
    "email" in obj
  );
}

// Discriminated union
type Shape =
  | { kind: "circle"; radius: number }
  | { kind: "rectangle"; width: number; height: number };

function getArea(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2;
    case "rectangle":
      return shape.width * shape.height;
  }
}
```

## Enums

```typescript
// Numeric enum
enum Direction {
  Up = 0,
  Down = 1,
  Left = 2,
  Right = 3,
}

// String enum
enum GameMode {
  PvP = "pvp",
  PvAI = "pvai",
  Tournament = "tournament",
}

// Const enum (inlined at compile time)
const enum Status {
  Active = "active",
  Inactive = "inactive",
}
```

## Type Assertions

```typescript
// Angle bracket syntax (not recommended in TSX)
const name = <string>"John";

// As syntax (recommended)
const name = "John" as string;

// Non-null assertion
const element = document.getElementById("app")!;
const value = someObject?.property!;
```

## Best Practices

1. Use interfaces for object shapes
2. Use type aliases for unions and intersections
3. Use generics for reusable components
4. Use type guards for runtime type checking
5. Use discriminated unions for complex states
6. Avoid `any` type - use `unknown` instead
7. Use readonly for immutable data
8. Use utility types to reduce code duplication

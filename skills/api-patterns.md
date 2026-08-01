---
name: api-patterns
description: Generic API patterns for autobot-swarm. Use when creating REST APIs, handling HTTP requests, or implementing backend logic. Provides Express.js patterns, middleware, and error handling.
---

# API Patterns Skill

## Express.js Basic Setup

```typescript
// src/index.ts
import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(helmet());
app.use(morgan("dev"));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Routes
app.use("/api/users", userRoutes);
app.use("/api/posts", postRoutes);

// Error handling middleware
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

## Route Patterns

```typescript
// src/routes/userRoutes.ts
import { Router, Request, Response, NextFunction } from "express";
import { UserController } from "../controllers/userController";
import { authMiddleware } from "../middleware/auth";
import { validateRequest } from "../middleware/validate";
import { userSchema } from "../schemas/user";

const router = Router();
const userController = new UserController();

// GET /api/users
router.get("/", async (req: Request, res: Response) => {
  const users = await userController.getAll();
  res.json({ data: users });
});

// GET /api/users/:id
router.get("/:id", async (req: Request, res: Response) => {
  const user = await userController.getById(req.params.id);
  if (!user) {
    return res.status(404).json({ error: "User not found" });
  }
  res.json({ data: user });
});

// POST /api/users
router.post(
  "/",
  authMiddleware,
  validateRequest(userSchema),
  async (req: Request, res: Response) => {
    const user = await userController.create(req.body);
    res.status(201).json({ data: user });
  }
);

// PUT /api/users/:id
router.put(
  "/:id",
  authMiddleware,
  validateRequest(userSchema),
  async (req: Request, res: Response) => {
    const user = await userController.update(req.params.id, req.body);
    res.json({ data: user });
  }
);

// DELETE /api/users/:id
router.delete("/:id", authMiddleware, async (req: Request, res: Response) => {
  await userController.delete(req.params.id);
  res.status(204).send();
});

export default router;
```

## Controller Patterns

```typescript
// src/controllers/userController.ts
import { UserService } from "../services/userService";
import { CreateUserDTO, UpdateUserDTO } from "../types/user";

export class UserController {
  private userService: UserService;

  constructor() {
    this.userService = new UserService();
  }

  async getAll() {
    return this.userService.findAll();
  }

  async getById(id: string) {
    return this.userService.findById(id);
  }

  async create(data: CreateUserDTO) {
    return this.userService.create(data);
  }

  async update(id: string, data: UpdateUserDTO) {
    return this.userService.update(id, data);
  }

  async delete(id: string) {
    return this.userService.delete(id);
  }
}
```

## Service Patterns

```typescript
// src/services/userService.ts
import { UserRepository } from "../repositories/userRepository";
import { CreateUserDTO, UpdateUserDTO, User } from "../types/user";
import { AppError } from "../errors/AppError";

export class UserService {
  private userRepository: UserRepository;

  constructor() {
    this.userRepository = new UserRepository();
  }

  async findAll(): Promise<User[]> {
    return this.userRepository.findAll();
  }

  async findById(id: string): Promise<User | null> {
    return this.userRepository.findById(id);
  }

  async create(data: CreateUserDTO): Promise<User> {
    // Check if user exists
    const existing = await this.userRepository.findByEmail(data.email);
    if (existing) {
      throw new AppError("User with this email already exists", 400);
    }

    return this.userRepository.create(data);
  }

  async update(id: string, data: UpdateUserDTO): Promise<User> {
    const user = await this.userRepository.findById(id);
    if (!user) {
      throw new AppError("User not found", 404);
    }

    return this.userRepository.update(id, data);
  }

  async delete(id: string): Promise<void> {
    const user = await this.userRepository.findById(id);
    if (!user) {
      throw new AppError("User not found", 404);
    }

    await this.userRepository.delete(id);
  }
}
```

## Middleware Patterns

```typescript
// src/middleware/auth.ts
import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";

export const authMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  const token = req.headers.authorization?.split(" ")[1];

  if (!token) {
    return res.status(401).json({ error: "No token provided" });
  }

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET!);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ error: "Invalid token" });
  }
};

// src/middleware/validate.ts
import { Request, Response, NextFunction } from "express";
import { ZodSchema } from "zod";

export const validateRequest = (schema: ZodSchema) => {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({ error: result.error.issues });
    }
    req.body = result.data;
    next();
  };
};

// src/middleware/errorHandler.ts
import { Request, Response, NextFunction } from "express";
import { AppError } from "../errors/AppError";

export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({ error: err.message });
  }

  console.error(err);
  res.status(500).json({ error: "Internal server error" });
};
```

## Error Handling

```typescript
// src/errors/AppError.ts
export class AppError extends Error {
  public statusCode: number;
  public isOperational: boolean;

  constructor(message: string, statusCode: number) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

// Usage in controllers/services
throw new AppError("User not found", 404);
throw new AppError("Invalid input", 400);
throw new AppError("Unauthorized", 401);
```

## Best Practices

1. Use TypeScript for type safety
2. Follow MVC pattern (Model-View-Controller)
3. Use middleware for cross-cutting concerns
4. Validate all input data
5. Use proper HTTP status codes
6. Handle errors consistently
7. Use environment variables for config
8. Add logging for debugging

# MCP Builder Skill

## Purpose
Expert in building Model Context Protocol (MCP) servers and clients. Creates robust, scalable MCP implementations with proper tool definitions and resource management.

## Core Concepts

### MCP Architecture
- **Server**: Provides tools and resources
- **Client**: Consumes tools and resources
- **Transport**: Communication layer (stdio, HTTP, SSE)
- **Tools**: Executable functions
- **Resources**: Read-only data sources

### Protocol Flow
1. Client connects to server
2. Server advertises capabilities
3. Client requests tool/resource access
4. Server executes and returns results

## Server Implementation

### Basic Server Structure
```python
from mcp.server import Server
from mcp.types import Tool, Resource
import asyncio

server = Server("my-server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="example_tool",
            description="An example tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter 1"}
                },
                "required": ["param1"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "example_tool":
        return {"result": f"Processed: {arguments['param1']}"}

async def main():
    async with server.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    asyncio.run(main())
```

### Tool Definitions
```python
Tool(
    name="tool_name",
    description="What this tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param"]
    }
)
```

### Resource Definitions
```python
Resource(
    uri="resource://example",
    name="example_resource",
    description="An example resource",
    mimeType="application/json"
)
```

## Client Implementation

### Basic Client
```python
from mcp.client import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    async with stdio_client("python", "server.py") as (read, write):
        async with ClientSession(read, write) as session:
            # List tools
            tools = await session.list_tools()
            
            # Call tool
            result = await session.call_tool(
                "example_tool",
                {"param1": "value"}
            )
```

## Best Practices

### 1. Tool Design
- Single responsibility
- Clear descriptions
- Proper error handling
- Input validation

### 2. Resource Management
- Efficient data loading
- Caching when appropriate
- Proper cleanup

### 3. Error Handling
```python
@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        # Tool logic
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}
```

### 4. Security
- Validate inputs
- Sanitize outputs
- Rate limiting
- Authentication when needed

## Common Patterns

### File Operations Tool
```python
Tool(
    name="read_file",
    description="Read file contents",
    inputSchema={
        "type": "object",
        "properties": {
            "path": {"type": "string"}
        },
        "required": ["path"]
    }
)

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "read_file":
        with open(arguments['path'], 'r') as f:
            return {"content": f.read()}
```

### Database Query Tool
```python
Tool(
    name="query_db",
    description="Execute database query",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "params": {"type": "array"}
        },
        "required": ["query"]
    }
)

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "query_db":
        result = await db.execute(
            arguments['query'],
            arguments.get('params', [])
        )
        return {"rows": result}
```

## Quality Checklist
- [ ] Tools properly defined
- [ ] Resources correctly configured
- [ ] Error handling implemented
- [ ] Input validation added
- [ ] Security measures in place
- [ ] Documentation complete
- [ ] Tests written
- [ ] Performance optimized
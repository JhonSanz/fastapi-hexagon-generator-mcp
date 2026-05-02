# fastapi-hexagon-mcp

[![PyPI](https://img.shields.io/pypi/v/fastapi-hexagon-mcp.svg)](https://pypi.org/project/fastapi-hexagon-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/fastapi-hexagon-mcp.svg)](https://pypi.org/project/fastapi-hexagon-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An MCP (Model Context Protocol) server that lets Claude — and any other MCP-compatible client — scaffold production-ready **FastAPI** projects following **hexagonal (ports & adapters) architecture**.

It generates the full module: domain entities, ORM models, Pydantic schemas, repositories, use cases, and API routes — with the wiring between them, validation, search, filters, and relationships all handled for you.

---

## Why

Hexagonal architecture is great for separation of concerns, but the boilerplate is painful: every new entity touches 6+ files across 4 layers. This MCP automates the mechanical parts (file generation, field propagation, repository mapping, dependency wiring) while leaving the parts that need real judgment (domain rules, custom validations) as TODOs you complete with the LLM.

The result: ask Claude for *"a Product CRUD with name, price, and category"* and get a working, well-structured FastAPI module in seconds.

## Features

- **Layered scaffolding** — generates domain, application, infrastructure, and routes layers with a single command.
- **Field propagation across layers** — define a field once; it shows up correctly typed in entities, models, schemas, mappers, and search filters.
- **Relationship support** — one-to-many and many-to-one foreign keys with proper SQLAlchemy + Pydantic plumbing.
- **Dependency injection wiring** — auto-registers repositories and use cases.
- **Built-in apps** — bootstrap a complete project (auth, base infra, alembic) with `generate_builtin`.
- **TODO-driven workflow** — anything that requires understanding (custom validation, business rules) is left as a clearly-marked TODO instead of being guessed.

## Installation

The server runs via `uvx`, so you don't need to install anything globally — just configure your MCP client to invoke it.

### Claude Desktop / Claude Code

Add to your `claude_desktop_config.json` or `~/.claude.json`:

```json
{
  "mcpServers": {
    "hexagonal-generator": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "fastapi-hexagon-mcp",
        "hexagonal-mcp"
      ],
      "env": {}
    }
  }
}
```

Pin a specific version with `fastapi-hexagon-mcp==X.Y.Z` if you need reproducibility.

### Manual install

```bash
pip install fastapi-hexagon-mcp
hexagonal-mcp  # runs the server over stdio
```

## Usage

Once configured, prompt your LLM in natural language. Example:

> Generate a CRUD module called **Product** using the hexagonal-generator MCP. Define its fields: `name` (str, max 100, searchable), `price` (float, required), `description` (str, max 500, nullable), and `category` (str, max 50, searchable). Add a validation: `name` must start with `"PRODUCT: "`. Then generate a module **Store** with `name` (str, max 100, searchable), `address` (str, required), and `products` (foreign key to Product). Wire the modules and complete all remaining TODOs.

The model will orchestrate the MCP tools below to produce a working project.

## Tools

| Tool | What it does |
|---|---|
| `generate_builtin` | Bootstrap a project skeleton (auth, base infra, alembic). |
| `generate_crud` | Scaffold a new CRUD module's files across all layers. |
| `define_fields` | Add fields to a module and propagate them to entities, models, schemas, repositories, and filters. |
| `add_relationship` | Add a foreign-key relationship between two modules. |
| `wire_module` | Register a module's dependencies (repository + use cases) in the DI container and routes. |
| `list_todos` | List remaining TODOs in a module so the LLM can complete them. |
| `complete_todos` | Help complete TODOs that need judgment (custom validation, business rules). |

## Typical workflow

1. `generate_builtin` — create the project skeleton.
2. `generate_crud` — scaffold a module.
3. `define_fields` — fill in the fields.
4. `add_relationship` (optional) — connect modules.
5. `wire_module` — plug it into the app.
6. `list_todos` / `complete_todos` — finish the parts that need understanding.

## Generated project layout

```
src/
└── <module>/
    ├── domain/
    │   ├── entities.py        # dataclasses
    │   └── repositories.py    # repository protocol
    ├── application/
    │   ├── schemas.py         # Pydantic request/response models
    │   └── use_cases.py       # business logic
    ├── infrastructure/
    │   ├── models.py          # SQLAlchemy ORM
    │   └── database.py        # repository implementation
    └── routes.py              # FastAPI router
```

## Requirements

- Python ≥ 3.10
- `uvx` (or `pip` + a venv) to run the server
- An MCP-compatible client (Claude Desktop, Claude Code, or any other)

## Links

- [Repository](https://github.com/JhonSanz/fastapi-hexagon-generator-mcp)
- [Issue tracker](https://github.com/JhonSanz/fastapi-hexagon-generator-mcp/issues)
- [Underlying generator: `fastapi-hexagon`](https://github.com/JhonSanz/empty-fastapi-hexagonal)
- [Model Context Protocol](https://modelcontextprotocol.io)

## License

MIT — see [LICENSE](LICENSE).

"""Tool schema definitions for the MCP server."""

from mcp.types import Tool

from hexagon_generator.core.config import BUILTIN_APPS_CONFIG


TOOLS: list[Tool] = [
    Tool(
        name="generate_crud",
        description=(
            "Generate a complete CRUD module following hexagonal architecture. "
            "Creates domain entities, repositories, use cases, Pydantic schemas, ORM models, and API routes. "
            "The generated code includes TODO comments that can be completed with define_fields, wire_module, and complete_todos."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Name of the module in PascalCase or snake_case (e.g., 'School' or 'school')",
                },
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the FastAPI project directory (e.g., '/home/user/my-project')",
                },
            },
            "required": ["module_name", "project_path"],
        },
    ),
    Tool(
        name="define_fields",
        description=(
            "Define fields for a module and propagate them across all hexagonal layers. "
            "Automatically completes field-related TODOs in domain entities, ORM models, "
            "Pydantic schemas, and repository mappers. Run this after generate_crud."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Name of the module (e.g., 'school')",
                },
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the FastAPI project directory (e.g., '/home/user/my-project')",
                },
                "fields": {
                    "type": "array",
                    "description": "List of field definitions to propagate",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Field name in snake_case (e.g., 'student_count')",
                            },
                            "type": {
                                "type": "string",
                                "description": "Python type. Built-in supported: str, int, float, bool, datetime, date, Decimal. Any other type (e.g., UUID, dict, list) will be placed as a TODO for manual completion.",
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "Max length for string fields (generates String(N) in SQLAlchemy)",
                            },
                            "min_length": {
                                "type": "integer",
                                "description": "Min length for string fields",
                            },
                            "nullable": {
                                "type": "boolean",
                                "description": "Whether the field allows null (default: false)",
                            },
                            "description": {
                                "type": "string",
                                "description": "Human-readable description for API docs",
                            },
                            "searchable": {
                                "type": "boolean",
                                "description": "Whether this field is searchable/filterable (default: false)",
                            },
                            "gt": {"type": "number", "description": "Greater than constraint"},
                            "ge": {"type": "number", "description": "Greater than or equal constraint"},
                            "lt": {"type": "number", "description": "Less than constraint"},
                            "le": {"type": "number", "description": "Less than or equal constraint"},
                        },
                        "required": ["name", "type"],
                    },
                },
            },
            "required": ["module_name", "project_path", "fields"],
        },
    ),
    Tool(
        name="add_relationship",
        description=(
            "Add a relationship between two existing modules. "
            "Generates ForeignKey columns, relationship() declarations in ORM models, "
            "FK fields in domain entities, and mapper updates. "
            "Schemas are left as TODOs for the LLM to decide nesting strategy. "
            "Both modules must already exist (run generate_crud + define_fields first)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "source_module": {
                    "type": "string",
                    "description": "The 'one' side or owner module (e.g., 'store' in store-has-many-products)",
                },
                "target_module": {
                    "type": "string",
                    "description": "The 'many' side or owned module (e.g., 'product' in store-has-many-products)",
                },
                "relation_type": {
                    "type": "string",
                    "enum": ["one_to_many", "many_to_many", "one_to_one"],
                    "description": "Type of relationship: one_to_many (FK on target), many_to_many (association table), one_to_one (FK+unique on target)",
                },
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the FastAPI project directory",
                },
                "nullable": {
                    "type": "boolean",
                    "description": "Whether the FK allows null (default: false). Only applies to one_to_many and one_to_one.",
                },
            },
            "required": ["source_module", "target_module", "relation_type", "project_path"],
        },
    ),
    Tool(
        name="list_todos",
        description=(
            "Scan a generated module for TODO comments and return them organized by file and category. "
            "Helps identify what needs to be completed in the generated code."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Name of the module to scan (e.g., 'school')",
                },
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the FastAPI project directory (e.g., '/home/user/my-project')",
                },
            },
            "required": ["module_name", "project_path"],
        },
    ),
    Tool(
        name="explain_todos",
        description=(
            "Return structured guidance for the actionable TODOs in a file: each TODO with its "
            "surrounding code context plus per-layer rules. The LLM is expected to implement each "
            "TODO using this guidance — this tool does not modify the file. "
            "For field declarations use define_fields instead."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file containing TODOs to explain",
                },
                "context": {
                    "type": "string",
                    "description": "Optional domain context to include in the response (e.g., business rules)",
                },
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="generate_builtin",
        description=(
            "Copy a pre-built optional module into the project. "
            "These are fully implemented modules (not CRUD scaffolds) that provide common functionality. "
            f"Available modules: {', '.join(BUILTIN_APPS_CONFIG.available_apps)}. "
            "Only use this when the user explicitly requests one of these modules."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": f"Name of the built-in module to copy. Available: {', '.join(BUILTIN_APPS_CONFIG.available_apps)}",
                    "enum": BUILTIN_APPS_CONFIG.available_apps,
                },
                "project_path": {
                    "type": "string",
                    "description": "Absolute path to the FastAPI project directory (e.g., '/home/user/my-project')",
                },
            },
            "required": ["app_name", "project_path"],
        },
    ),
]

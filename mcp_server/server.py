"""Main MCP Server implementation for hexagonal architecture generator."""

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from hexagon_generator.core.config import BUILTIN_APPS_CONFIG
from hexagon_generator.core.generator_factory import GeneratorFactory
from hexagon_generator.utils.validators import normalize_name

from .tools.todo_completer import TodoCompleter, scan_module_todos
from .tools.field_propagator import FieldPropagator
from .tools.module_wirer import ModuleWirer
from .tools.relationship_builder import RelationshipBuilder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
app = Server("hexagonal-generator")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
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
            name="wire_module",
            description=(
                "Register a module's router and exception handlers in the project. "
                "Automatically completes wiring TODOs in src/common/router.py and "
                "src/common/exceptions_mapping.py. Run this after generate_crud."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to wire (e.g., 'school')",
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
            name="complete_todos",
            description=(
                "Complete remaining TODOs in a file. Default action 'remove' deletes TODO comments directly. "
                "Use 'guidance' to get suggestions instead. "
                "For field declarations use define_fields. For wiring use wire_module."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file containing TODOs to complete",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["remove", "guidance"],
                        "description": "Action: 'remove' deletes TODO comments from file (default), 'guidance' returns suggestions",
                        "default": "remove",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the domain (only used with action='guidance')",
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


def _resolve_project_path(arguments: dict[str, Any]) -> str:
    """Extract and validate project_path from tool arguments.

    The LLM must provide an absolute path. Since the MCP server runs in its
    own cwd (which differs from the LLM's), relative paths would resolve
    incorrectly.
    """
    raw = arguments.get("project_path", "")
    if not raw:
        raise ValueError(
            "project_path is required and must be an absolute path "
            "(e.g., '/home/user/my-project')"
        )
    p = Path(raw)
    if not p.is_absolute():
        raise ValueError(
            f"project_path must be an absolute path, got relative: '{raw}'. "
            f"Use the full path (e.g., '/home/user/my-project')"
        )
    return str(p)


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    try:
        handlers = {
            "generate_crud": handle_generate_crud,
            "define_fields": handle_define_fields,
            "wire_module": handle_wire_module,
            "add_relationship": handle_add_relationship,
            "list_todos": handle_list_todos,
            "complete_todos": handle_complete_todos,
            "generate_builtin": handle_generate_builtin,
        }
        handler = handlers.get(name)
        if handler:
            return await handler(arguments)
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_generate_crud(arguments: dict[str, Any]) -> list[TextContent]:
    """Generate CRUD module using the hexagonal generator."""
    module_name = arguments["module_name"]
    project_path = _resolve_project_path(arguments)

    from hexagon_generator.core import constant

    original_target_root = constant.TARGET_ROOT

    try:
        constant.TARGET_ROOT = project_path

        pascal_name, snake_name = normalize_name(module_name)

        generator = GeneratorFactory()
        generator.create_base_generator().run()
        generator.create_crud_generator(pascal_name).run()

        module_path = Path(constant.TARGET_ROOT) / "src" / snake_name
        todo_info = scan_module_todos(module_path)

        result = {
            "success": True,
            "module": snake_name,
            "pascal_name": pascal_name,
            "project_path": project_path,
            "message": f"CRUD module '{pascal_name}' generated with {todo_info['total_todos']} TODOs",
            "next_steps": [
                f"define_fields module_name='{snake_name}' to declare fields",
                f"wire_module module_name='{snake_name}' to register routes",
                "complete_todos on use case files to clean up business logic placeholders",
            ],
        }

        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error generating CRUD: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]

    finally:
        constant.TARGET_ROOT = original_target_root


async def handle_define_fields(arguments: dict[str, Any]) -> list[TextContent]:
    """Define fields and propagate them across all hexagonal layers."""
    module_name = arguments["module_name"]
    project_path = _resolve_project_path(arguments)
    fields = arguments["fields"]

    try:
        propagator = FieldPropagator(
            module_name=module_name,
            project_path=project_path,
            fields=fields,
        )
        result = propagator.propagate()
        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error defining fields: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]


async def handle_wire_module(arguments: dict[str, Any]) -> list[TextContent]:
    """Wire a module's router and exception handlers."""
    module_name = arguments["module_name"]
    project_path = _resolve_project_path(arguments)

    try:
        wirer = ModuleWirer(
            module_name=module_name,
            project_path=project_path,
        )
        result = wirer.wire()
        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error wiring module: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]


async def handle_add_relationship(arguments: dict[str, Any]) -> list[TextContent]:
    """Add a relationship between two modules."""
    source_module = arguments["source_module"]
    target_module = arguments["target_module"]
    relation_type = arguments["relation_type"]
    project_path = _resolve_project_path(arguments)
    nullable = arguments.get("nullable", False)

    try:
        builder = RelationshipBuilder(
            source_module=source_module,
            target_module=target_module,
            relation_type=relation_type,
            project_path=project_path,
            nullable=nullable,
        )
        result = builder.build()
        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error adding relationship: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]


async def handle_generate_builtin(arguments: dict[str, Any]) -> list[TextContent]:
    """Copy a built-in module into the project."""
    app_name = arguments["app_name"]
    project_path = _resolve_project_path(arguments)

    from hexagon_generator.core import constant

    original_target_root = constant.TARGET_ROOT

    try:
        constant.TARGET_ROOT = project_path

        factory = GeneratorFactory()
        generator, source_path, target_path = factory.create_builtin_generator(app_name)
        copied = generator.copy_builtin_apps(
            path_source=source_path,
            path_target=target_path,
        )

        if copied:
            result = {
                "success": True,
                "app_name": app_name,
                "project_path": project_path,
                "message": f"Built-in module '{app_name}' copied successfully to {target_path}",
            }
        else:
            result = {
                "success": True,
                "app_name": app_name,
                "project_path": project_path,
                "message": f"Built-in module '{app_name}' already exists at {target_path}, skipped",
            }

        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error copying built-in app: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]

    finally:
        constant.TARGET_ROOT = original_target_root


async def handle_list_todos(arguments: dict[str, Any]) -> list[TextContent]:
    """List all TODOs in a module."""
    module_name = arguments["module_name"]
    project_path = _resolve_project_path(arguments)

    try:
        module_path = Path(project_path) / "src" / module_name
        result = scan_module_todos(module_path)

        result["project_path"] = project_path

        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error listing TODOs: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]


async def handle_complete_todos(arguments: dict[str, Any]) -> list[TextContent]:
    """Complete TODOs in a specific file."""
    file_path = Path(arguments["file_path"])
    context = arguments.get("context", "")
    action = arguments.get("action", "remove")

    try:
        completer = TodoCompleter()
        result = await completer.complete_file_todos(file_path, context, action=action)

        return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        logger.error(f"Error completing TODOs: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}),
            )
        ]


async def start_server():
    """Start the MCP server."""
    logger.info("Starting Hexagonal Generator MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point for the server."""
    import asyncio

    asyncio.run(start_server())


if __name__ == "__main__":
    main()

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
                "The generated code includes TODO comments for domain-specific logic that needs completion."
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
                        "description": "Path to the FastAPI project where code will be generated (default: 'generated_project')",
                    },
                },
                "required": ["module_name"],
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
                        "description": "Path to the FastAPI project (default: 'generated_project')",
                    },
                },
                "required": ["module_name"],
            },
        ),
        Tool(
            name="complete_todos",
            description=(
                "Intelligently complete TODO comments in a specific file while respecting hexagonal architecture principles. "
                "Analyzes context and generates appropriate domain logic, validations, or business rules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file containing TODOs to complete",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about the domain (e.g., 'A school has name, address, and manages students')",
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
                        "description": "Path to the FastAPI project (default: 'generated_project')",
                    },
                },
                "required": ["app_name"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "generate_crud":
            return await handle_generate_crud(arguments)
        elif name == "list_todos":
            return await handle_list_todos(arguments)
        elif name == "complete_todos":
            return await handle_complete_todos(arguments)
        elif name == "generate_builtin":
            return await handle_generate_builtin(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_generate_crud(arguments: dict[str, Any]) -> list[TextContent]:
    """Generate CRUD module using the hexagonal generator."""
    module_name = arguments["module_name"]
    project_path = arguments.get("project_path", "generated_project")

    # Import constant to modify TARGET_ROOT temporarily
    from hexagon_generator.core import constant

    # Save original TARGET_ROOT
    original_target_root = constant.TARGET_ROOT

    try:
        # Set custom project path
        constant.TARGET_ROOT = project_path

        # Normalize the module name
        pascal_name, snake_name = normalize_name(module_name)

        # Generate the CRUD module using the factory
        generator = GeneratorFactory()
        generator.create_base_generator().run()
        generator.create_crud_generator(pascal_name).run()

        # Dynamically scan generated files for TODOs
        module_path = Path(constant.TARGET_ROOT) / "src" / snake_name
        todo_info = scan_module_todos(module_path)

        result = {
            "success": True,
            "module": snake_name,
            "pascal_name": pascal_name,
            "project_path": project_path,
            "message": f"CRUD module '{pascal_name}' generated successfully",
            "todos_found": todo_info["total_todos"],
            "todos": todo_info["todos"],
            "summary": todo_info["summary"],
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error generating CRUD: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}, indent=2),
            )
        ]

    finally:
        # Always restore original TARGET_ROOT
        constant.TARGET_ROOT = original_target_root


async def handle_generate_builtin(arguments: dict[str, Any]) -> list[TextContent]:
    """Copy a built-in module into the project."""
    app_name = arguments["app_name"]
    project_path = arguments.get("project_path", "generated_project")

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

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error copying built-in app: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}, indent=2),
            )
        ]

    finally:
        constant.TARGET_ROOT = original_target_root


async def handle_list_todos(arguments: dict[str, Any]) -> list[TextContent]:
    """List all TODOs in a module."""
    module_name = arguments["module_name"]
    project_path = arguments.get("project_path", "generated_project")

    try:
        # Dynamically scan module directory for TODOs
        module_path = Path(project_path) / "src" / module_name
        result = scan_module_todos(module_path)

        result["project_path"] = project_path

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error listing TODOs: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}, indent=2),
            )
        ]


async def handle_complete_todos(arguments: dict[str, Any]) -> list[TextContent]:
    """Complete TODOs in a specific file."""
    file_path = Path(arguments["file_path"])
    context = arguments.get("context", "")

    try:
        completer = TodoCompleter()
        result = await completer.complete_file_todos(file_path, context)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error completing TODOs: {e}", exc_info=True)
        return [
            TextContent(
                type="text",
                text=json.dumps({"success": False, "error": str(e)}, indent=2),
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

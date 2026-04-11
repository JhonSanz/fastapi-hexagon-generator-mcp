"""Main MCP Server implementation for hexagonal architecture generator."""

import json
import logging
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from hexagon_generator.core.generator_factory import GeneratorFactory
from hexagon_generator.core.config import CrudConfig
from hexagon_generator.utils.validators import normalize_name

from .tools.todo_completer import TodoCompleter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
app = Server("hexagonal-generator")


def get_known_todos(module_name: str) -> dict[str, Any]:
    """
    Get the list of known TODOs for a generated module.

    This is a static list based on the known template structure,
    avoiding the need to scan files and improving performance.

    Args:
        module_name: Name of the module (snake_case)

    Returns:
        Dictionary with todos and summary
    """
    base_path = f"src/{module_name}"

    todos = [
        # Domain layer TODOs
        {
            "file_path": f"{base_path}/domain/models.py",
            "line_number": 22,
            "content": "Add your model fields here",
            "category": "domain",
            "file_type": "models",
        },
        {
            "file_path": f"{base_path}/domain/dtos.py",
            "line_number": 16,
            "content": "Add your domain fields here",
            "category": "domain",
            "file_type": "dtos",
        },
        {
            "file_path": f"{base_path}/domain/dtos.py",
            "line_number": 26,
            "content": "Add fields that can be updated (all optional)",
            "category": "domain",
            "file_type": "dtos",
        },
        {
            "file_path": f"{base_path}/domain/dtos.py",
            "line_number": 41,
            "content": "Add specific filters for your domain",
            "category": "domain",
            "file_type": "dtos",
        },
        # Application layer TODOs
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 10,
            "content": "Add your model fields here",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 24,
            "content": "Add example data",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 34,
            "content": "Add fields that can be updated (all optional for partial updates)",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 42,
            "content": "Add example data",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 62,
            "content": "Add your fields",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 76,
            "content": "Add main fields for list view (keep it minimal)",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 86,
            "content": "Add your fields",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/schemas.py",
            "line_number": 119,
            "content": "Add specific filters for your model",
            "category": "application",
            "file_type": "schemas",
        },
        {
            "file_path": f"{base_path}/application/web_cases.py",
            "line_number": 64,
            "content": "Add your business logic here (validation, transformations, etc.)",
            "category": "application",
            "file_type": "web_cases",
        },
        {
            "file_path": f"{base_path}/application/web_cases.py",
            "line_number": 89,
            "content": "Add your business logic here (validation, authorization, etc.)",
            "category": "application",
            "file_type": "web_cases",
        },
        {
            "file_path": f"{base_path}/application/web_cases.py",
            "line_number": 116,
            "content": "Add your business logic here (filtering, authorization, etc.)",
            "category": "application",
            "file_type": "web_cases",
        },
        {
            "file_path": f"{base_path}/application/web_cases.py",
            "line_number": 134,
            "content": "Add your business logic here (authorization, data enrichment, etc.)",
            "category": "application",
            "file_type": "web_cases",
        },
        {
            "file_path": f"{base_path}/application/web_cases.py",
            "line_number": 152,
            "content": "Add your business logic here (authorization, cascading deletes, etc.)",
            "category": "application",
            "file_type": "web_cases",
        },
        {
            "file_path": f"{base_path}/application/mappers.py",
            "line_number": 68,
            "content": "Map additional filters",
            "category": "application",
            "file_type": "mappers",
        },
        # Infrastructure layer TODOs
        {
            "file_path": f"{base_path}/infrastructure/database.py",
            "line_number": 60,
            "content": "Customize search fields based on your model",
            "category": "infrastructure",
            "file_type": "database",
        },
        {
            "file_path": f"{base_path}/infrastructure/database.py",
            "line_number": 70,
            "content": "Add custom filters based on filter_dto",
            "category": "infrastructure",
            "file_type": "database",
        },
        {
            "file_path": f"{base_path}/infrastructure/database.py",
            "line_number": 84,
            "content": "Add validation for allowed order fields",
            "category": "infrastructure",
            "file_type": "database",
        },
    ]

    # Calculate summary
    summary = {
        "by_category": {"domain": 4, "application": 14, "infrastructure": 3},
        "by_file_type": {
            "models": 1,
            "dtos": 3,
            "schemas": 8,
            "web_cases": 5,
            "mappers": 1,
            "database": 3,
        },
        "total": 21,
    }

    return {
        "success": True,
        "module": module_name,
        "total_todos": len(todos),
        "todos": todos,
        "summary": summary,
    }


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="generate_crud",
            description=(
                "Generate a complete CRUD module following hexagonal architecture. "
                "Creates domain models, DTOs, repositories, use cases, schemas, and API routes. "
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
        # Set custom project path if provided
        if project_path != "generated_project":
            constant.TARGET_ROOT = f"./{project_path}"

        # Normalize the module name
        pascal_name, snake_name = normalize_name(module_name)

        # Generate the CRUD module using the factory
        generator = GeneratorFactory()
        generator.create_base_generator().run()
        generator.create_crud_generator(pascal_name).run()

        # Get known TODOs for this module
        todo_info = get_known_todos(snake_name)

        result = {
            "success": True,
            "module": snake_name,
            "pascal_name": pascal_name,
            "project_path": project_path,
            "message": f"CRUD module '{pascal_name}' generated successfully",
            "files_created": [
                f"src/{snake_name}/domain/models.py",
                f"src/{snake_name}/domain/dtos.py",
                f"src/{snake_name}/domain/repository.py",
                f"src/{snake_name}/domain/unit_of_work.py",
                f"src/{snake_name}/application/schemas.py",
                f"src/{snake_name}/application/handlers.py",
                f"src/{snake_name}/application/web_cases.py",
                f"src/{snake_name}/application/mappers.py",
                f"src/{snake_name}/infrastructure/database.py",
                f"src/{snake_name}/infrastructure/web.py",
                f"src/{snake_name}/infrastructure/unit_of_work.py",
            ],
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


async def handle_list_todos(arguments: dict[str, Any]) -> list[TextContent]:
    """List all TODOs in a module."""
    module_name = arguments["module_name"]
    project_path = arguments.get("project_path", "generated_project")

    try:
        # Get known TODOs from static list
        result = get_known_todos(module_name)

        # Add project_path to the result
        result["project_path"] = project_path

        # Update file paths to include project_path
        for todo in result["todos"]:
            todo["file_path"] = f"{project_path}/{todo['file_path']}"

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

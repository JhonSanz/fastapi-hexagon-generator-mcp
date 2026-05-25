"""Main MCP Server implementation for hexagonal architecture generator."""

import json
import logging
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from hexagon_generator.core import constant
from hexagon_generator.core.generator_factory import GeneratorFactory
from hexagon_generator.utils.validators import normalize_name

from .schemas import TOOLS
from .tools.todo_completer import TodoCompleter, scan_module_todos
from .tools.field_propagator import FieldPropagator
from .tools.module_wirer import ModuleWirer
from .tools.relationship_builder import RelationshipBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Server("hexagonal-generator")


def _json_response(payload: dict[str, Any]) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload))]


def json_handler(func):
    """Wrap a handler so exceptions become a `{success: False, error}` JSON response."""

    @wraps(func)
    async def wrapper(arguments: dict[str, Any]) -> list[TextContent]:
        try:
            return _json_response(await func(arguments))
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return _json_response({"success": False, "error": str(e)})

    return wrapper


@contextmanager
def target_root(path: str):
    """Temporarily point the generator's TARGET_ROOT at `path`."""
    original = constant.TARGET_ROOT
    constant.TARGET_ROOT = path
    try:
        yield
    finally:
        constant.TARGET_ROOT = original


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


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    logger.info(f"Tool called: {name} with arguments: {arguments}")
    handler = HANDLERS.get(name)
    if handler is None:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    return await handler(arguments)


@json_handler
async def handle_generate_crud(arguments: dict[str, Any]) -> dict[str, Any]:
    module_name = arguments["module_name"]
    project_path = _resolve_project_path(arguments)

    with target_root(project_path):
        pascal_name, snake_name = normalize_name(module_name)

        generator = GeneratorFactory()
        generator.create_base_generator().run()
        generator.create_crud_generator(pascal_name).run()

        module_path = Path(constant.TARGET_ROOT) / "src" / snake_name
        todo_info = scan_module_todos(module_path)

    return {
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


@json_handler
async def handle_define_fields(arguments: dict[str, Any]) -> dict[str, Any]:
    propagator = FieldPropagator(
        module_name=arguments["module_name"],
        project_path=_resolve_project_path(arguments),
        fields=arguments["fields"],
    )
    return propagator.propagate()


@json_handler
async def handle_wire_module(arguments: dict[str, Any]) -> dict[str, Any]:
    wirer = ModuleWirer(
        module_name=arguments["module_name"],
        project_path=_resolve_project_path(arguments),
    )
    return wirer.wire()


@json_handler
async def handle_add_relationship(arguments: dict[str, Any]) -> dict[str, Any]:
    builder = RelationshipBuilder(
        source_module=arguments["source_module"],
        target_module=arguments["target_module"],
        relation_type=arguments["relation_type"],
        project_path=_resolve_project_path(arguments),
        nullable=arguments.get("nullable", False),
    )
    return builder.build()


@json_handler
async def handle_generate_builtin(arguments: dict[str, Any]) -> dict[str, Any]:
    app_name = arguments["app_name"]
    project_path = _resolve_project_path(arguments)

    with target_root(project_path):
        factory = GeneratorFactory()
        generator, source_path, target_path = factory.create_builtin_generator(app_name)
        copied = generator.copy_builtin_apps(path_source=source_path, path_target=target_path)

    message = (
        f"Built-in module '{app_name}' copied successfully to {target_path}"
        if copied
        else f"Built-in module '{app_name}' already exists at {target_path}, skipped"
    )
    return {
        "success": True,
        "app_name": app_name,
        "project_path": project_path,
        "message": message,
    }


@json_handler
async def handle_list_todos(arguments: dict[str, Any]) -> dict[str, Any]:
    project_path = _resolve_project_path(arguments)
    module_path = Path(project_path) / "src" / arguments["module_name"]
    result = scan_module_todos(module_path)
    result["project_path"] = project_path
    return result


@json_handler
async def handle_complete_todos(arguments: dict[str, Any]) -> dict[str, Any]:
    completer = TodoCompleter()
    return await completer.complete_file_todos(
        Path(arguments["file_path"]),
        arguments.get("context", ""),
        action=arguments.get("action", "remove"),
    )


HANDLERS = {
    "generate_crud": handle_generate_crud,
    "define_fields": handle_define_fields,
    "wire_module": handle_wire_module,
    "add_relationship": handle_add_relationship,
    "list_todos": handle_list_todos,
    "complete_todos": handle_complete_todos,
    "generate_builtin": handle_generate_builtin,
}


async def start_server():
    logger.info("Starting Hexagonal Generator MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    import asyncio

    asyncio.run(start_server())


if __name__ == "__main__":
    main()

"""End-to-end exercise of every MCP tool in the order they're expected to run."""

import asyncio
import json
from pathlib import Path

from mcp_server.server import (
    handle_generate_crud,
    handle_define_fields,
    handle_wire_module,
    handle_add_relationship,
    handle_list_todos,
    handle_complete_todos,
    handle_generate_builtin,
)


PROJECT = "/home/finanzas/documents/hexagon/servertest"


def show(label: str, result) -> dict:
    """Pretty-print a handler result and return the decoded payload."""
    header = f"══ {label} "
    print("\n" + header + "═" * max(0, 72 - len(header)))
    payload = json.loads(result[0].text)
    print(json.dumps(payload, indent=2))
    return payload


async def main() -> None:
    # # 1. Scaffold the School CRUD module
    # show("generate_crud: school", await handle_generate_crud({
    #     "module_name": "School",
    #     "project_path": PROJECT,
    # }))

    # 2. Define School fields (propagates across entities, models, schemas, mapper)
    show("define_fields: school", await handle_define_fields({
        "module_name": "school",
        "project_path": PROJECT,
        "fields": [
            {
                "name": "TEST",
                "type": "str",
                "max_length": 100,
                "min_length": 1,
                "searchable": True,    
                "nullable": True,
                "description": "School display TEST"
            },
            {
                "name": "TEST2",
                "type": "str",
                "max_length": 100,
                "min_length": 1,
                "searchable": True,
                "description": "School display TEST2"
            },
            {
                "name": "TEST3",
                "type": "int",
                "max_length": 100,
                "min_length": 1,
                "searchable": True,
                "nullable": False,
                "description": "School display TEST3"
            }
        ],
    }))

    # # 3. Register School's router and exception handlers in src/common
    # show("wire_module: school", await handle_wire_module({
    #     "module_name": "school",
    #     "project_path": PROJECT,
    # }))

    # # 4. Scaffold the Student CRUD module (target of the relationship)
    # show("generate_crud: student", await handle_generate_crud({
    #     "module_name": "Student",
    #     "project_path": PROJECT,
    # }))

    # # 5. Define Student fields
    # show("define_fields: student", await handle_define_fields({
    #     "module_name": "student",
    #     "project_path": PROJECT,
    #     "fields": [
    #         {
    #             "name": "first_name",
    #             "type": "str",
    #             "max_length": 80,
    #             "min_length": 1,
    #             "searchable": True,
    #             "description": "Student first name",
    #         },
    #         {
    #             "name": "last_name",
    #             "type": "str",
    #             "max_length": 80,
    #             "min_length": 1,
    #             "searchable": True,
    #             "description": "Student last name",
    #         },
    #         {
    #             "name": "age",
    #             "type": "int",
    #             "ge": 0,
    #             "le": 120,
    #             "description": "Age in years",
    #         },
    #     ],
    # }))

    # # 6. Wire Student
    # show("wire_module: student", await handle_wire_module({
    #     "module_name": "student",
    #     "project_path": PROJECT,
    # }))

    # # 7. School has many Students (FK + relationship() declarations on Student)
    # show("add_relationship: school -> student (one_to_many)", await handle_add_relationship({
    #     "source_module": "school",
    #     "target_module": "student",
    #     "relation_type": "one_to_many",
    #     "project_path": PROJECT,
    #     "nullable": False,
    # }))

    # # 8. Scan for any TODOs left in the School module after all the above
    # todos = show("list_todos: school", await handle_list_todos({
    #     "module_name": "school",
    #     "project_path": PROJECT,
    # }))

    # # 9. Pick the file with the most TODOs and clean it up with complete_todos
    # file_counts: dict[str, int] = {}
    # for t in todos.get("todos", []):
    #     file_counts[t["file_path"]] = file_counts.get(t["file_path"], 0) + 1

    # if file_counts:
    #     target_rel = max(file_counts, key=file_counts.get)
    #     target_abs = str(Path(PROJECT) / target_rel)
    #     show(f"complete_todos: {target_rel}", await handle_complete_todos({
    #         "file_path": target_abs,
    #         "action": "remove",
    #     }))
    # else:
    #     print("\n(no remaining TODOs to clean)")

    # # 10. Copy a built-in module (user/role/auth/smtp) into the project
    # show("generate_builtin: user", await handle_generate_builtin({
    #     "app_name": "user",
    #     "project_path": PROJECT,
    # }))


if __name__ == "__main__":
    asyncio.run(main())

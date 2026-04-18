# debug.py en /home/finanzas/documents/hexagon/hexagonal-mcp-server/
import asyncio
from mcp_server.server import handle_list_todos, handle_define_fields 

async def main():
    result = await handle_define_fields({
        "module_name": "school",
        "project_path": "/home/finanzas/documents/hexagon/servertest",
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
        ]
    })
    print(result[0].text)

asyncio.run(main())
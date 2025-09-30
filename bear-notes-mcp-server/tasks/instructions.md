# Instructions

Build an MCP server hat queries the chromadb database enriched with vector embeddings with the pipeline bear-notes-parser -> bear-notes-cag-data-creator.
The tool should expose a manifest to be used in desktop tools like Claude Desktop and a custom command line tool that I am going to build in the future.
Some implementation (the CAG queries) is ready in the file test-files/chromadb_query_client.py, we need to take some code from there and build the MCP server around it.
The tool this MCP server will expose will be only one: markdown_notes_search and will accept only one parameter that is the user_query.
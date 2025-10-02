# Instructions

This application will be an MCP server that queries a chromadb database enriched with vector embeddings from the pipeline

1. bear-notes-parser (or zim-articles-parser)
2. markdown-notes-cag-data-creator.

The application should expose a manifest to be used in desktop tools like Claude Desktop and a custom command line tool that I am going to build in the future.
Some implementation (the CAG queries) is ready in the file test-files/chromadb_query_client.py, we need to take some code from there and build the MCP server around it.

The "tools" this MCP server will expose will be only one: markdown_notes_search and will accept only one parameter that is the user_query.
A problem that hasn't been solved (yet) is the fact that the chromadb database may contain different collections, one for bear notes, another from a zim file and maybe a third one with markdown taken from, for example, a website documentation.
We need to figure out:

- if this is really possible: it is only a matter of running markdown-notes-cag-data-creator with a different collection name, isn't it? and this is already possible or we need to tweak the tool? we need to look at its implementation.
- how to build the MCP server in order to query the different collections?
  - one option is to get the collection name from the input request but this will force the AI based applications that will use it to add this parameter to the query, but this will be in the hands of the AI, will it be able to do something like: if the user asks something about my notes, the MCP will be instructed to use a certain collection, if the user asks something about my codebase, MCP will use a collection made from my repository doc md files and so on. 
  - another option, which seems easier but has its downsizes, is to provide different tools in the MCP: bear_notes_search, wiki_search and so on but then the manifest will depend on the database collections, which looks like a weak point
  - a third option is to use different MCP instances, one for the notes, another for wiki content, a third for my documentation. That means providing different manifests, each has a different input param to send to the command to start the MCP; again we are making a link between an hardcoded information (the manifest) and a dynamically available source (the collection), I'm not sure I like it 
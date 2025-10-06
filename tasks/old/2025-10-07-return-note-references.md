# Return note references

The MCP server works as expected, we just need to improve its response.
We need to return to the AI using the tool (and thus to the user making the request) the reference where the information has been found.

Being a multi-origin MCP server, we will use a generic term like "reference" that will contain different information depending on the origin of the source. For example, for Bear Notes this will be the note title, something similar will be for wikipedia articles but one day, when we will be able to index my company wiki, I will return the wiki page URL.

This improvement will potentially affect all the projects, so we will need to

- [ ] check that these two tools already return this information: bear-notes-extractor and zim-article-parser
- [ ] check that this information is embedded in the database looking at markdown-notes-cag-data-creator
- [ ] check that the information is returned to the user looking at markdown-notes-mcp-server
- [ ] prepare a PRD to implement what is missing according to our previous checks
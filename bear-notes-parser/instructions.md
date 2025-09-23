# instructions

Build a tool that receives in input a bear notes backup and returns note contents along with their metadata, neglecting assets.
We will use phyton as a development technology
Bear notes backup is a zip file with a .bear2bk extension. Inside the archive there is a list of notes in the textbundle format (and a json file that we will ignore).

A TextBundle is a folder with this structure:

* info.json
* text.markdown - this file contains the note text in markdown format
* assets folder 

Example of an info.json

```json
{
  "creatorIdentifier" : "net.shinyfrog.bear",
  "net.shinyfrog.bear" : {
    "archived" : 1,
    "archivedDate" : "2024-06-14T16:24:38Z",
    "creationDate" : "2024-06-07T10:08:13Z",
    "lastEditingDevice" : "Michele MacBook Pro M2",
    "locked" : 0,
    "lockedDate" : null,
    "modificationDate" : "2024-06-14T05:56:56Z",
    "pinned" : 0,
    "pinnedDate" : "2024-06-14T05:57:04Z",
    "pinnedInTagTitles" : [

    ],
    "trashed" : 0,
    "trashedDate" : "2024-06-14T16:24:38Z",
    "uniqueIdentifier" : "B1C5CA69-462B-45A9-A063-A046FD2A12A1",
    "version" : 3
  },
  "transient" : false,
  "type" : "net.daringfireball.markdown",
  "version" : 2
}
```

The tool will be composed by a module that extract all these information and return it as a result of a function call and by a command line utility to test it.
The function must return an array of all untrashed (info.json contains "trashed": 0) composed by

    title (use the name of the text bundle folder)
    markdown original content
    markdown original content size
    modificationDate - ISO format, standardize it if necessary

the output format will be a python array of objects containing the three fields.
The command line utility takes a bear2bk file as the only input and saves the returned array in JSON format to a file (overwriting the existing) with the same name of the input file and json extension.

Use utf-8 encoding.
Pure python is preferred to libraries.
There is no need for unit tests.

An example bear backup note you can use Bear Notes 2025-09-20 at 08.49.bear2bk in this folder.
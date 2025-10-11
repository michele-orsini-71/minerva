# Instructions: convert markdown books to a format suitable for CAG data creator

I found a set of markdown books divided by authors, the path is the following
'/Users/michele/my-code/classic-books-markdown`

we need to build a script that

- accepts an input file
- outputs a json data file with format test-data/Bear Notes 2025-10-11 at 10.17.json, that is the format expected by the CAG data creator (it is the file pointed in json_file field of its configuration file)

Now, a file like the one I gave you as an example, it is from a multi-notes bear application backup, so each entry describes a different note, here we are dealing with a book so I don't know how to proceed!

- modificationDate and creationDate are useless (no, I don't think that Lewis Carrol will publish a new version of Alice in wonderland!) but we can find when the book has been published
- I could use a block for each chapter maybe, keeping the chapter title as title, so when the MCP will search for a query, it will be able to report in which chapter the information lies

the other book information will be added to the collection metadata in the cag data creator phase
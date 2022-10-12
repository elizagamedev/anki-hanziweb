`config_version`
: This is used internally by Hanzi Web to ensure compatibility with future
  versions.

`search_query`
: Only notes will be considered which match this search query. If empty, this
  includes the entire database. You could use this to limit Hanzi Web's
  operation to specific decks, note types, tags, or other creative use-cases.
  See the [Anki manual on Searching](https://docs.ankiweb.net/searching.html#tags-decks-cards-and-notes).

`hanzi_fields_regexp`
: If a note is considered by Hanzi Web, any hanzi/kanji contained in fields
  whose names completely match this regular expression are used to build the
  web. See the [Python documentation on Regular expressions](https://docs.python.org/3/library/re.html).

`web_field`
: For each considered note, the output of the web will be placed in this field
  if it exists. This name is case-sensitive.

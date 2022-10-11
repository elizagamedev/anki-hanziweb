`config_version`
: This is used internally by Hanzi Web to ensure compatibility with future
  versions.

`include_decks_regexp`
: Notes which belong to decks whose names completely match the given regular
  expression will be considered by Hanzi Web.

`include_note_types_regexp`
: Notes which belong to note types whose names completely match the given
  regular expression will be considered by Hanzi Web.

`hanzi_fields_regexp`
: If a note is considered by Hanzi Web, any hanzi/kanji contained in fields
  whose names completely match this regular expression are used to build the
  web.

`web_field`
: For each considered note, the output of the web will be placed in this field
  if it exists.

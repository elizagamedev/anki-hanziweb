### `config_version`
This is used internally by Hanzi Web to ensure compatibility with future
versions. Keep this set to `0`.

Default: `0`.

### `hanzi_fields_regexp`
If a note is considered by Hanzi Web, any hanzi/kanji contained in fields whose
names *completely* match this case-sensitive regular expression are used as
terms to build the web. See the [Python documentation on Regular
expressions](https://docs.python.org/3/library/re.html).

Default: `"Expression"`

### `max_terms_per_hanzi`
This limits the list of terms to the N most recently reviewed notes. Set this to
`0` to remove the limit.

Default: `"5"`.

### `search_query`
Only notes will be considered which match this search query. If empty, this
includes the entire database. You could use this to limit Hanzi Web's operation
to specific decks, note types, tags, or other creative use-cases. See the [Anki
manual on Searching](https://docs.ankiweb.net/searching.html#tags-decks-cards-and-notes).

For example, to select only decks that contain the word “Chinese”:
`"deck:*Chinese*"`

Default: `""`.

### `term_separator`
This will be used to separate the list of terms on each note.

Default: `"、"`.

### `web_field`
For each considered note, the output of the web will be placed in this field if
it exists. This name is case-sensitive. You probably don't want to change this.

Default: `"HanziWeb"`.

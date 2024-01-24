### `auto_run_on_sync`
If `true`, automatically run Hanzi Web before and after each sync. With this
enabled, after you review cards on another device, you'll typically have to sync
twice in a row on the device that’s running Hanzi Web: once to download their
changes, and once again to synchronize the updated Hanzi Web entries.

Default: `false`.

### `config_version`
This is used internally by Hanzi Web to ensure compatibility with future
versions. If you are nagged about your configuration being out of date, please
update this value to `1`.

Default: `1`.

### `days_to_update`
If set to a value other than `0`, only the notes due within the next N days
(both new cards and reviews) will be updated. This can significantly improve the
speed at which Hanzi Web runs and improves AnkiWeb sync times.

Default: `0`.

### `hanzi_fields_regexp`
If a note is considered by Hanzi Web, any hanzi/kanji contained in fields whose
names *completely* match this case-sensitive regular expression are used as
terms to build the web. See the [Python documentation on Regular
expressions](https://docs.python.org/3/library/re.html).

Default: `"Expression"`

### `japanese_search_query`
A search query which is used to determine which notes to treat as Japanese,
rather than Chinese, the default. This is a subset of `search_query`. If empty,
*no notes* are considered to be Japanese; this is the *opposite behavior* of an
empty term for `search_query`, so be careful.

There are several differences in behavior when a note is considered Japanese.
Please see the README for a comprehensive explanation.

See the [Anki manual on
Searching](https://docs.ankiweb.net/searching.html#tags-decks-cards-and-notes).
See also the `kyujitai_field` configuration option.

For example, to select only decks that contain the word “Japanese”:
`"deck:*Japanese*"`. To select all of your notes, `"deck:*"`.

Default: `""`.

### `kyujitai_field`
For each Japanese note, its corresponding `kyujitai_field` will be updated with
the values of the fields matching `hanzi_fields_regexp`, converted to kyūjitai,
each time Hanzi Web is run. (It is assumed that `hanzi_fields_regexp` generally
will contain shinjitai forms.)

See also the `japanese_search_query` configuration option.

Default: `"Kyujitai"`.

### `max_terms_per_hanzi`
This limits the list of terms to the N most recently reviewed notes. Set this to
`0` to remove the limit.

Default: `5`.

### `search_query`
Only notes will be considered which match this search query. If empty, this
includes the entire database. You could use this to limit Hanzi Web’s operation
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
it exists. This name is case-sensitive. You probably don’t want to change this.

Default: `"HanziWeb"`.

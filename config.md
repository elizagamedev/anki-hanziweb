### `auto_run_on_sync`
If `true`, automatically run Hanzi Web before and after each sync. With this
enabled, after you review cards on another device, you'll typically have to sync
twice in a row on the device that's running Hanzi Web: once to download their
changes, and once again to synchronize the updated Hanzi Web entries.

Default: `false`.

### `click_hanzi_action`, `click_hanzi_term_action`, `click_phonetic_action`, `click_phonetic_term_action`
These four options configure what happens when you click certain items in Hanzi
Web. You can configure these to browse directly to the notes in Anki or
automatically open dictionary apps, for example.

- `click_hanzi_action` corresponds to the hanzi on the very left. Default:
  `":browse"`.
- `click_hanzi_term_action` corresponds to the individual terms on the right of
  the hanzi row. Default: `":edit"`.
- `click_phonetic_action` corresponds to the phonetic component characters (音符)
  on the left. Default: `":browse"`.
- `click_phonetic_term_action` corresponds to the individual terms on the right
  of the phonetic component row. Default: `":edit"`.

These four options can be set the any of the following values.

#### `":none"`
Nothing happens when this item is clicked.

#### `":browse"`
If `hanzi` or `phonetic` are set to this value, open the Anki card browser to
point to *all* other notes which share this hanzi or phonetic component. If
`hanzi_term` or `phonetic_term` are set to this value, open the Anki card
browser to this specific note. Unfortunately, this functionality does not work
on AnkiMobile on iOS.

#### `":edit"`
If `hanzi_term` or `phonetic_term` are set to this value, open the term's note
for editing.

This may also be used for `hanzi` and `phonetic`, but doing so will only open a
single arbitrary note for editing, so this is not very useful.

Note that this only works on desktop and if
[AnkiConnect](https://ankiweb.net/shared/info/2055492159) is installed. If
AnkiConnect is not installed, or if using AnkiDroid, the note is opened in the
browser instead, much like `":browse"`. Additionally, this functionality does
not work on AnkiMobile on iOS.

#### Templated URL
You may also use an arbitrary templated URL with keyword replacements. For
example, consider the following URLs:

- `"https://example.com/search-hanzi?q={hanzi}"`
- `"https://example.com/search-term?q={kanji:term}&highlight={hanzi}"`
- `"https://example.com/search-hanzi?q={phonetic},{hanzi}"`

The complete list of available keywords is as follows:

- `hanzi`
- `phonetic`
- `term`

Note that you may only specify these keywords for options where this information
is accessible. For example, the `phonetic` keyword is unavailable in
`click_hanzi_action` and `click_hanzi_term_action`. Likewise, the `term` keyword
is unavailable in `click_hanzi_action` and `click_phonetic_action`.

Much like the [built-in Anki template
feature](https://docs.ankiweb.net/templates/fields.html?highlight=furigana#additional-ruby-character-filters),
you may filter these keywords by prefixing them with filters `kanji:` and
`kana:`. Unlike Anki templates, however, you may not chain filters.

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
This limits the list of terms to the next N notes with cards scheduled for
review. Set this to `0` to remove the limit.

Default: `5`.

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

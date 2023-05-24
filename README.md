# Hanzi Web for Anki
![Screenshot](screenshot.png)

This addon generates a “web” of hanzi/kanji amongst your Anki notes, adding a
few examples taken from cards you’ve already reviewed for each hanzi in each
note. The intent is that you’ll be able to more easily learn the readings of
hanzi if you are reminded of other words it comprises that you’ve already
studied.

## Installation
You may install this from its [Anki Web page](https://ankiweb.net/shared/info/125468335). You may alternatively download
it from the GitHub releases page, then install in Anki via `Tools -> Add-ons ->
Install from file…`

## Configuration
You can configure Hanzi Web through Anki after installing via `Tools -> Add-ons
-> Hanzi Web -> Config`. See [config.md](config.md).

You may want to also configure the CSS of your notes, as Hanzi Web does no
styling by default. It instead exposes three CSS classes:

- `ol.hanziewb`, applied to the `<ol>` which contains each entry.
- `span.hanziweb-hanzi`, which is the hanzi for which terms are listed (the left
  side of the screenshot shown above).
- `span.hanziweb-terms`, which contains the entire list of terms (the right side
  of the screenshot shown above).

The styling in the above screenshot was achieved with the following CSS. You may
copy it into your note type’s CSS if you wish.

``` css
ol.hanziweb {
  list-style-type: none;
  margin: 10px auto;
  font-size: 20px;
  max-width: 400px;
  border-style: solid;
  border-color: gray;
  border-width: 1px;
  padding: 5px 10px 5px 10px;
}

.hanziweb-hanzi {
  font-weight: bold;
  margin-right: 20px;
  font-size: 30px;
  font-family: serif;
}
```

### Chinese notes vs. Japanese notes

Notes can be configured to be recognized as either Chinese or Japanese by
adjusting the `japanese_search_query` option. There are subtle differences to
each.

### Chinese

- Characters are used as-is to look up phonetic series. In the future,
  simplified characters will be converted to traditional characters.
- Japanese on'yomi readings are omitted.

### Japanese

- When looking up the phonetic series, shinjitai characters will be converted to
  kyūjitai. This is done because the included database of phonetic series is
  based on traditional Chinese, which more closely matches kyūjitai variants.
  Regardless, there is not perfect coverage of Japanese.
- If both a `shinjitai_fields_regexp` field and a `kyujitai_fields_regexp` field
  are found on a note, there will be a *one way conversion* from shinjitai to
  kyūjitai on the matched notes. The results are not perfect. The intent is not
  necessary for users to study the kyūjitai forms (this is probably not
  generally helpful when learning Japanese), but rather to be able to have
  broader coverage when looking up Japanese words in Chinese dictionaries, for
  example, the [Outlier Dictionary of Chinese Characters](https://www.outlier-linguistics.com/products/outlier-dictionary-of-chinese-characters) in Pleco.


## Usage
Ensure that the note types of the notes you want to add web entries to have a
field called “HanziWeb” (without quotes). Also ensure that you’ve configured
Hanzi Web as described in the [Configuration](#configuration) section, so that
you are including the correct cards and using the hanzi from the correct fields.
Make sure that you add `{{HanziWeb}}` to your cards’ HTML templates as well.

Now you can add web entries to your notes by accessing `Tools -> Hanzi Web ->
Update notes…` or by pressing `Control-W` (`Command-W` on macOS). A dialog with
a report of the pending changes will be shown; you’ll want to consider this
carefully if it’s your first time running Hanzi Web or if you’ve recently
changed your configuration to make sure that you haven’t made any mistakes.
Click “Apply” and your notes’ “HanziWeb” fields will be filled!

var hanziweb = {
  ankidroid :
      typeof AnkiDroidJS !== 'undefined'
          ? new AnkiDroidJS({version : "0.0.3", developer : "Hanzi Web"})
          : null,
};

function hanziwebEditNote(id) {
  if (hanziweb.ankidroid !== null) {
    // Can't directly open note editor on AnkiDroid.
    hanziweb.ankidroid.ankiSearchCard("nid:" + id);
  } else if (typeof pycmd !== 'undefined') {
    pycmd("hanziwebEditNote " + id);
  }
}

function hanziwebBrowse(query) {
  if (hanziweb.ankidroid != null) {
    hanziweb.ankidroid.ankiSearchCard(query);
  } else if (typeof pycmd !== 'undefined') {
    pycmd("hanziwebBrowse " + query);
  }
}

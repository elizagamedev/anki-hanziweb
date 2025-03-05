window.hanziwebAnkiDroid =
    typeof AnkiDroidJS !== "undefined"
        ? new AnkiDroidJS({"version" : "0.0.3", "developer" : "Hanzi Web"})
        : null;

function hidePopup() {
  document.getElementById("hanziweb-popup")
      .classList.remove("hanziweb-popup-open");
}

function ankiEditNote(nid) {
  if (window.hanziwebAnkiDroid !== null) {
    // Can't directly open note editor on AnkiDroid.
    window.hanziwebAnkiDroid.ankiSearchCard("nid:" + nid);
  } else if (typeof pycmd !== "undefined") {
    pycmd("hanziwebEditNote " + nid);
  }
}

function ankiBrowse(query) {
  if (window.hanziwebAnkiDroid != null) {
    window.hanziwebAnkiDroid.ankiSearchCard(query);
  } else if (typeof pycmd !== "undefined") {
    pycmd("hanziwebBrowse " + query);
  }
}

function browseNotesQuery(nids) {
  return nids.map(nid => "nid:" + nid).join(" OR ");
}

function templateUrl(url, keywords) {
  for (const [key, value] of Object.entries(keywords)) {
    url = url.replace("{" + key + "}", encodeURIComponent(value));
  }
  return url;
}

function actionToHrefAndOnclick(action, nids, keywords) {
  switch (action) {
  case ":none":
    return [
      "#",
      (event) => {
        hidePopup();
        event.preventDefault();
      }
    ];
  case ":edit":
    return [
      "#",
      (event) => {
        ankiEditNote(nids[0]);
        hidePopup();
        event.preventDefault();
      },
    ];
  case ":browse":
    return [
      "#",
      (event) => {
        ankiBrowse(browseNotesQuery(nids));
        hidePopup();
        event.preventDefault();
      }
    ];
  default:
    if (action.startsWith(":")) {
      throw `hanziweb: unknown action: ${action}`;
    }
    return [ templateUrl(action, keywords), (event) => { hidePopup(); } ];
  }
}

function actionsToButtons(actions, nids, keywords) {
  return actions.map(([ text, action ]) => {
    const [href, onclick] = actionToHrefAndOnclick(action, nids, keywords);
    const button = document.createElement("a");
    button.innerText = text;
    button.setAttribute("role", "button");
    button.setAttribute("href", href);
    button.onclick = onclick;
    return button;
  });
}

function handleActions(title, actions, nids, keywords) {
  if (typeof actions === "string") {
    switch (actions) {
    case ":none":
      return;
    case ":edit":
      ankiEditNote(nids[0]);
      return;
    case ":browse":
      ankiBrowse(browseNotesQuery(nids));
      return;
    default:
      if (actions.startsWith(":")) {
        throw `hanziweb: unknown action: ${actions}`;
      }
      window.open(templateUrl(actions, keywords));
      return;
    }
  }
  if (actions === null || actions === undefined || actions.length === 0) {
    return;
  }
  // Show popup.
  document.getElementById("hanziweb-popup-title").replaceChildren(title);
  document.getElementById("hanziweb-popup-actions")
      .replaceChildren(...actionsToButtons(actions, nids, keywords));
  document.getElementById("hanziweb-popup")
      .classList.add("hanziweb-popup-open");
}

function getEventLink(event) {
  return event.target.closest("a[onclick^=hanziweb]");
}

function makeTermKeywords(element) {
  let kanji = "";
  let kana = "";

  function traverse(node, appendToKanji, appendToKana) {
    for (const child of node.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) {
        const text = child.wholeText;
        if (appendToKanji) {
          kanji += text;
        }
        if (appendToKana) {
          kana += text;
        }
      } else if (child.tagName !== "RP") {
        traverse(child, appendToKanji && child.tagName !== "RT",
                 appendToKana && child.tagName !== "RB");
      }
    }
  }
  traverse(element, true, true);

  return {"kanji:term" : kanji, "kana:term" : kana};
}

function sanitizeTermElement(element) {
  function traverse(node, out) {
    for (const child of node.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) {
        out.appendChild(new Text(child.wholeText));
      } else {
        if (child.tagName === "RUBY" || child.tagName === "RT" ||
            child.tagName === "RB" || child.tagName === "RP") {
          const outChild = document.createElement(child.tagName);
          traverse(child, outChild)
          out.appendChild(outChild);
        } else {
          traverse(child, out);
        }
      }
    }
  }
  const out = document.createElement("span");
  traverse(element, out);
  return out;
}

window.hanziwebOnClickHanzi = function(event, ...nids) {
  const hanzi = getEventLink(event).innerText;
  handleActions(new Text(hanzi), window.hanziwebHanziActions, nids,
                {"hanzi" : hanzi});
  event.preventDefault();
};

window.hanziwebOnClickHanziTerm = function(event, hanzi, ...nids) {
  const termElement = sanitizeTermElement(getEventLink(event));
  handleActions(termElement, window.hanziwebHanziTermActions, nids,
                {"hanzi" : hanzi, ...makeTermKeywords(termElement)});
  event.preventDefault();
};

window.hanziwebOnClickPhonetic = function(event, hanzi, ...nids) {
  const phonetic = getEventLink(event)
                       .querySelector(".hanziweb-phonetic-component")
                       .innerText;
  handleActions(new Text(phonetic), window.hanziwebPhoneticActions, nids,
                {"hanzi" : hanzi, "phonetic" : phonetic});
  event.preventDefault();
};

window.hanziwebOnClickPhoneticTerm = function(event, hanzi, phonetic, ...nids) {
  const termElement = sanitizeTermElement(getEventLink(event));
  handleActions(termElement, window.hanziwebPhoneticTermActions, nids, {
    "hanzi" : hanzi,
    "phonetic" : phonetic,
    ...makeTermKeywords(termElement)
  });
  event.preventDefault();
};

function init(css, html) {
  // Delete any stale elements that might have been left over from a previous
  // refresh of the Anki card preview.
  for (const element of document.querySelectorAll(
           "[id=hanziweb-style],[id=hanziweb-popup]")) {
    element.remove();
  }

  // Insert stylesheet.
  // document.getElementById("hanziweb-style")?.remove();
  const styleElement = document.createElement("style");
  styleElement.id = "hanziweb-style";
  styleElement.textContent = css;
  document.head.appendChild(styleElement);

  // Insert popup HTML.
  // document.getElementById("hanziweb-popup")?.remove();
  document.body.insertAdjacentHTML("afterbegin", html);
}

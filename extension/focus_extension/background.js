// background.js (manifest v3 service worker)
// Local classifier endpoint
const LOCAL_SERVER = "http://127.0.0.1:5000/check";

const DEFAULTS = {
  sendSnippet: false,   // user must opt-in to send full snippet
  snippetMaxChars: 1500
};

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set(DEFAULTS);
});

// helper: fetch with timeout
function fetchWithTimeout(url, opts = {}, timeout = 3000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Fetch timeout")), timeout);
    fetch(url, opts)
      .then(res => { clearTimeout(timer); resolve(res); })
      .catch(err => { clearTimeout(timer); reject(err); });
  });
}

// Accept messages from content script
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "analyze_page") {
    // get user settings then call server
    chrome.storage.local.get(["sendSnippet", "snippetMaxChars"], (settings) => {
      const payload = {
        domain: msg.domain || "",
        title: msg.title || "",
        snippet: (settings.sendSnippet && msg.snippet) ? msg.snippet.substring(0, settings.snippetMaxChars) : ""
      };

      fetchWithTimeout(LOCAL_SERVER, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }, 4000).then(r => r.json())
        .then(data => {
          // Normalize response shape
          const action = (data && data.action) || "allow";

          // Notify the tab and instruct content script to show overlay (if needed)
          if (sender?.tab?.id != null) {
            if (action === "block") {
              chrome.tabs.sendMessage(sender.tab.id, { type: "show_block", data }, () => {});
              chrome.notifications.create({
                type: "basic",
                iconUrl: "icon128.png",
                title: "Focus Mode — Blocking",
                message: `Blocked distracting site: ${payload.domain || sender.tab.url}`
              });
            } else if (action === "warn") {
              chrome.tabs.sendMessage(sender.tab.id, { type: "show_warn", data }, () => {});
              chrome.notifications.create({
                type: "basic",
                iconUrl: "icon128.png",
                title: "Focus Mode — Warning",
                message: data.message || "This page may be distracting."
              });
            } else {
              // allow -> inform content script to optionally remove overlays
              chrome.tabs.sendMessage(sender.tab.id, { type: "allow", data }, () => {});
            }
          }
          sendResponse({ ok: true, data });
        })
        .catch(err => {
          console.warn("Local classifier unreachable:", err);
          // Tell content script classifier unavailable so it can avoid blanking
          if (sender?.tab?.id != null) {
            chrome.tabs.sendMessage(sender.tab.id, { type: "classifier_unavailable" }, () => {});
          }
          sendResponse({ ok: false, error: String(err) });
        });
    });

    // indicate we'll call sendResponse asynchronously
    return true;
  }

  // allow other message types
});

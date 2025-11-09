// background.js
// Service worker (Manifest V3)
const LOCAL_SERVER = "http://127.0.0.1:5000/check"; // local classifier endpoint

// Default settings
const DEFAULTS = {
  sendSnippet: false,   // require explicit consent to send snippet
  snippetMaxChars: 300  // max characters to send when enabled
};

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set(DEFAULTS);
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "analyze_page") {
    chrome.storage.local.get(["sendSnippet", "snippetMaxChars"], (settings) => {
      const payload = {
        domain: msg.domain || "",
        title: msg.title || "",
        // include snippet only if user enabled it
        snippet: settings.sendSnippet && msg.snippet ? msg.snippet.substring(0, settings.snippetMaxChars) : ""
      };
      // POST to local server (fire-and-forget with a timeout)
      fetchWithTimeout(LOCAL_SERVER, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }, 3000).then(res => res.json())
        .then(data => {
          // Expected response shape: { action: "allow"|"warn"|"block", tag: "...", reason: "..." }
          sendResponse({ ok: true, data });
        })
        .catch(err => {
          console.warn("Local classifier unreachable:", err);
          sendResponse({ ok: false, error: String(err) });
        });
    });
    // Return true to indicate we will sendResponse asynchronously
    return true;
  }
});

// small helper: fetch with timeout
function fetchWithTimeout(url, opts = {}, timeout = 3000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Fetch timeout")), timeout);
    fetch(url, opts)
      .then(res => {
        clearTimeout(timer);
        resolve(res);
      })
      .catch(err => {
        clearTimeout(timer);
        reject(err);
      });
  });
}

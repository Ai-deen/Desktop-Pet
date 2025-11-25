// content_script.js
(function () {
  if (window.__FOCUS_SIGNAL_INJECTED) return;
  window.__FOCUS_SIGNAL_INJECTED = true;

  // small utils
  function hashString(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) {
      h = (h << 5) - h + str.charCodeAt(i);
      h |= 0;
    }
    return String(h);
  }

  // Basic stopword removal to shorten snippet
  const STOPWORDS = new Set([
    "the","a","an","and","or","is","are","was","were","to","of","in",
    "that","this","it","for","on","with","as","by","be","at","from",
    "your","you","i","we","they","their","our","but","if","not",
    "can","will","just","up","out","about","into","so","no","yes"
  ]);

  function cleanSnippet(text) {
    if (!text) return "";
    return text
      .replace(/\s+/g, " ")
      .split(" ")
      .filter(w => w && !STOPWORDS.has(w.toLowerCase()))
      .join(" ")
      .slice(0, 1500);
  }

  // Throttle and dedupe
  let lastHash = null;
  let lastSend = 0;
  const MIN_SEND_INTERVAL = 1200;

  function safeSendMessage(payload) {
    const now = Date.now();
    if (now - lastSend < MIN_SEND_INTERVAL) return;
    lastSend = now;

    try {
      chrome.runtime.sendMessage(payload, (resp) => {
        if (chrome.runtime.lastError) {
          console.warn("sendMessage error:", chrome.runtime.lastError.message);
        } else {
          console.log("FocusSignal: server response", resp);
        }
      });
    } catch (err) {
      console.error("safeSendMessage exception:", err);
    }
  }

  // Extract and send snippet only when changed
  function dumpText(tries = 6, delay = 1200) {
    let attempt = 0;
    function grab() {
      let text = "";
      try { text = document.body?.innerText || ""; } catch (e) { }
      const cleaned = cleanSnippet(text);
      const h = hashString(cleaned);

      if (cleaned.length > 40 && h !== lastHash) {
        lastHash = h;
        safeSendMessage({
          type: "analyze_page",
          domain: location.hostname,
          title: document.title || "",
          snippet: cleaned
        });
      } else if (attempt < tries) {
        attempt++;
        setTimeout(grab, delay);
      }
    }
    grab();
  }

  // SPA detection (URL change)
  let lastUrl = location.href;
  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      dumpText();
    }
  }, 900);

  // First load
  if (document.readyState === "complete") {
    setTimeout(dumpText, 800);
  } else {
    window.addEventListener("load", () => setTimeout(dumpText, 800));
  }

  // Overlay creation / helper functions
  function createOverlay(type, data) {
    // avoid duplicate overlay
    if (document.getElementById("focus-signal-overlay")) return;

    const overlay = document.createElement("div");
    overlay.id = "focus-signal-overlay";
    overlay.style.cssText = `
      position:fixed; inset:0;
      display:flex; align-items:center; justify-content:center;
      background: rgba(12,12,12,0.96);
      color:#fff; z-index:2147483647; padding:20px; text-align:center;
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    `;

    const box = document.createElement("div");
    box.style.cssText = "max-width:900px; width:100%;";

    if (type === "block") {
      box.innerHTML = `
        <div style="font-size:28px; font-weight:600; margin-bottom:8px">🚫 Blocked by FocusAI</div>
        <div style="font-size:16px; margin-bottom:14px">${(data && data.message) ? data.message : "This page was classified as a distraction."}</div>
        <div style="display:flex; gap:8px; justify-content:center;">
          <button id="fs-continue" style="padding:10px 16px; font-size:14px;">Continue anyway</button>
          <button id="fs-white" style="padding:10px 16px; font-size:14px;">Whitelist this domain</button>
        </div>
        <div style="margin-top:12px; font-size:12px; opacity:0.8;">Tip: The pet will encourage you when on allowed sites.</div>
      `;
    } else if (type === "warn") {
      box.innerHTML = `
        <div style="font-size:22px; font-weight:600; margin-bottom:8px">⚠️ Be mindful</div>
        <div style="font-size:15px; margin-bottom:10px">${(data && data.message) ? data.message : "This page may be distracting."}</div>
        <div style="display:flex; gap:8px; justify-content:center;">
          <button id="fs-dismiss" style="padding:8px 12px; font-size:13px;">Dismiss</button>
        </div>
      `;
    } else {
      // allow - nothing to show
      return;
    }

    overlay.appendChild(box);
    document.documentElement.appendChild(overlay);

    // handlers
    document.getElementById("fs-continue")?.addEventListener("click", () => {
      removeOverlay();
    });
    document.getElementById("fs-white")?.addEventListener("click", () => {
      // simple local whitelist by domain (persistent)
      chrome.storage.local.get(["whitelist"], (s) => {
        const wl = new Set(s.whitelist || []);
        wl.add(location.hostname);
        chrome.storage.local.set({ whitelist: Array.from(wl) }, () => {
          removeOverlay();
        });
      });
    });
    document.getElementById("fs-dismiss")?.addEventListener("click", () => {
      removeOverlay();
    });
  }

  function removeOverlay() {
    const el = document.getElementById("focus-signal-overlay");
    if (el) el.remove();
  }

  // receive signals from background
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || !msg.type) return;
    if (msg.type === "show_block") {
      // check whitelist first
      chrome.storage.local.get(["whitelist"], (s) => {
        const wl = new Set(s.whitelist || []);
        if (wl.has(location.hostname)) {
          // don't show overlay
          sendResponse({ ok: "whitelisted" });
        } else {
          createOverlay("block", msg.data);
          sendResponse({ ok: true });
        }
      });
      return true;
    } else if (msg.type === "show_warn") {
      createOverlay("warn", msg.data);
    } else if (msg.type === "allow") {
      removeOverlay();
    } else if (msg.type === "classifier_unavailable") {
      // optional: small console marker
      console.warn("FocusSignal: classifier unavailable");
    }
  });
})();

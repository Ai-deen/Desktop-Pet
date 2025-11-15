(function () {
  if (window.__FOCUS_SIGNAL_INJECTED) return;
  window.__FOCUS_SIGNAL_INJECTED = true;

  console.log("[FocusSignal] content script loaded.");

  const domain = location.hostname;

  // ============================
  //  THROTTLE MESSAGE SENDING
  // ============================
  function safeSendMessage(payload) {
    const now = Date.now();

    // throttle: allow only 1 message per 1500ms
    if (window.__lastSend && now - window.__lastSend < 1500) {
      console.log("[FocusSignal] throttled message");
      return;
    }

    window.__lastSend = now;

    if (!chrome?.runtime?.id) {
      console.warn("[FocusSignal] Extension context lost.");
      return;
    }

    try {
      chrome.runtime.sendMessage(payload, (resp) => {
        if (chrome.runtime.lastError) {
          console.warn("[FocusSignal] sendMessage error:", chrome.runtime.lastError.message);
          return;
        }
        console.log("[FocusSignal] Message OK:", resp);
      });
    } catch (err) {
      console.error("[FocusSignal] safeSendMessage exception:", err);
    }
  }

  // ============================
  //  CLEAN SNIPPET (stopwords removed)
  // ============================
  function cleanSnippet(text) {
    if (!text) return "";

    const stopwords = new Set([
      "the","a","an","and","or","is","are","was","were","to","of","in",
      "that","this","it","for","on","with","as","by","be","at","from",
      "your","you","i","we","they","their","our","but","if","not",
      "can","will","just","up","out","about","into","so","no","yes"
    ]);

    return text
      .replace(/\s+/g, " ")              // normalize whitespace
      .split(" ")
      .filter(w => w && !stopwords.has(w.toLowerCase()))
      .join(" ")
      .slice(0, 1500);
  }

  // ============================
  //  MAIN TEXT EXTRACTION LOOP
  // ============================
  function dumpText(tries = 8, delay = 1500) {
    let attempt = 0;

    function grab() {
      let text = "";

      try {
        text = document.body?.innerText || "";
      } catch (e) {
        console.error("Text extract error", e);
      }

      const cleaned = cleanSnippet(text);

      console.log(`[FocusSignal] attempt ${attempt + 1}, cleaned snippet length = ${cleaned.length}`);

      // Only send if snippet has enough content
      if (cleaned.length > 40) {
        safeSendMessage({
          type: "analyze_page",
          domain,
          title: document.title || "",
          snippet: cleaned
        });
      } else if (attempt < tries) {
        attempt++;
        setTimeout(grab, delay);
      } else {
        console.log("[FocusSignal] snippet too small, giving up.");
      }
    }

    grab();
  }

  // ============================
  //  URL CHANGE DETECTOR (SPA FIX)
  // ============================
  let lastUrl = location.href;

  setInterval(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      console.log("[FocusSignal] URL changed:", lastUrl);
      dumpText();
    }
  }, 1000);

  // ============================
  //  FIRST LOAD TRIGGER
  // ============================
  if (document.readyState === "complete") {
    setTimeout(() => dumpText(), 1200);
  } else {
    window.addEventListener("load", () => setTimeout(() => dumpText(), 1200));
  }
})();

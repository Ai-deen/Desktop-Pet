// content_script.js
(function () {
  if (window.__FOCUS_SIGNAL_INJECTED) return;
  window.__FOCUS_SIGNAL_INJECTED = true;

  console.log("[FocusSignal] content script loaded.");

  const domain = location.hostname;
  const title = document.title;
  let sentOnce = false; // prevent multiple sends

  // --- Safe message sender ---
  function safeSendMessage(payload) {
    if (sentOnce) return;
    if (!chrome?.runtime?.id) {
      console.warn("[FocusSignal] Extension context lost; skipping sendMessage.");
      return;
    }
    try {
      chrome.runtime.sendMessage(payload, (resp) => {
        if (chrome.runtime.lastError) {
          console.warn("[FocusSignal] sendMessage error:", chrome.runtime.lastError.message);
          return;
        }
        console.log("[FocusSignal] Message sent ok; response:", resp);
      });
      sentOnce = true;
    } catch (err) {
      console.error("[FocusSignal] safeSendMessage exception:", err);
    }
  }

  // --- Main text dump logic ---
  function dumpText(tries = 8, delay = 2000) {
    let attempt = 0;

    function grab() {
      let text = "";
      try {
        text = document.body?.innerText || "";
      } catch (e) {
        console.error("Text extract error", e);
      }

      const len = text.length;
      console.log(`[FocusSignal] attempt ${attempt + 1}: body text length ${len}`);

      // clean + slice text
      let snippet = text.replace(/\s+/g, " ").trim().slice(0, 50000);

      if (len > 300) {
        console.log("[FocusSignal] preparing to send snippet of", snippet.length, "chars");

        // slight delay so backend is ready
        setTimeout(() => {
          safeSendMessage({
            type: "analyze_page",
            domain,
            title,
            snippet
          });
        }, 1000);
      } else if (attempt < tries) {
        attempt++;
        console.log("[FocusSignal] snippet too short, retrying...");
        setTimeout(grab, delay);
      } else {
        console.log("[FocusSignal] gave up after", tries, "tries (still empty).");
      }
    }

    grab();
  }

  // --- Run after full load ---
  if (document.readyState === "complete") {
    setTimeout(() => dumpText(), 15000);
  } else {
    window.addEventListener("load", () => setTimeout(() => dumpText(), 15000));
  }
})();

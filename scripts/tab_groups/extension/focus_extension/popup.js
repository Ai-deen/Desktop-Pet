// popup.js
document.addEventListener("DOMContentLoaded", () => {
  const checkbox = document.getElementById("sendSnippet");
  const openBtn = document.getElementById("openSettings");

  chrome.storage.local.get(["sendSnippet"], (s) => {
    checkbox.checked = !!s.sendSnippet;
  });

  checkbox.addEventListener("change", () => {
    chrome.storage.local.set({ sendSnippet: checkbox.checked });
  });

  openBtn.addEventListener("click", () => {
    // optional: open local docs or show brief info
    alert("Make sure your local classifier server is running at http://127.0.0.1:5000/check\nPayload: {domain, title, snippet}\nResponse: {action:'allow'|'warn'|'block', tag:'', reason:''}");
  });
});

(async function () {
  await new Promise(r => document.readyState === "complete" ? r() : window.addEventListener("load", r));
  const html = document.documentElement.outerHTML.slice(0, 50000);
  const title = document.title || "";
  const url = window.location.href;
  const text = document.body.innerText.slice(0, 2000);
  try {
    const res = await fetch("http://localhost:5000/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ url, title, text, html })
    });
    const data = await res.json();
    console.log("Focus AI verdict:", data);
    if (!data.allow) {
      document.body.innerHTML = `
        <div style="font-family:sans-serif;text-align:center;margin-top:25vh;
                    background:#111;color:#fff;height:100vh;font-size:20px;">
          🚫 <b>Blocked by Focus AI</b><br>
          <small>This page is not study-related.</small>
        </div>`;
    }
  } catch (err) {
    console.error("Focus AI filter unavailable:", err);
  }
})();
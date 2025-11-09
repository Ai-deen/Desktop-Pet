# focus_server.py
# simple local test server for Focus Extension
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)
    print("\n[DEBUG] Received:", data) 
    domain = (data.get("domain") or "").lower()
    title = (data.get("title") or "").lower()

    # quick rule-based filter
    if any(x in domain for x in ["youtube", "instagram", "netflix", "spotify", "reddit"]):
        action = "block"
        reason = f"Domain '{domain}' is in blocked list."
    elif any(x in title for x in ["music", "beats", "movie", "meme"]):
        action = "warn"
        reason = f"Title contains '{title}'."
    else:
        action = "allow"
        reason = "Looks like a work-related page."

    result = {
        "action": action,
        "tag": "entertainment" if action != "allow" else "work",
        "reason": reason
    }
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)

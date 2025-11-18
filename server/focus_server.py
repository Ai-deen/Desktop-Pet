# focus_server.py
from flask import Flask, request, jsonify
import os, json, requests, re
from nltk.corpus import stopwords
import nltk
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)

# ---- NLTK SETUP ----
nltk.download('stopwords', quiet=True)
try:
    STOPWORDS = set(stopwords.words('english'))
except LookupError:
    nltk.download('stopwords')
    STOPWORDS = set(stopwords.words('english'))

def remove_stopwords(text):
    return " ".join([w for w in text.split() if w.lower() not in STOPWORDS])

def clean_snippet(snippet):
    if not snippet:
        return ""

    # strip special tokens
    snippet = snippet.replace("<s>", "").replace("</s>", "")

    # remove non-ascii/bad chars
    snippet = re.sub(r'[^ -~]', ' ', snippet)

    # collapse spaces
    snippet = " ".join(snippet.split())

    # apply stopwords
    snippet = remove_stopwords(snippet)

    return snippet[:1500]


# ---------------- CONFIG ----------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemma-2-9b-it"   # better JSON reliability
# -----------------------------------------


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)
    print("\n[DEBUG] Received:", data)

    domain = (data.get("domain") or "").lower()
    title = (data.get("title") or "").lower()
    raw_snippet = data.get("snippet") or ""

    snippet = clean_snippet(raw_snippet)
    print("[CLEANED SNIPPET]:", snippet[:1500], "...")

    # Quick blocklist
    if any(x in domain for x in ["netflix", "instagram", "reddit", "hotstar", "spotify"]):
        return jsonify({
            "action": "block",
            "pet_behavior": "alert",
            "message": f"Blocked distracting site: {domain}"
        })

    prompt = f"""
    You are FocusAI, an agent controlling a productivity pet. Your job is to PROTECT the user's focus by being extremely strict.

    Context:
    Domain: {domain}
    Title: {title}
    Snippet: {snippet}

    TASK:
    Decide if the page is TECHNICAL (directly relevant to software engineering, coding, or career development) or NON-TECHNICAL (anything else). The user has low self-control — prioritize blocking ambiguous content.

    VERY STRICT RULES (apply exactly):
    1) ALLOW ONLY (set action = "allow"):
    - Coding problems, algorithms, data-structures (LeetCode, Codeforces, etc.)
    - Programming tutorials (YouTube/videos/blogs) explicitly about coding
    - Official technical documentation (language docs, API docs, MDN, RFCs, AWS/GCP docs)
    - System design, backend engineering, reliability, distributed systems
    - Developer tools, GitHub repos, StackOverflow, coding tests, interview pages
    - Job application pages, LinkedIn job listings, recruiter messages
    - Tech news (explicitly about AI, programming, software engineering)

    2) BLOCK EVERYTHING ELSE (set action = "block"):
    - Music, artists, albums, K-pop, entertainment, movies, TV shows, drama
    - Cute animals, nature photos, image galleries, non-technical videos
    - General Wikipedia pages not explicitly about computer science
    - Social media platforms and feeds (Instagram, Reddit, TikTok, X/Twitter, Facebook)
    - Shopping, product pages, sports, travel, lifestyle, gossip, memes
    - Most blogs and news unless explicitly technical
    - Music streaming sites (Spotify), video streaming (Netflix), video short feeds

    3) WARN (set action = "warn") when:
    - The page is clearly educational but NOT about software/engineering (e.g., biology, history, math theory not tied to CS).
    - The page might be tangentially useful but not directly for coding or career growth.

    4) DEFAULT behavior:
    - If unsure or ambiguous, DEFAULT TO BLOCK.
    - Assume the user will get distracted — be conservative.

    OUTPUT FORMAT (MANDATORY):
    Return ONLY a single RAW JSON object and nothing else (no markdown, no code fences, no extra text). The JSON must be valid.

    Example JSON schema:
    {{
    "action": "allow" | "warn" | "block",
    "pet_behavior": "encourage" | "alert" | "relax",
    "message": "short motivational sentence (one line)"
    }}

    BEHAVIOR MAPPING:
    - If action == "allow": use pet_behavior="encourage" and message should encourage progress.
    - If action == "warn": use pet_behavior="alert" and message should be a short caution about relevance.
    - If action == "block": use pet_behavior="alert" and message should clearly tell the user focus is required.

    FINAL RULES:
    - NEVER output <s> or </s>, never wrap JSON in backticks, never include extra commentary.
    - ALWAYS produce a JSON object even if you must guess (if uncertain, return block with a short reason).

    Now make the decision and output the JSON object only.
    """


    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000"
            },
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3
            },
            timeout=20
        )

        data = resp.json()
        ai_text = data["choices"][0]["message"]["content"].strip()
        print("[AI Response]:", ai_text)

        # Clean AI output
        ai_text = ai_text.replace("<s>", "").replace("</s>", "").strip()

        try:
            result = json.loads(ai_text)
        except Exception:
            result = {
                "action": "warn",
                "pet_behavior": "alert",
                "message": "AI output malformed—defaulting to warn."
            }

        return jsonify(result)

    except Exception as e:
        print("[ERROR] OpenRouter failed:", e)
        return jsonify({
            "action": "allow",
            "pet_behavior": "relax",
            "message": "AI unavailable. Defaulting to allow."
        })


if __name__ == "__main__":
    print("🚀 Focus Server running on http://127.0.0.1:5000/check")
    app.run(host="127.0.0.1", port=5000)

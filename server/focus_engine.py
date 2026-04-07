# focus_server.py
import os
import json
import requests
import re
import nltk
from nltk.corpus import stopwords
from dotenv import load_dotenv
import logging
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
from app.utils.log_file import log_file



# -------------------- ENV --------------------
load_dotenv()



# -------------------- LOGGING --------------------
LOG_PATH = log_file("focus_server.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [FOCUS_SERVER] %(levelname)s: %(message)s"
)

logging.info("Focus server module imported.")

# -------------------- NLTK STOPWORDS --------------------
def load_stopwords():
    try:
        nltk.download("stopwords", quiet=True)
        return set(stopwords.words("english"))
    except:
        try:
            nltk.download("stopwords")
            return set(stopwords.words("english"))
        except Exception as e:
            logging.error(f"Failed to load stopwords: {e}")
            return set()

STOPWORDS = load_stopwords()


def remove_stopwords(text):
    return " ".join(w for w in text.split() if w.lower() not in STOPWORDS)


def clean_snippet(snippet):
    if not snippet:
        return ""

    snippet = snippet.replace("<s>", "").replace("</s>", "")
    snippet = re.sub(r"[^ -~]", " ", snippet)
    snippet = " ".join(snippet.split())
    snippet = remove_stopwords(snippet)

    return snippet[:1500]


# -------------------- CONFIG --------------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = "google/gemma-2-9b-it"
# -------------------------------------------------


def check_focus(domain: str, title: str, snippet: str) -> dict:
    domain = (domain or "").lower()
    title = (title or "").lower()
    snippet = clean_snippet(snippet or "")

    # Quick blocklist
    if any(x in domain for x in ["netflix", "instagram", "reddit", "hotstar", "spotify"]):
        result = {
            "action": "block",
            "pet_behavior": "alert",
            "message": f"Blocked distracting site: {domain}"
        }
        logging.info(f"Quick blocklist triggered: {result}")
        return result

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

        ai_raw = resp.json()
        ai_output = ai_raw["choices"][0]["message"]["content"].strip()

        logging.info(f"AI Raw: {ai_output}")

        ai_output = ai_output.replace("<s>", "").replace("</s>", "").strip()

        # ---- JSON extraction fix ----
        def extract_json(text):
            text = text.strip().replace("```json", "").replace("```", "")
            start = text.find("{")
            end = text.rfind("}")

            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1]
                try:
                    return json.loads(candidate)
                except Exception as e:
                    logging.error(f"JSON candidate failed: {e}")

            return None

        result = extract_json(ai_output)

        if result is None:
            logging.error(f"Malformed AI JSON. Raw output: {ai_output}")
            result = {
                "action": "warn",
                "pet_behavior": "alert",
                "message": "AI output malformed—defaulting to warn."
            }

        return result

    except Exception as e:
        logging.error(f"OpenRouter error: {e}")
        return {
            "action": "allow",
            "pet_behavior": "relax",
            "message": "AI unavailable. Defaulting to allow."
        }





import os
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

# Load .env keys
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (NEWS_API_KEY and OPENAI_API_KEY):
    st.error("Missing API keys. Please set NEWS_API_KEY and OPENAI_API_KEY in a .env file.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)
NEWS_ENDPOINT = "https://newsapi.org/v2/top-headlines"
WORD_LIMIT = 60

# ---------- Helpers ----------
def plain(html_str):
    return BeautifulSoup(html_str or "", "html.parser").get_text(" ", strip=True)

def summarise_english(text):
    prompt = (
        f"Summarise the following news article in ≤ {WORD_LIMIT} words. "
        "Keep it strictly factual; do not add opinions or extra details.\n\n"
        f"{text}"
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120,
        temperature=0.2,
    )
    summary = resp.choices[0].message.content.strip()
    words = summary.split()
    return " ".join(words[:WORD_LIMIT]) + ("…" if len(words) > WORD_LIMIT else "")

@st.cache_data(ttl=900, show_spinner="🔄 Fetching news & writing summaries…")
def fetch_and_summarise(country="us", category="general", n=20):
    params = {"country": country, "category": category, "pageSize": n, "apiKey": NEWS_API_KEY}
    res = requests.get(NEWS_ENDPOINT, params=params, timeout=10)
    res.raise_for_status()
    output = []
    for art in res.json()["articles"]:
        body = plain(art.get("content") or art.get("description") or "")
        summary = summarise_english(body)
        output.append((art, summary))
    return output

# ---------- Streamlit UI ----------
st.set_page_config(page_title="News-in-60", layout="centered")
st.title("📰 News-in-60")
st.caption("Bite-sized news summaries using GPT-4o-mini")

# Sidebar filters
st.sidebar.title("Filters")
country = st.sidebar.selectbox("🌍 Country", ["us", "gb", "in", "au"], index=0)
category = st.sidebar.selectbox("🗂️ Category", ["general", "business", "technology", "sports", "science"], index=0)
if st.sidebar.button("🔄 Refresh News"):
    st.cache_data.clear()

# CSS Styles
st.markdown("""
    <style>
        .news-card {
            max-width: 700px;
            margin: 20px auto;
            border-radius: 20px;
            overflow: hidden;
            background-color: #fff;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
            display: flex;
            flex-direction: column;
        }
        .news-image {
            width: 100%;
            height: 240px;
            object-fit: cover;
        }
        .news-content {
            padding: 20px;
        }
        .news-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #111;
        }
        .news-meta {
            font-size: 13px;
            color: #888;
            margin-bottom: 12px;
        }
        .news-summary {
            font-size: 15px;
            line-height: 1.6;
            color: #333;
        }
        .news-button {
            display: inline-block;
            margin-top: 16px;
            padding: 10px 18px;
            background-color: #007bff;
            color: #fff;
            text-decoration: none;
            border-radius: 30px;
            font-weight: 500;
            font-size: 14px;
        }
    </style>
""", unsafe_allow_html=True)

# Render news cards
articles = fetch_and_summarise(country, category)

for art, summary in articles:
    # ✅ Skip if any required info is missing or bad
    if (
        not art.get("title") or
        not art.get("url") or
        not summary or
        "Please provide the news" in summary
    ):
        continue

    image_html = f"<img src='{art['urlToImage']}' class='news-image' />" if art.get("urlToImage") else ""

    card_html = f"""
    <div class="news-card">
        {image_html}
        <div class="news-content">
            <div class="news-title">{art['title']}</div>
            <div class="news-meta">{art['source']['name']} • {art['publishedAt'][:10]}</div>
            <div class="news-summary">{summary}</div>
            <a href="{art['url']}" target="_blank" class="news-button">Read Full Article ↗</a>
        </div>
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)

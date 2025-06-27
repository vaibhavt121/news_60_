import os
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from streamlit_elements import elements, mui, html, sync

# Load keys
load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
NEWS_ENDPOINT = "https://newsapi.org/v2/top-headlines"
WORD_LIMIT = 60

# -------- Helper Functions --------
def plain(html_str):
    return BeautifulSoup(html_str or "", "html.parser").get_text(" ", strip=True)

def summarise_english(text):
    prompt = (
        f"Summarise the following news article in ≤ {WORD_LIMIT} words. "
        "Keep it strictly factual.\n\n"
        f"{text}"
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120,
        temperature=0.2,
    )
    summary = response.choices[0].message.content.strip()
    words = summary.split()
    return " ".join(words[:WORD_LIMIT]) + ("…" if len(words) > WORD_LIMIT else "")

@st.cache_data(ttl=900)
def fetch_articles(country="us", category="general", n=15):
    params = {"country": country, "category": category, "pageSize": n, "apiKey": NEWS_API_KEY}
    res = requests.get(NEWS_ENDPOINT, params=params)
    res.raise_for_status()
    articles = res.json()["articles"]
    output = []
    for art in articles:
        if not art.get("title") or not art.get("url"):
            continue
        text = plain(art.get("content") or art.get("description") or "")
        summary = summarise_english(text)
        output.append({
            "title": art["title"],
            "source": art["source"]["name"],
            "date": art["publishedAt"][:10],
            "image": art.get("urlToImage"),
            "url": art["url"],
            "summary": summary
        })
    return output

# -------- UI State --------
st.set_page_config(page_title="Swipe News", layout="centered")
st.title("🗞️ News.Shot")
st.sidebar.title("Filters")
country = st.sidebar.selectbox("Country", ["us", "gb", "in", "au"], index=0)
category = st.sidebar.selectbox("Category", ["general", "business", "technology", "sports", "science"], index=0)

# Get articles and track index
articles = fetch_articles(country, category)
if "index" not in st.session_state:
    st.session_state.index = 0

# Swipe navigation
if st.button("⬅️ Previous"):
    st.session_state.index = max(0, st.session_state.index - 1)
if st.button("➡️ Next"):
    st.session_state.index = min(len(articles) - 1, st.session_state.index + 1)

# Display current article
if articles:
    art = articles[st.session_state.index]
    with elements("news-card"):
        with mui.Card(sx={"maxWidth": 700, "margin": "auto", "boxShadow": 3}):
            if art["image"]:
                mui.CardMedia(component="img", height=240, image=art["image"], alt="news")
            with mui.CardContent():
                mui.Typography(art["title"], variant="h6", sx={"fontWeight": 600})
                mui.Typography(f"{art['source']} • {art['date']}", variant="body2", color="text.secondary", gutterBottom=True)
                mui.Typography(art["summary"], variant="body1", sx={"marginTop": 2})
            with mui.CardActions():
                mui.Button("Read Full Article ↗", href=art["url"], target="_blank")
else:
    st.info("No articles available.")

# app.py  –  run with:  streamlit run app.py
import os, textwrap, requests, streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI          # ⬅ new-style import

# ───── Load keys from .env ─────
load_dotenv()
NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not (NEWS_API_KEY and OPENAI_API_KEY):
    st.error("Add NEWS_API_KEY and OPENAI_API_KEY to a .env file then restart.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)      # ⬅ new client object
NEWS_ENDPOINT = "https://newsapi.org/v2/top-headlines"
WORD_LIMIT    = 60

# ---------- helpers ----------
def plain(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)

def summarise_english(text: str) -> str:
    """
    Return a factual ≤60-word English summary using GPT-4o-mini
    (works with openai-python ≥1.0).
    """
    prompt = (
        f"Summarise the following news article in ≤ {WORD_LIMIT} words. "
        "Keep it strictly factual; do not add opinions or extra details.\n\n"
        f"{text}"
    )
    resp = client.chat.completions.create(         # ⬅ new call
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120,
        temperature=0.2,
    )
    summary = resp.choices[0].message.content.strip()
    words   = summary.split()
    return " ".join(words[:WORD_LIMIT]) + ("…" if len(words) > WORD_LIMIT else "")

@st.cache_data(ttl=900, show_spinner="Fetching news & writing summaries…")
def fetch_and_summarise(country="us", category="general", n=20):
    params = {"country": country, "category": category, "pageSize": n, "apiKey": NEWS_API_KEY}
    res = requests.get(NEWS_ENDPOINT, params=params, timeout=10)
    res.raise_for_status()
    output = []
    for art in res.json()["articles"]:
        body    = plain(art.get("content") or art.get("description") or "")
        summary = summarise_english(body)
        output.append((art, summary))
    return output

# ---------- Streamlit UI ----------
st.set_page_config(page_title="News-in-60 (English)", layout="wide")
st.sidebar.title("Filters")
country  = st.sidebar.selectbox("Country", ["us", "gb", "in", "au"], index=0)
category = st.sidebar.selectbox("Category",
                                ["general", "business", "technology", "sports", "science"],
                                index=0)
if st.sidebar.button("🔄 Refresh"):
    st.cache_data.clear()

for art, summary in fetch_and_summarise(country, category):
    st.markdown("---")
    st.subheader(art["title"])
    st.caption(f'{art["source"]["name"]} • {art["publishedAt"][:10]}')
    if art.get("urlToImage"):
        st.image(art["urlToImage"], use_column_width=True)
    st.write(textwrap.fill(summary, 85))
    st.link_button("Read full article ↗", art["url"], use_container_width=True)

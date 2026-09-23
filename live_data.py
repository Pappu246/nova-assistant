"""
NOVA Live Data Layer - real-time information fetching.

Sources:
  1. Google News RSS    -> news headlines (no API key)
  2. CoinGecko API      -> crypto prices (free)
  3. Yahoo Finance      -> stock prices (free)
  4. Wikipedia API      -> person/place info
  5. DuckDuckGo Search  -> general web search
  6. Smart dispatcher   -> picks right source for query
"""
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime

try:
    import feedparser
    _FEED = True
except Exception:
    _FEED = False

# ddgs is the new name (duckduckgo_search is deprecated)
_DDG = False
try:
    from ddgs import DDGS
    _DDG = True
    print("[live_data] Using ddgs (new)")
except Exception:
    try:
        from duckduckgo_search import DDGS
        _DDG = True
    except Exception:
        _DDG = False

try:
    import yfinance as yf
    _YF = True
except Exception:
    _YF = False


# ============ 1. NEWS (Google News RSS) ============

def get_news(topic="top", country="IN", limit=5):
    """
    Get news headlines from Google News RSS.
    topic: 'top', or any keyword like 'cricket', 'technology'
    """
    if not _FEED:
        return "News reader not available."

    try:
        if topic == "top":
            url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        else:
            q = urllib.parse.quote(topic)
            url = "https://news.google.com/rss/search?q=" + q + "&hl=en-IN&gl=IN&ceid=IN:en"

        feed = feedparser.parse(url)
        if not feed.entries:
            return "Aaj koi news nahi mili."

        lines = ["Aaj ki " + topic + " news:"]
        for i, entry in enumerate(feed.entries[:limit], 1):
            title = entry.get("title", "").strip()
            # Clean title (remove source suffix)
            title = re.sub(r"\s+-\s+[^-]+$", "", title)
            if title:
                lines.append(str(i) + ". " + title[:120])
        return "\n".join(lines)
    except Exception as e:
        return "News fetch fail: " + str(e)[:80]


# ============ 2. CRYPTO (CoinGecko) ============

_CRYPTO_IDS = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "solana": "solana", "sol": "solana",
    "cardano": "cardano", "ada": "cardano",
    "ripple": "ripple", "xrp": "ripple",
    "bnb": "binancecoin",
    "shiba": "shiba-inu",
    "polygon": "matic-network",
}


def get_crypto(coin="bitcoin"):
    """Get live crypto price from CoinGecko (free, no key)."""
    coin_lower = coin.lower().strip()
    coin_id = _CRYPTO_IDS.get(coin_lower, coin_lower)

    try:
        url = ("https://api.coingecko.com/api/v3/simple/price"
               "?ids=" + coin_id + "&vs_currencies=usd,inr"
               "&include_24hr_change=true")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        if coin_id not in data:
            return "Crypto nahi mila: " + coin

        info = data[coin_id]
        usd = info.get("usd", 0)
        inr = info.get("inr", 0)
        change = info.get("usd_24h_change", 0)
        arrow = "up" if change > 0 else "down"

        return (coin.upper() + " live price: $" + str(round(usd, 2)) +
                " (Rs " + str(int(inr)) + "). 24h " + arrow + " " +
                str(round(abs(change), 2)) + "%")
    except Exception as e:
        return "Crypto fetch fail: " + str(e)[:80]


# ============ 3. STOCK (Yahoo Finance) ============

_COMMON_TICKERS = {
    "tesla": "TSLA", "apple": "AAPL", "google": "GOOGL",
    "microsoft": "MSFT", "amazon": "AMZN", "meta": "META",
    "nvidia": "NVDA", "netflix": "NFLX",
    "reliance": "RELIANCE.NS", "tata": "TCS.NS",
    "infosys": "INFY.NS", "wipro": "WIPRO.NS",
}


def get_stock(symbol):
    """Get live stock price from Yahoo Finance (free)."""
    if not _YF:
        return "yfinance not available."

    sym = symbol.upper().strip()
    if sym.lower() in _COMMON_TICKERS:
        sym = _COMMON_TICKERS[sym.lower()]

    try:
        ticker = yf.Ticker(sym)
        info = ticker.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        change = info.get("regularMarketChangePercent", 0)
        name = info.get("shortName", sym)
        currency = info.get("currency", "USD")

        if price is None:
            return sym + " ka price nahi mila."

        arrow = "up" if change > 0 else "down"
        return (name + " (" + sym + "): " + str(round(price, 2)) + " " + currency +
                " | 24h " + arrow + " " + str(round(abs(change), 2)) + "%")
    except Exception as e:
        return "Stock fetch fail: " + str(e)[:80]


# ============ 4. WIKIPEDIA ============

def get_wikipedia(query):
    """Get summary from Wikipedia."""
    try:
        # Try search first
        search_url = ("https://en.wikipedia.org/w/api.php?action=query"
                      "&list=search&srsearch=" + urllib.parse.quote(query) +
                      "&format=json&srlimit=1")
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())

        results = data.get("query", {}).get("search", [])
        if not results:
            return None

        title = results[0]["title"]

        # Get summary
        summary_url = ("https://en.wikipedia.org/api/rest_v1/page/summary/" +
                       urllib.parse.quote(title))
        req = urllib.request.Request(summary_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            summary_data = json.loads(r.read())

        extract = summary_data.get("extract", "")
        if extract:
            return extract[:400]
        return None
    except Exception as e:
        return None


# ============ 5. WEB SEARCH (DuckDuckGo) ============

def search_web(query, max_results=3):
    """Search DuckDuckGo for current info."""
    if not _DDG:
        return "Web search not available."

    try:
        results = []
        # Add current year for time-sensitive queries
        q_lower = query.lower()
        if any(w in q_lower for w in ["kaun", "cm", "pm", "president",
                                       "latest", "aaj", "current", "abhi"]):
            query = query + " " + str(datetime.now().year)

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "").strip()
                body = r.get("body", "").strip()
                if title and body:
                    results.append(title + ": " + body[:200])

        if not results:
            return "Koi result nahi mila: " + query

        return "\n".join(results[:max_results])
    except Exception as e:
        return "Search fail: " + str(e)[:80]


# ============ 6. SMART DISPATCHER ============

def _detect_intent(query):
    """Detect what type of live data is needed."""
    q = query.lower()

    # Crypto
    for coin in _CRYPTO_IDS.keys():
        if coin in q:
            return ("crypto", coin)

    # Stock
    for name in _COMMON_TICKERS.keys():
        if name in q:
            return ("stock", name)
    if "stock" in q or "share price" in q:
        return ("stock", q.replace("stock", "").replace("price", "").strip())

    # News
    if any(w in q for w in ["news", "khabar", "headlines", "samachar"]):
        for topic in ["cricket", "technology", "politics", "business", "sports"]:
            if topic in q:
                return ("news", topic)
        return ("news", "top")

    # Person/place/current info (kaun hai, who is) - WEB FIRST (live data)
    if any(w in q for w in ["kaun hai", "who is", "kaun hain", "cm kaun"]):
        return ("web", query)

    # Static info (about, ke baare mein) - wiki OK
    if any(w in q for w in ["kya hai", "about", "ke baare mein"]):
        subject = re.sub(r"(kya hai|about|ke baare mein|\?)", "", q).strip()
        if subject:
            return ("wiki", subject)

    # Default - web search
    return ("web", query)


def get_live_answer(query):
    """
    Main dispatcher - picks right source for query.
    Returns string answer.
    """
    source, value = _detect_intent(query)
    print("[live_data] source=" + source + " value=" + str(value))

    if source == "crypto":
        return get_crypto(value)

    if source == "stock":
        return get_stock(value)

    if source == "news":
        return get_news(value)

    if source == "wiki":
        wiki = get_wikipedia(value)
        if wiki:
            return wiki
        # Fallback to web
        return search_web(query)

    if source == "web":
        return search_web(query)

    return "Live data nahi mila."


# ============ TESTS ============

if __name__ == "__main__":
    print("=" * 60)
    print("  LIVE DATA TEST")
    print("=" * 60)

    tests = [
        ("News", lambda: get_news("top", limit=3)),
        ("Cricket news", lambda: get_news("cricket", limit=3)),
        ("Bitcoin", lambda: get_crypto("bitcoin")),
        ("Ethereum", lambda: get_crypto("eth")),
        ("Tesla stock", lambda: get_stock("tesla")),
        ("Reliance stock", lambda: get_stock("reliance")),
        ("Wikipedia Modi", lambda: get_wikipedia("Narendra Modi")),
        ("Web search", lambda: search_web("Bihar CM 2026")),
        ("Smart: Bihar CM", lambda: get_live_answer("Bihar CM kaun hai")),
        ("Smart: Bitcoin", lambda: get_live_answer("bitcoin price kya hai")),
    ]

    for label, fn in tests:
        print("\n--- " + label + " ---")
        try:
            result = fn()
            if result:
                print(result[:300])
            else:
                print("(no result)")
        except Exception as e:
            print("ERROR: " + str(e)[:100])

"""
NOVA Web Search Live — Phase 1
Google/DuckDuckGo se CURRENT info nikalta hai.
"""
import re, json, urllib.parse, urllib.request
from datetime import datetime
_DDG=False
try:
 from ddgs import DDGS
 _DDG=True
except: 
 try:
  from duckduckgo_search import DDGS
  _DDG=True
 except: _DDG=False
def search_live(query, max_results=5):
 q=query.strip()
 if not _DDG: return "pip install ddgs karo."
 if any(w in q.lower() for w in ["kaun","cm","pm","latest","aaj","current","abhi"]) and str(datetime.now().year) not in q: q+=" "+str(datetime.now().year)
 try:
  res=[]
  with DDGS() as ddgs:
   for r in ddgs.text(q, max_results=max_results):
    t=(r.get("title")or"").strip(); b=(r.get("body")or"").strip()
    if t and b: res.append(f"{t}: {b[:220]}")
  return "\n".join(res[:max_results]) if res else f"Koi result nahi: {query}"
 except Exception as e: return f"Search fail: {e}"[:200]

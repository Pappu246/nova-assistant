"""
NOVA Semantic Memory - Phase 4: ChromaDB
Long-term vector memory with semantic search.
Fallback to SQLite if Chroma not available.
"""
import os, time, uuid
from pathlib import Path

BASE_DIR = Path.home() / "Documents" / "NOVA_Memory"
BASE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PATH = str(BASE_DIR / "chroma_db")

_CHROMA_AVAILABLE = False
_client = None
_collection = None

def _get_chroma():
    global _CHROMA_AVAILABLE, _client, _collection
    if _client is not None:
        return _client, _collection
    try:
        import chromadb
        from chromadb.config import Settings
        _client = chromadb.PersistentClient(path=CHROMA_PATH, settings=Settings(anonymized_telemetry=False))
        _collection = _client.get_or_create_collection(name="nova_semantic", metadata={"hnsw:space": "cosine"})
        _CHROMA_AVAILABLE = True
        print(f"[semantic] Chroma ready at {CHROMA_PATH}, count={_collection.count()}")
        return _client, _collection
    except Exception as e:
        print(f"[semantic] Chroma not available: {e}")
        _CHROMA_AVAILABLE = False
        return None, None

try:
    import memory as _legacy
except Exception:
    _legacy = None

def semantic_remember(args):
    text = args.get("text") or args.get("content") or args.get("value") or args.get("fact") or ""
    category = args.get("category") or "general"
    if not text or not text.strip():
        return "Kya yaad rakhna hai? Text bolo."
    text = text.strip()
    try:
        client, coll = _get_chroma()
        if coll is not None:
            doc_id = str(uuid.uuid4())[:8] + "_" + str(int(time.time()))
            meta = {"category": category, "timestamp": str(int(time.time())), "text": text[:500]}
            coll.add(documents=[text], ids=[doc_id], metadatas=[meta])
            if _legacy:
                _legacy.save_fact(f"sem_{doc_id[:6]}", text, category)
            return f"Semantic yaad rakh liya: {text[:60]}... (id:{doc_id[:6]})"
    except Exception as e:
        print(f"[semantic remember fail] {e}")
    if _legacy:
        return _legacy.save_fact(f"sem_{int(time.time())}", text, category)
    return f"Yaad rakh liya (fallback): {text[:60]}"

def semantic_recall(args):
    query = args.get("query") or args.get("text") or args.get("key") or ""
    n = int(args.get("n") or args.get("limit") or 3)
    if not query or not query.strip():
        return semantic_list({"limit": n})
    query = query.strip()
    try:
        client, coll = _get_chroma()
        if coll is not None and coll.count() > 0:
            res = coll.query(query_texts=[query], n_results=min(n, coll.count()))
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[]])[0]
            if docs:
                out = [f"'{query}' ke liye semantic yaad:"]
                for i, (d, m, dist) in enumerate(zip(docs, metas, dists)):
                    sim = 1 - dist if dist is not None else 0
                    cat = m.get("category", "") if m else ""
                    out.append(f"{i+1}. {d} (cat:{cat}, sim:{sim:.2f})")
                return "\n".join(out)
    except Exception as e:
        print(f"[semantic recall fail] {e}")
    if _legacy:
        res = _legacy.search_conversations(query, limit=n)
        if res and "kuch yaad nahi" not in res:
            return res
        facts = _legacy.list_facts(limit=5)
        if facts and "kuch yaad nahi" not in facts:
            return f"Semantic fallback - facts:\n{facts}"
    return f"'{query}' ke baare mein kuch khaas yaad nahi. Naya yaad kara do?"

def semantic_forget(args):
    text = args.get("text") or args.get("query") or args.get("id") or ""
    if not text:
        return "Kya bhoolna hai? Text bolo."
    try:
        client, coll = _get_chroma()
        if coll is not None:
            res = coll.query(query_texts=[text], n_results=5)
            ids = res.get("ids", [[]])[0]
            if ids:
                coll.delete(ids=ids[:2])
                return f"Bhool gaya: {text[:40]} (ids:{','.join(ids[:2])})"
    except Exception as e:
        print(f"[semantic forget fail] {e}")
    if _legacy:
        return _legacy.forget_fact(text)
    return "Bhool gaya (fallback)."

def semantic_list(args=None):
    limit = int((args or {}).get("limit") or 5)
    try:
        client, coll = _get_chroma()
        if coll is not None and coll.count() > 0:
            data = coll.peek(limit=limit)
            docs = data.get("documents", [])
            metas = data.get("metadatas", [])
            if docs:
                out = [f"Semantic memory ({coll.count()} total, {len(docs)} shown):"]
                for i, (d, m) in enumerate(zip(docs, metas)):
                    cat = m.get("category", "") if m else ""
                    out.append(f"{i+1}. [{cat}] {d[:80]}")
                return "\n".join(out)
    except Exception as e:
        print(f"[semantic list fail] {e}")
    if _legacy:
        return _legacy.list_facts(limit=limit)
    return "Koi semantic yaad nahi."

def get_semantic_context(query, k=3):
    try:
        res = semantic_recall({"query": query, "n": k})
        if res and "yaad nahi" not in res.lower():
            return res
    except Exception:
        pass
    return ""

TOOLS = {
    "semantic_remember": semantic_remember,
    "semantic_recall": semantic_recall,
    "semantic_forget": semantic_forget,
    "semantic_list": semantic_list,
}

if __name__ == "__main__":
    print("Testing semantic memory...")
    print(semantic_remember({"text": "Mujhe chai pasand hai, Jaipur me rehta hu", "category": "like"}))
    time.sleep(1)
    print(semantic_recall({"query": "chai kahan pasand hai", "n": 2}))
    print(semantic_list({"limit": 2}))

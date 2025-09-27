# Requires:
#   pip install chromadb ollama nltk tiktoken
# And run:
#   ollama serve
#   ollama pull mxbai-embed-large:latest

import os, re, json, hashlib
from typing import List, Dict, Any, Tuple
from datetime import datetime

import numpy as np
import chromadb
from ollama import embeddings as ollama_embeddings

# --------------------------
# Token estimation (for chunk sizing)
# --------------------------
try:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def ntokens(s: str) -> int: return len(enc.encode(s))
except:
    def ntokens(s: str) -> int: return max(1, len(s) // 4)

# --------------------------
# Markdown chunker (heading-aware, keeps code fences intact)
# --------------------------
CODE_FENCE = re.compile(r"(^```.*?$)(.*?)(^```$)", re.M | re.S)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)

def split_code_blocks(md: str) -> List[Tuple[str, bool]]:
    parts, last = [], 0
    for m in CODE_FENCE.finditer(md):
        if m.start() > last:
            prose = md[last:m.start()].strip()
            if prose: parts.append((prose, False))
        block = f"{m.group(1)}\n{m.group(2)}\n{m.group(3)}"
        parts.append((block.strip(), True))
        last = m.end()
    tail = md[last:].strip()
    if tail: parts.append((tail, False))
    return parts

def sectionize(md: str) -> List[Tuple[List[str], str]]:
    lines, sections, path, buf = md.splitlines(), [], [], []
    def flush():
        if buf:
            sections.append((path.copy(), "\n".join(buf).strip()))
            buf.clear()
    for line in lines:
        m = HEADING.match(line)
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            path = path[:level-1] + [title]
        buf.append(line)
    flush()
    cleaned = []
    for hp, sec in sections:
        ls = sec.splitlines()
        if ls and HEADING.match(ls[0]):
            sec = "\n".join(ls[1:]).strip()
        cleaned.append((hp or [], sec))
    return cleaned

def sentence_split(text: str) -> List[str]:
    # simple heuristic splitter
    return re.split(r"(?<=[\.\!\?])\s+(?=[A-ZÀ-ÖØ-Þ])", text.strip()) if text.strip() else []

def window_chunks(text: str, target_tokens: int, overlap_tokens: int) -> List[str]:
    tokens = re.split(r"(\s+)", text)
    acc, acc_tok, out = [], 0, []
    for t in tokens:
        acc.append(t)
        acc_tok += ntokens(t)
        if acc_tok >= target_tokens:
            blob = "".join(acc).strip()
            if blob: out.append(blob)
            tail = "".join(acc)[-max(1, overlap_tokens*4):]
            acc, acc_tok = [tail], ntokens(tail)
    if acc:
        blob = "".join(acc).strip()
        if blob: out.append(blob)
    return out

def window_chunks_sentences(text: str, target_tokens: int, overlap_tokens: int) -> List[str]:
    sents = sentence_split(text)
    out, cur, cur_tok = [], [], 0
    for s in sents:
        st = ntokens(s)
        if cur_tok + st <= target_tokens:
            cur.append(s); cur_tok += st
        else:
            if cur:
                out.append(" ".join(cur).strip())
                # overlap: keep last sentences up to overlap budget
                tail, tail_tok = [], 0
                for sent in reversed(cur):
                    tt = ntokens(sent)
                    if tail_tok + tt > overlap_tokens: break
                    tail.insert(0, sent); tail_tok += tt
                cur, cur_tok = tail, tail_tok
            cur.append(s); cur_tok += st
    if cur: out.append(" ".join(cur).strip())
    return out

def chunk_markdown(md: str, target_tokens=300, overlap_tokens=50) -> List[str]:
    chunks = []
    for seg, is_code in split_code_blocks(md):
        if is_code:
            chunks.append(seg)
            continue
        for _, section in sectionize(seg):
            if not section: continue
            paragraphs = [p for p in section.split("\n\n") if p.strip()]
            buf = []
            for p in paragraphs:
                joined = "\n\n".join(buf + [p])
                if ntokens(joined) <= target_tokens:
                    buf.append(p); continue
                if buf:
                    chunks.extend(window_chunks("\n\n".join(buf), target_tokens, overlap_tokens))
                    buf = []
                if ntokens(p) <= target_tokens:
                    chunks.append(p)
                else:
                    chunks.extend(window_chunks_sentences(p, target_tokens, overlap_tokens))
            if buf:
                chunks.extend(window_chunks("\n\n".join(buf), target_tokens, overlap_tokens))
    return [c for c in chunks if c.strip()]

# --------------------------
# Embeddings via Ollama (mxbai-embed-large) + L2 normalization
# --------------------------
EMBED_MODEL = "mxbai-embed-large:latest"

def l2_normalize(vecs: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms

def embed_texts(texts: List[str]) -> List[List[float]]:
    # Ollama's embeddings API typically processes one text per call
    out = []
    for t in texts:
        r = ollama_embeddings(model=EMBED_MODEL, prompt=t)
        v = np.array(r["embedding"], dtype=np.float32)
        out.append(v)
    vecs = np.vstack(out)
    vecs = l2_normalize(vecs)
    return vecs.astype(np.float32).tolist()

# --------------------------
# Chroma setup (cosine space)
# --------------------------
PERSIST_DIR = "../chromadb_data"
client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_or_create_collection(
    name="notes-chunking-test",
    metadata={"hnsw:space": "cosine"}  # cosine similarity in HNSW index
)

# --------------------------
# Ingest helpers
# --------------------------
def stable_note_id(title: str) -> str:
    return hashlib.sha1(title.encode("utf-8")).hexdigest()

def chunk_and_embed_note(note: Dict[str, Any], target_tokens=300, overlap_tokens=50):
    note_id = stable_note_id(note["title"])
    chunks = chunk_markdown(note["markdown"], target_tokens, overlap_tokens)
    ids, docs, metas = [], [], []
    for i, ch in enumerate(chunks):
        cid = hashlib.sha256(f"{note_id}|{note['modificationDate']}|{i}".encode()).hexdigest()
        ids.append(cid)
        docs.append(ch)
        metas.append({
            "note_id": note_id,
            "title": note["title"],
            "modificationDate": note["modificationDate"],
            "size": note["size"],
            "chunk_index": i,
        })
    vecs = embed_texts(docs) if docs else []
    return ids, docs, metas, vecs, note_id

def upsert_note(note: Dict[str, Any]):
    ids, docs, metas, vecs, note_id = chunk_and_embed_note(note)
    if not ids:
        return
    try:
        collection.delete(where={"note_id": note_id})
    except Exception:
        pass
    collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=vecs)

def query(q: str, top_k=6, where: Dict[str, Any] = None):
    qvec = embed_texts([q])[0]
    query_params = {
        "query_embeddings": [qvec],
        "n_results": top_k
    }
    if where:
        query_params["where"] = where
    return collection.query(**query_params)

# --------------------------
# Example driver
# --------------------------
if __name__ == "__main__":
    # Replace with your real data source (array or JSON file)
    notes = [
        {
            "title": "Note title",
            "markdown": "# Heading\nSome content about chunking.\n\n```python\nprint('code block kept whole')\n```",
            "size": 1234,
            "modificationDate": "2025-09-01T10:00:00Z"
        }
    ]

    print(f"Indexing {len(notes)} notes...")
    for n in notes:
        upsert_note(n)

    print(f"Querying...")
    res = query("How do I keep code blocks intact?")
    # Print top hits
    for md, doc in zip(res["metadatas"][0], res["documents"][0]):
        print(f"[{md['title']} #{md['chunk_index']}] → {doc[:120].replace('\\n', ' ')}...")
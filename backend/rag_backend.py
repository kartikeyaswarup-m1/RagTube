from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from urllib.parse import urlparse, parse_qs
import time, json, os, re

CACHE_FILE = "rag_cache.json"

vector_store  = None
chunks_store  = []
video_skeleton: str = ""
_cache: dict  = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_video_id(url):
    p = urlparse(url)
    if p.hostname == "youtu.be":
        return p.path[1:].split("?")[0]
    if p.hostname in ("www.youtube.com", "youtube.com"):
        return parse_qs(p.query).get("v", [None])[0]
    return None

def seconds_to_timestamp(s: float) -> str:
    s = int(s)
    return f"{s // 60}:{s % 60:02d}"

def build_chunks(entries) -> list[Document]:
    chunks, i = [], 0
    while i < len(entries):
        text, start, j = "", entries[i].start, i
        while j < len(entries) and len(text) < 600:
            text += " " + entries[j].text
            j += 1
        chunks.append(Document(
            page_content=text.strip(),
            metadata={"start": start, "timestamp": seconds_to_timestamp(start)}
        ))
        ov, step = 0, j - 1
        while step > i and ov < 120:
            ov += len(entries[step].text)
            step -= 1
        i = max(i + 1, step + 1)
    return chunks

def build_skeleton(entries) -> str:
    """
    Weighted sampling — sparse in the intro, dense in the main content.
    First 15% of video: sample every 90s (intro/setup gets fewer slots).
    Remaining 85%: sample every 20s (actual content gets more coverage).
    Each sample collects 10s of speech at that timestamp.
    """
    if not entries:
        return ""

    total_duration = entries[-1].start
    intro_cutoff   = total_duration * 0.15   # first 15% = intro

    lines, last = [], -90
    for e in entries:
        interval = 90 if e.start < intro_cutoff else 20
        if e.start - last >= interval:
            snippet = " ".join(x.text for x in entries if e.start <= x.start < e.start + 10).strip()
            if snippet:
                lines.append(f"[{seconds_to_timestamp(e.start)}] {snippet}")
            last = e.start
    return "\n".join(lines)


# ── Cache ─────────────────────────────────────────────────────────────────────

def _load_cache():
    global _cache
    try:
        with open(CACHE_FILE) as f:
            _cache = json.load(f)
    except Exception:
        _cache = {}

def _save_cache():
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(_cache, f)
    except Exception:
        pass

_load_cache()


# ── Video loader ──────────────────────────────────────────────────────────────

def load_video(video_url):
    global vector_store, chunks_store, video_skeleton, _cache

    video_id = extract_video_id(video_url)
    if not video_id:
        return "Could not extract video ID from the URL."

    try:
        entries = list(YouTubeTranscriptApi().fetch(video_id))
    except (TranscriptsDisabled, NoTranscriptFound):
        return "Transcripts are disabled or not found for this video."
    except Exception as e:
        return f"Could not fetch transcript: {e}"

    video_skeleton = build_skeleton(entries)
    chunks_store   = build_chunks(entries)
    vector_store   = FAISS.from_documents(
        chunks_store, HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )

    for k in [k for k in _cache if k.startswith(f"{video_id}:")]:
        del _cache[k]

    print(f"Indexed {len(chunks_store)} chunks. Skeleton: {len(video_skeleton)} chars.")
    return None


# ── LLM & prompts ─────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    max_tokens=1024,
)

classifier_prompt = ChatPromptTemplate.from_template("""
Classify this question about a YouTube video into exactly one of three categories:

SUMMARY  — asks for a general overview, summary, or what the video is about.
LISTING  — asks to enumerate or list specific distinct items from the video.
SPECIFIC — asks about a particular detail, explanation, or moment.

Question: {question}
Reply with exactly one word — SUMMARY, LISTING, or SPECIFIC:
""")

summary_prompt = ChatPromptTemplate.from_template("""
Summarise this YouTube video as a bullet point list (5-8 bullets).
Each bullet MUST be on its own separate line starting with "- ".
Include the timestamp naturally in each bullet, e.g. "(at 8:13)".
Keep each bullet concise — one sentence max.
Do not put multiple bullets on the same line.

Video outline:
{skeleton}

Summary:
""")

listing_prompt = ChatPromptTemplate.from_template("""
Using the timestamped video outline, answer the question by listing only the
core top-level items — like a table of contents, not sub-details.

Rules:
- If the same subject appears multiple times (e.g. continued later), list it ONCE
  at its earliest timestamp. Never add "(continued)" or repeat an item.
- Only include items that are clearly a main focus, not passing mentions.
- Format: "N. Item name (at MM:SS)". Plain numbered list, nothing else.

Question: {question}

Video outline:
{skeleton}

List:
""")

rag_prompt = ChatPromptTemplate.from_template("""
Answer the question using only the context below.
Be thorough. Reference [MM:SS] timestamps naturally. Never invent information.

Context:
{context}

Question: {question}

Answer:
""")

rewrite_prompt = ChatPromptTemplate.from_template("""
You are given a conversation history and a follow-up question.
If the question contains pronouns like "it", "they", "he", "she", replace them
with the correct noun from the history. Otherwise return the question UNCHANGED.
Never rephrase, never add information, never change the meaning.
Return only the question text, nothing else.

History:
{history}

Question: {question}

Output:
""")

classifier_chain = classifier_prompt | llm | StrOutputParser()
rewrite_chain    = rewrite_prompt    | llm | StrOutputParser()


# ── Query classification ──────────────────────────────────────────────────────

def classify_query(question: str) -> str:
    q = question.lower()
    listing_signals = {"topics", "problems", "questions", "concepts",
                       "items", "covered", "solved", "list"}
    specific_signals = {"who", "speaker", "host", "when", "explain",
                        "how does", "how do", "why", "define", "compare"}

    if any(w in q for w in specific_signals) and not any(w in q for w in listing_signals):
        return "SPECIFIC"
    if any(w in q for w in ("summarize", "summarise", "summary", "overview")):
        return "SUMMARY"
    if len(set(q.split()) & {"list", "what", "which", "all"} & listing_signals) >= 1 \
       or len(set(q.split()) & listing_signals) >= 1:
        return "LISTING"

    result = classifier_chain.invoke({"question": question}).strip().upper()
    if "SUMMARY" in result:  return "SUMMARY"
    if "LISTING" in result:  return "LISTING"
    return "SPECIFIC"


# ── LISTING: verify rough list against FAISS ──────────────────────────────────

def _verify_listing(rough: str) -> str:
    """Drop items not well-supported in the transcript, re-number cleanly."""
    verified = []
    for line in rough.strip().splitlines():
        m = re.match(r'^\d+\.\s+(.+?)(?:\s*\(at\s*[\d:]+\))?$', line.strip())
        if not m:
            continue
        score = vector_store.similarity_search_with_score(m.group(1).strip(), k=1)[0][1]
        if score <= 1.4:
            clean = re.sub(r'^[\d]+\.\s+|^[*\-]\s+', '', line.strip())
            verified.append(clean)

    # fallback — nothing passed, keep all parsed lines
    if not verified:
        for line in rough.strip().splitlines():
            m = re.match(r'^\d+\.\s+(.+)', line.strip())
            if m:
                verified.append(m.group(1).strip())

    # Deduplicate — strip qualifier prefixes so "Brute Force for X" and
    # "Optimal for X" both normalize to "X" and count as the same item.
    STRIP_PREFIXES = re.compile(
        r'^(brute force|optimal|better|improved|naive|two.?pointer|'
        r'approach|solution|method|technique)\s+(for\s+|to\s+)?',
        re.IGNORECASE
    )
    seen, deduped = set(), []
    for l in verified:
        key = l.lower().split("(")[0].strip()          # drop timestamp
        key = STRIP_PREFIXES.sub("", key).strip()      # drop qualifier
        if key not in seen:
            seen.add(key)
            # Keep earliest occurrence — but use clean subject name not qualifier
            subject = STRIP_PREFIXES.sub("", l.split("(")[0].strip()).strip()
            ts      = re.search(r'\(at [\d:]+\)', l)
            deduped.append(f"{subject} {ts.group() if ts else ''}".strip())
    return "\n".join(f"{i}. {l}" for i, l in enumerate(deduped, 1))


# ── SPECIFIC: retrieve with neighbouring chunks ───────────────────────────────

def _retrieve(question: str) -> list[Document]:
    candidates     = vector_store.similarity_search_with_score(question, k=4)
    relevant       = [d for d, s in candidates if s <= 1.5] or [d for d, _ in candidates[:3]]
    matched_starts = {d.metadata["start"] for d in relevant}
    expanded, seen = list(relevant), set(matched_starts)

    for idx, chunk in enumerate(chunks_store):
        if chunk.metadata["start"] in matched_starts:
            for nb in [chunks_store[idx-1] if idx > 0 else None,
                       chunks_store[idx+1] if idx < len(chunks_store)-1 else None]:
                if nb and nb.metadata["start"] not in seen:
                    expanded.append(nb)
                    seen.add(nb.metadata["start"])

    return sorted(expanded, key=lambda d: d.metadata["start"])


# ── Main entry point ──────────────────────────────────────────────────────────

def ask_question(question: str, chat_history: list, query_type: str, video_url: str) -> tuple:
    if vector_store is None:
        return "Please load a video first.", [], question

    history_text = "\n".join(f"{role}: {msg}" for role, msg in chat_history)
    rewritten = rewrite_chain.invoke({"history": history_text, "question": question}).strip() \
                if history_text.strip() else question

    video_id = extract_video_id(video_url) or "unknown"

    if query_type == "SUMMARY":
        cache_key = f"{video_id}:SUMMARY"
        if cache_key not in _cache:
            _cache[cache_key] = llm.invoke(summary_prompt.invoke({"skeleton": video_skeleton})).content
            _save_cache()
        answer, sources = _cache[cache_key], []

    elif query_type == "LISTING":
        cache_key = f"{video_id}:LISTING:{rewritten.lower().strip()}"
        if cache_key not in _cache:
            rough    = llm.invoke(listing_prompt.invoke({"question": rewritten, "skeleton": video_skeleton})).content
            _cache[cache_key] = _verify_listing(rough)
            _save_cache()
        answer, sources = _cache[cache_key], []

    else:  # SPECIFIC
        docs    = _retrieve(rewritten)
        context = "\n\n---\n\n".join(f"[{d.metadata['timestamp']}] {d.page_content}" for d in docs)
        answer  = llm.invoke(rag_prompt.invoke({"context": context, "question": rewritten})).content
        raw     = vector_store.similarity_search_with_score(rewritten, k=3)
        sources = [(d.page_content, s, d.metadata["start"]) for d, s in raw]

    chat_history.append(("User", question))
    chat_history.append(("AI", answer))
    return answer, sources, rewritten
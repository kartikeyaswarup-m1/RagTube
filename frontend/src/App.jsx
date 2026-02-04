import { useMemo, useState } from "react";

const DEFAULT_API = "http://127.0.0.1:8000";

export default function App() {
  const apiBase = useMemo(
    () => import.meta.env.VITE_API_BASE || DEFAULT_API,
    []
  );

  const [videoUrl, setVideoUrl] = useState("");
  const [ingestStatus, setIngestStatus] = useState(null);
  const [ingestBusy, setIngestBusy] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [queryBusy, setQueryBusy] = useState(false);
  const [error, setError] = useState("");

  const canIngest = videoUrl.trim().length > 0 && !ingestBusy;
  const canAsk = question.trim().length > 0 && !queryBusy;

  const handleIngest = async (event) => {
    event.preventDefault();
    setError("");
    setIngestStatus(null);
    setIngestBusy(true);

    try {
      const url = `${apiBase}/ingest?video_url=${encodeURIComponent(videoUrl.trim())}`;
      const response = await fetch(url);
      const data = await response.json();
      setIngestStatus(data);
    } catch (err) {
      setError(err?.message || "Failed to ingest video.");
    } finally {
      setIngestBusy(false);
    }
  };

  const handleQuery = async (event) => {
    event.preventDefault();
    setError("");
    setAnswer("");
    setQueryBusy(true);

    try {
      const url = `${apiBase}/query?question=${encodeURIComponent(question.trim())}`;
      const response = await fetch(url, {
        headers: {
          Accept: "application/x-ndjson"
        }
      });

      if (!response.ok || !response.body) {
        throw new Error("Query failed. Check backend logs.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let newlineIndex = buffer.indexOf("\n");
        while (newlineIndex !== -1) {
          const line = buffer.slice(0, newlineIndex).trim();
          buffer = buffer.slice(newlineIndex + 1);

          if (line) {
            try {
              const payload = JSON.parse(line);
              if (payload.error) {
                setError(payload.error);
              }
              if (payload.text) {
                setAnswer((prev) => prev + payload.text);
              }
              if (payload.done) {
                await reader.cancel();
                break;
              }
            } catch {
              // Ignore malformed lines
            }
          }

          newlineIndex = buffer.indexOf("\n");
        }
      }
    } catch (err) {
      setError(err?.message || "Failed to query the model.");
    } finally {
      setQueryBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="eyebrow">Local RAG • Ollama • YouTube</p>
          <h1>RagTube</h1>
          <p className="subtitle">
            Turn any YouTube transcript into a searchable knowledge base and get
            streaming answers instantly.
          </p>
        </div>
        <div className="hero-card">
          <div className="metric">
            <span>Chunks</span>
            <strong>{ingestStatus?.chunks ?? "—"}</strong>
          </div>
          <div className="metric">
            <span>Status</span>
            <strong>
              {ingestBusy
                ? "Processing"
                : ingestStatus?.status || "Ready"}
            </strong>
          </div>
        </div>
      </header>

      <main className="content">
        <section className="panel">
          <div className="panel-header">
            <h2>1. Ingest a video</h2>
            <p>Paste a YouTube URL and build your vector store.</p>
          </div>
          <form className="panel-body" onSubmit={handleIngest}>
            <input
              type="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={videoUrl}
              onChange={(event) => setVideoUrl(event.target.value)}
              required
            />
            <button className="primary" type="submit" disabled={!canIngest}>
              {ingestBusy ? "Ingesting…" : "Ingest video"}
            </button>
          </form>
          {ingestStatus && (
            <div className={`status ${ingestStatus.status || "info"}`}>
              <strong>{ingestStatus.status?.toUpperCase() || "INFO"}</strong>
              <span>
                {ingestStatus.transcript ||
                  ingestStatus.error ||
                  `Stored ${ingestStatus.chunks || 0} chunks.`}
              </span>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>2. Ask a question</h2>
            <p>Stream an answer grounded in the ingested transcript.</p>
          </div>
          <form className="panel-body" onSubmit={handleQuery}>
            <input
              type="text"
              placeholder="What is the main takeaway?"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              required
            />
            <button className="primary" type="submit" disabled={!canAsk}>
              {queryBusy ? "Thinking…" : "Ask"}
            </button>
          </form>
          <div className="answer-card">
            <div className="answer-header">
              <h3>Answer</h3>
              {queryBusy && <span className="pulse">Streaming</span>}
            </div>
            <p className={`answer ${answer ? "" : "muted"}`}>
              {answer || "Start by ingesting a video, then ask your question."}
            </p>
          </div>
        </section>

        {error && (
          <section className="panel error">
            <strong>Something went wrong.</strong>
            <span>{error}</span>
          </section>
        )}
      </main>

      <footer className="footer">
        <span>Built for local, private RAG workflows.</span>
        <span>Powered by FastAPI + Ollama.</span>
      </footer>
    </div>
  );
}

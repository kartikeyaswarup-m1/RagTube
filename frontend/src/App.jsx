import { useMemo, useState } from "react";

const DEFAULT_API = "http://127.0.0.1:8001";

export default function App() {
  const apiBase = useMemo(
    () => import.meta.env.VITE_API_BASE || DEFAULT_API,
    []
  );

  const [videoUrl, setVideoUrl] = useState("");
  const [ingestStatus, setIngestStatus] = useState(null);
  const [ingestBusy, setIngestBusy] = useState(false);

  const [question, setQuestion] = useState("");
  const [queryBusy, setQueryBusy] = useState(false);
  const [error, setError] = useState("");
  const [videoDetails, setVideoDetails] = useState(null);
  const [activeTimestamp, setActiveTimestamp] = useState(0);
  const [provider, setProvider] = useState("ollama");

  // Chat conversation messages
  const [messages, setMessages] = useState(() => {
    return [];
  });

  const canIngest = videoUrl.trim().length > 0 && !ingestBusy;
  const canAsk = question.trim().length > 0 && !queryBusy;

  const saveChatMessage = (newMessage) => {
    const updated = [...messages, newMessage];
    setMessages(updated);
  };

  const streamingDelay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const seekToTimestamp = (timestampLabel) => {
    const parts = timestampLabel.split(":").map((value) => Number(value));
    let seconds = 0;

    if (parts.length === 2) {
      seconds = parts[0] * 60 + parts[1];
    } else if (parts.length === 3) {
      seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
    }

    setActiveTimestamp(seconds);
  };

  const renderInlineContent = (text, keyPrefix) => {
    const pattern = /(\[(\d{2}:\d{2}(?::\d{2})?)\])|(\*\*[^*]+\*\*)/g;
    const parts = [];
    let lastIndex = 0;
    let match = null;

    while ((match = pattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(
          <span key={`${keyPrefix}-text-${lastIndex}`}>
            {text.slice(lastIndex, match.index)}
          </span>
        );
      }

      if (match[2]) {
        const timestampValue = match[2];
        parts.push(
          <button
            key={`${keyPrefix}-timestamp-${match.index}`}
            type="button"
            className="timestamp-chip"
            onClick={() => seekToTimestamp(timestampValue)}
            title={`Jump to ${timestampValue}`}
          >
            {timestampValue}
          </button>
        );
      } else {
        parts.push(
          <strong key={`${keyPrefix}-bold-${match.index}`}>
            {match[0].slice(2, -2)}
          </strong>
        );
      }

      lastIndex = pattern.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(
        <span key={`${keyPrefix}-text-${lastIndex}`}>{text.slice(lastIndex)}</span>
      );
    }

    return parts;
  };

  const renderRichMessage = (content) => {
    const lines = content.split(/\r?\n/);
    const blocks = [];
    let paragraphBuffer = [];
    let listBuffer = null;

    const flushParagraph = () => {
      const paragraph = paragraphBuffer.join(" ").trim();
      if (paragraph) {
        blocks.push({ type: "paragraph", text: paragraph });
      }
      paragraphBuffer = [];
    };

    const flushList = () => {
      if (listBuffer) {
        blocks.push(listBuffer);
        listBuffer = null;
      }
    };

    lines.forEach((rawLine) => {
      const line = rawLine.trim();

      if (!line) {
        flushParagraph();
        flushList();
        return;
      }

      const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
      const orderedMatch = line.match(/^\d+\.\s+(.*)$/);
      const bulletMatch = line.match(/^[-*]\s+(.*)$/);

      if (headingMatch) {
        flushParagraph();
        flushList();
        blocks.push({ type: "heading", level: headingMatch[1].length, text: headingMatch[2] });
        return;
      }

      if (orderedMatch || bulletMatch) {
        flushParagraph();
        const ordered = Boolean(orderedMatch);
        const itemText = (orderedMatch?.[1] || bulletMatch?.[1] || "").trim();
        if (!listBuffer) {
          listBuffer = { type: "list", ordered, items: [] };
        }

        listBuffer.ordered = listBuffer.ordered || ordered;
        listBuffer.items.push(itemText);
        return;
      }

      flushList();
      paragraphBuffer.push(line);
    });

    flushParagraph();
    flushList();

    return blocks.map((block, blockIndex) => {
      if (block.type === "heading") {
        const HeadingTag = `h${Math.min(3, block.level + 1)}`;
        return (
          <HeadingTag key={`block-${blockIndex}`} className={`message-heading level-${block.level}`}>
            {renderInlineContent(block.text, `heading-${blockIndex}`)}
          </HeadingTag>
        );
      }

      if (block.type === "list") {
        const ListTag = block.ordered ? "ol" : "ul";
        return (
          <ListTag key={`block-${blockIndex}`} className={`message-list ${block.ordered ? "ordered" : "unordered"}`}>
            {block.items.map((item, itemIndex) => (
              <li key={`block-${blockIndex}-item-${itemIndex}`} className="message-list-item">
                {renderInlineContent(item, `list-${blockIndex}-${itemIndex}`)}
              </li>
            ))}
          </ListTag>
        );
      }

      return (
        <p key={`block-${blockIndex}`} className="message-paragraph">
          {renderInlineContent(block.text, `paragraph-${blockIndex}`)}
        </p>
      );
    });
  };

  const clearChat = () => {
    if (confirm("Clear all chat messages?")) {
      setMessages([]);
    }
  };

  const formatTimestamp = (seconds) => {
    const totalSeconds = Math.max(0, Math.floor(Number(seconds) || 0));
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const remainingSeconds = totalSeconds % 60;

    if (hours > 0) {
      return [hours, minutes, remainingSeconds]
        .map((value) => String(value).padStart(2, "0"))
        .join(":");
    }

    return [minutes, remainingSeconds]
      .map((value) => String(value).padStart(2, "0"))
      .join(":");
  };

  const extractVideoId = (url) => {
    try {
      const parsedUrl = new URL(url);
      if (parsedUrl.hostname.includes("youtu.be")) {
        return parsedUrl.pathname.replace("/", "");
      }

      if (parsedUrl.searchParams.get("v")) {
        return parsedUrl.searchParams.get("v");
      }

      const match = parsedUrl.pathname.match(/(?:shorts|embed)\/([^/]+)/);
      return match?.[1] || "";
    } catch {
      return "";
    }
  };

  const currentVideoId = videoDetails?.video_id || extractVideoId(videoUrl);
  const embedSource = currentVideoId
    ? `https://www.youtube.com/embed/${currentVideoId}?rel=0&modestbranding=1&start=${activeTimestamp}`
    : "";

  const handleIngest = async (event) => {
    event.preventDefault();
    setError("");
    setIngestStatus(null);
    setVideoDetails(null);
    setActiveTimestamp(0);
    setIngestBusy(true);

    try {
      const url = `${apiBase}/ingest?video_url=${encodeURIComponent(videoUrl.trim())}`;
      const response = await fetch(url);
      let data = null;
      try {
        data = await response.json();
      } catch (e) {
        const text = await response.text().catch(() => "<non-JSON response>");
        data = { status: response.ok ? "ok" : "error", error: text };
      }

      console.debug("/ingest response", response.status, data);
      setIngestStatus(data);
      if (data?.status === "ingested") {
        setVideoDetails(data);
      } else if (!response.ok) {
        setError(data?.error || `Ingest failed with status ${response.status}`);
      }
    } catch (err) {
      setError(err?.message || "Failed to ingest video.");
    } finally {
      setIngestBusy(false);
    }
  };

  const handleQuery = async (event) => {
    event.preventDefault();
    setError("");
    setQueryBusy(true);

    const q = question.trim();
    let finalAnswer = "";

    // Add user message immediately
    saveChatMessage({ role: "user", content: q });
    setQuestion("");

    // Add empty assistant placeholder immediately
    const assistantIndex = messages.length + 1; // Index where assistant message will be
    saveChatMessage({ role: "assistant", content: "" });

    try {
      const url = `${apiBase}/query?question=${encodeURIComponent(q)}&provider=${encodeURIComponent(provider)}`;
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
                finalAnswer += payload.text;
                await streamingDelay(28);
                // Update the assistant message in real-time
                setMessages((prev) => {
                  const updated = [...prev];
                  if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
                    updated[updated.length - 1].content = finalAnswer;
                  }
                  return updated;
                });
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
      // Remove the empty placeholder and add error message
      setMessages((prev) => {
        const updated = [...prev];
        if (updated.length > 0 && updated[updated.length - 1].role === "assistant" && !updated[updated.length - 1].content) {
          updated[updated.length - 1] = { role: "error", content: err?.message || "Failed to query the model." };
        }
        return updated;
      });
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
        <div className="workspace-grid">
          <div className="workspace-left">
            <section className="video-stage">
              <div className="stage-shell">
                <div className="stage-header">
                  <div>
                    <span className="stage-kicker">Now playing</span>
                    <h2>{videoDetails?.title || "No video loaded yet"}</h2>
                    <p>
                      {videoDetails
                        ? "The ingested video lives here, centered in the workflow so it feels built into the app."
                        : "Ingest a YouTube URL to load the player here."}
                    </p>
                  </div>
                  {videoDetails && (
                    <div className="stage-meta">
                      <span>Video loaded</span>
                      <strong>{videoDetails.segments?.length || 0} cues</strong>
                    </div>
                  )}
                </div>

                <div className={`stage-player ${videoDetails ? "has-video" : "empty"}`}>
                  {videoDetails ? (
                    <iframe
                      title={videoDetails.title || "Inserted YouTube video"}
                      src={embedSource}
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    />
                  ) : (
                    <div className="video-empty">
                      <strong>No video loaded yet.</strong>
                      <span>Use the ingest box below to bring a video into focus.</span>
                    </div>
                  )}
                </div>
              </div>
            </section>

            {/* Ingest Section */}
            <section className="panel">
              <div className="panel-header">
                <h2>1. Ingest a video</h2>
                <p>Paste a YouTube URL to get started.</p>
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
                    {ingestStatus.error || `Stored ${ingestStatus.chunks || 0} chunks.`}
                  </span>
                </div>
              )}
            </section>
          </div>

            {/* Chat Section */}
          <aside className="workspace-right">
            <section className="panel chat-panel">
              <div className="panel-header">
                <h2>2. Chat about the video</h2>
                {messages.length > 0 && (
                  <button
                    type="button"
                    className="ghost small"
                    onClick={clearChat}
                    title="Clear chat"
                  >
                    Clear
                  </button>
                )}
              </div>

              <div className="chat-messages">
                {messages.length === 0 ? (
                  <p className="empty-chat-placeholder">Ingest a video and start asking questions!</p>
                ) : (
                  messages.map((msg, idx) => (
                    <div key={idx} className={`chat-message chat-${msg.role} ${msg.role === "assistant" && !msg.content ? "streaming" : ""}`}>
                      {msg.role === "user" && <div className="message-label">You</div>}
                      {msg.role === "error" && <div className="message-label">Error</div>}
                      <div className={`message-content ${msg.role === "assistant" ? "rich-message" : ""}`}>
                        {msg.role === "assistant" && !msg.content && <div className="streaming-indicator"><span></span><span></span><span></span></div>}
                        {msg.role === "assistant" && msg.content ? renderRichMessage(msg.content) : (msg.role === "user" || msg.role === "error") && msg.content}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <form className="chat-input-form" onSubmit={handleQuery}>
                <div className="chat-input-group">
                  <label className="field-label" htmlFor="provider-select">
                    Provider
                  </label>
                  <select
                    id="provider-select"
                    value={provider}
                    onChange={(event) => setProvider(event.target.value)}
                    disabled={!videoDetails}
                  >
                    <option value="ollama">Ollama (local)</option>
                    <option value="groq">Groq API</option>
                  </select>
                </div>
                <div className="chat-input-group">
                  <input
                    type="text"
                    placeholder="Ask a question about the video..."
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    disabled={!videoDetails}
                    required
                  />
                  <button
                    className="primary"
                    type="submit"
                    disabled={!canAsk || !videoDetails}
                  >
                    {queryBusy ? "…" : "Send"}
                  </button>
                </div>
              </form>
            </section>
          </aside>
        </div>

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

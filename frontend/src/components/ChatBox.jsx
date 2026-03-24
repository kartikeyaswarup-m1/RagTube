import { useState, useEffect, useRef } from "react"
import Answer from "./Answer"

// ChatBox shows the conversation and the question input.
// Props:
// - chatHistory: array of message objects
// - onAsk: function to call when user submits a question
// - onClear: function to clear the chat
// - onTimestampClick: function to seek the video player
// - loading: boolean
// - videoId: for source iframes

export default function ChatBox({ chatHistory, onAsk, onClear, onTimestampClick, loading, videoId }) {
  const [question, setQuestion] = useState("")

  // useRef on the messages div lets us auto-scroll to the bottom
  // when new messages arrive
  const bottomRef = useRef(null)

  // useEffect runs after every render where chatHistory changed.
  // We use it to scroll to the bottom automatically.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatHistory])

  function handleSubmit(e) {
    e.preventDefault()
    if (question.trim() && !loading) {
      onAsk(question.trim())
      setQuestion("")   // clear input after sending
    }
  }

  return (
    <div className="chatbox">

      {/* Messages area */}
      <div className="messages">
        {chatHistory.length === 0 && (
          <div className="chat-empty">Ask anything about the video</div>
        )}

        {chatHistory.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <div className="bubble">
              {msg.role === "user" ? (
                // User message — plain text
                <p>{msg.content}</p>
              ) : (
                // AI message — Answer component handles clickable timestamps
                <>
                  {msg.rewritten && msg.rewritten !== chatHistory[i-1]?.content && (
                    <p className="rewritten-query">🔍 {msg.rewritten}</p>
                  )}
                  <Answer
                    content={msg.content}
                    onTimestampClick={onTimestampClick}
                  />
                  {/* Sources — shown only for SPECIFIC answers */}
                  {msg.sources && msg.sources.length > 0 && (
                    <Sources
                      sources={msg.sources}
                      videoId={videoId}
                      onTimestampClick={onTimestampClick}
                    />
                  )}
                </>
              )}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="message ai">
            <div className="bubble loading-bubble">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}

        {/* Invisible div at the bottom — we scroll to this */}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        <form onSubmit={handleSubmit} className="chat-form">
          <input
            type="text"
            placeholder="Ask a question about the video..."
            value={question}
            onChange={e => setQuestion(e.target.value)}
            disabled={loading}
            className="chat-input"
          />
          <button type="submit" disabled={loading || !question.trim()} className="ask-btn">
            Send
          </button>
        </form>
        <button onClick={onClear} className="clear-btn">Clear chat</button>
      </div>

    </div>
  )
}

// ── Sources component ─────────────────────────────────────────────────────────
// Small inline component — shows the source chunks with timestamp buttons.
// Clicking a source timestamp seeks the main player (same as clicking in answer text).

function Sources({ sources, videoId, onTimestampClick }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="sources">
      <button className="sources-toggle" onClick={() => setExpanded(e => !e)}>
        {expanded ? "Hide sources ▲" : `Show sources (${sources.length}) ▼`}
      </button>

      {expanded && sources.map((src, i) => {
        const ts = `${Math.floor(src.start / 60)}:${String(src.start % 60).padStart(2, "0")}`
        return (
          <div key={i} className="source-item">
            <div className="source-header">
              <span>Source {i + 1}</span>
              <span className="source-score">score: {src.score}</span>
              <button
                className="source-timestamp"
                onClick={() => onTimestampClick(src.start)}
              >
                ▶ {ts}
              </button>
            </div>
            <p className="source-text">{src.text.slice(0, 200)}...</p>
          </div>
        )
      })}
    </div>
  )
}
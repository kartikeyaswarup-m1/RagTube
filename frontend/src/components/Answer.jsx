// Answer renders the AI response text.
// It finds timestamps like (at 8:42) or [8:42] and makes them clickable.
// When clicked, they call onTimestampClick(seconds) which seeks the player.

export default function Answer({ content, onTimestampClick }) {
  // Split into lines. If a line starts with "- " or "* " or a number,
  // treat it as a bullet. Otherwise render as a paragraph.
  const lines = content.split("\n").filter(l => l.trim())

  const isBullet = l => /^[-*•]/.test(l.trim()) || /^\d+\./.test(l.trim())

  return (
    <div className="answer-text">
      {lines.map((line, i) => {
        const clean = line.replace(/^[-*•]\s*/, "").replace(/^\d+\.\s*/, "")
        const parts = parseTimestamps(clean)
        const rendered = parts.map((part, j) =>
          part.type === "timestamp" ? (
            <span
              key={j}
              className="timestamp-link"
              onClick={() => onTimestampClick(part.seconds)}
              title={`Jump to ${part.label}`}
            >
              ▶ {part.label}
            </span>
          ) : (
            <span key={j}>{part.text}</span>
          )
        )
        return isBullet(line)
          ? <div key={i} className="bullet-line">• {rendered}</div>
          : <p key={i}>{rendered}</p>
      })}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function parseTimestamps(text) {
  // Matches patterns like: (at 8:42), [8:42], at 8:42, (at 1:05:30)
  const regex = /(?:\(at\s+|at\s+|\[)((?:\d+:)?\d+:\d+)(?:\)|\])?/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    // Push the text before this match
    if (match.index > lastIndex) {
      parts.push({ type: "text", text: text.slice(lastIndex, match.index) })
    }
    // Push the timestamp
    parts.push({
      type: "timestamp",
      label: match[1],
      seconds: timestampToSeconds(match[1]),
    })
    lastIndex = regex.lastIndex
  }

  // Push any remaining text after the last match
  if (lastIndex < text.length) {
    parts.push({ type: "text", text: text.slice(lastIndex) })
  }

  return parts
}

function timestampToSeconds(ts) {
  // Converts "8:42" → 522, "1:05:30" → 3930
  const parts = ts.split(":").map(Number)
  if (parts.length === 2) return parts[0] * 60 + parts[1]
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]
  return 0
}
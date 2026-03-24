import { useState } from "react"

// VideoLoader receives two props from App:
// - onLoad: function to call when user submits a URL
// - loading: boolean — is something loading right now?
// - loadingMsg: string — what to show while loading

export default function VideoLoader({ onLoad, loading, loadingMsg }) {

  // Local state — just for this component's input field
  const [url, setUrl] = useState("")

  function handleSubmit(e) {
    e.preventDefault()          // prevent page refresh (default form behaviour)
    if (url.trim()) onLoad(url.trim())
  }

  return (
    <div className="video-loader">
      <form onSubmit={handleSubmit} className="url-form">
        <input
          type="text"
          placeholder="Paste YouTube URL..."
          value={url}
          // onChange fires on every keystroke.
          // e.target.value is what the user typed.
          // We update local state so the input stays controlled by React.
          onChange={e => setUrl(e.target.value)}
          disabled={loading}
          className="url-input"
        />
        <button type="submit" disabled={loading} className="load-btn">
          {loading ? loadingMsg : "Load Video"}
        </button>
      </form>
    </div>
  )
}
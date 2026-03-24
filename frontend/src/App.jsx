import { useState } from "react"
import axios from "axios"
import VideoLoader from "./components/VideoLoader"
import ChatBox from "./components/ChatBox"
import "./App.css"

// App is the ROOT component — it owns all the shared state.
// Child components receive data via "props" (like function arguments).
// When the user does something in a child, it calls a function passed
// down from App to update the state here.

export default function App() {

  // useState(initialValue) returns [currentValue, setterFunction]
  // When you call the setter, React re-renders the component.
  const [videoUrl, setVideoUrl]       = useState("")        // the YouTube URL
  const [videoId, setVideoId]         = useState("")        // extracted video ID
  const [videoLoaded, setVideoLoaded] = useState(false)     // is a video loaded?
  const [chatHistory, setChatHistory] = useState([])        // array of {role, content, sources}
  const [activeTime, setActiveTime]   = useState(null)      // timestamp clicked by user
  const [loading, setLoading]         = useState(false)     // loading spinner state
  const [loadingMsg, setLoadingMsg]   = useState("")        // message shown while loading

  // Extract video ID from a YouTube URL
  // e.g. "https://youtu.be/abc123" → "abc123"
  function extractVideoId(url) {
    const patterns = [
      /youtu\.be\/([^?&]+)/,
      /v=([^?&]+)/,
    ]
    for (const pattern of patterns) {
      const match = url.match(pattern)
      if (match) return match[1]
    }
    return null
  }

  // Called when user clicks "Load Video"
  async function handleLoadVideo(url) {
    setLoading(true)
    setLoadingMsg("Processing video...")
    try {
      const res = await axios.post("/api/load-video", { url })
      if (res.data.success) {
        setVideoUrl(url)
        setVideoId(extractVideoId(url))
        setVideoLoaded(true)
        setChatHistory([])   // clear chat when new video loaded
      } else {
        alert(res.data.error)
      }
    } catch (e) {
      alert("Failed to load video. Is the backend running?")
    }
    setLoading(false)
  }

  // Called when user asks a question
  async function handleAsk(question) {
    // First classify the question to show right loading message
    const classifyRes = await axios.post("/api/classify", { url: question })
    const queryType = classifyRes.data.query_type

    setLoading(true)
    setLoadingMsg(
      queryType === "SPECIFIC"
        ? "Thinking..."
        : "Scanning full video outline..."
    )

    // Capture history BEFORE optimistic update so backend gets clean history
    const historySnapshot = chatHistory.map(m => [m.role === "user" ? "User" : "AI", m.content])

    // Add user message to chat immediately (optimistic update)
    setChatHistory(prev => [...prev, { role: "user", content: question }])

    try {
      const res = await axios.post("/api/ask", {
        question,
        query_type: queryType,
        video_url: videoUrl,
        chat_history: historySnapshot
      })
      // Add AI response to chat
      setChatHistory(prev => [...prev, {
        role: "ai",
        content: res.data.answer,
        sources: res.data.sources,
        rewritten: res.data.rewritten_query,
      }])
    } catch (e) {
      setChatHistory(prev => [...prev, {
        role: "ai",
        content: "Something went wrong. Please try again.",
        sources: [],
      }])
    }
    setLoading(false)
  }

  // Called when a timestamp is clicked anywhere in the UI
  // Sets activeTime which the YouTube player listens to
  function handleTimestampClick(seconds) {
    setActiveTime(seconds)
  }

  function handleClearChat() {
    setChatHistory([])
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>YT<span>Chat</span></h1>
        <p>Ask anything about any YouTube video</p>
      </header>

      <main className="app-main">
        {/* Left panel — video + loader */}
        <div className="left-panel">
          <VideoLoader
            onLoad={handleLoadVideo}
            loading={loading}
            loadingMsg={loadingMsg}
          />

          {/* YouTube iframe player — shown once video is loaded */}
          {videoLoaded && (
            <div className="player-wrapper">
              {/* The YouTube iframe embed.
                  We use the YouTube IFrame API to control it via JS.
                  activeTime drives seeking when a timestamp is clicked. */}
              <YouTubePlayer
                videoId={videoId}
                activeTime={activeTime}
              />
            </div>
          )}
        </div>

        {/* Right panel — chat */}
        <div className="right-panel">
          {videoLoaded ? (
            <ChatBox
              chatHistory={chatHistory}
              onAsk={handleAsk}
              onClear={handleClearChat}
              onTimestampClick={handleTimestampClick}
              loading={loading}
              videoId={videoId}
            />
          ) : (
            <div className="empty-state">
              <p>Load a YouTube video to start chatting</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

// ── YouTube Player component ──────────────────────────────────────────────────
// This lives here because it's small and tightly coupled to App state.
// It uses the YouTube IFrame API to seek to a timestamp when activeTime changes.

import { useEffect, useRef } from "react"

function YouTubePlayer({ videoId, activeTime }) {
  const playerRef = useRef(null)   // useRef holds a reference to the YT player object
  const divRef    = useRef(null)   // reference to the DOM div where player mounts

  useEffect(() => {
    // Destroy existing player before creating a new one
    if (playerRef.current && playerRef.current.destroy) {
      playerRef.current.destroy()
      playerRef.current = null
    }

    function initPlayer() {
      playerRef.current = new window.YT.Player(divRef.current, {
        videoId,
        playerVars: { autoplay: 0, modestbranding: 1 },
      })
    }

    // Load the YouTube IFrame API script once
    if (!window.YT) {
      const tag = document.createElement("script")
      tag.src = "https://www.youtube.com/iframe_api"
      document.body.appendChild(tag)
      window.onYouTubeIframeAPIReady = initPlayer
    } else {
      // API already loaded — init directly
      initPlayer()
    }
  }, [videoId])   // re-run when videoId changes

  useEffect(() => {
    // When activeTime changes (timestamp clicked), seek the player
    if (playerRef.current && activeTime !== null) {
      playerRef.current.seekTo(activeTime, true)
      playerRef.current.playVideo()
    }
  }, [activeTime])   // re-run when activeTime changes

  return <div ref={divRef} className="yt-player" />
}
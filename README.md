# 🎥 RagTube — YouTube Video Q&A Assistant

**RagTube** is a Retrieval-Augmented Generation (RAG) based system that lets you **ask questions about any YouTube video**.  
It fetches the video transcript, splits it into chunks, generates embeddings, stores them in FAISS, and uses a local LLM (via Ollama) to answer user queries.

---

## 🚀 Features

- Fetches YouTube transcripts automatically (manual or auto captions)
- Cleans and chunks transcripts into meaningful sections
- Generates embeddings locally using Ollama
- Stores vectors in FAISS (local vector database)
- Retrieves the most relevant chunks for a given question
- Answers questions using a local LLM model (offline!)

---

## 🧠 Tech Stack

| Component | Technology |
|------------|-------------|
| **Backend** | FastAPI (Python) |
| **LLM Runtime** | Ollama |
| **Vector Database** | FAISS |
| **Embeddings** | `nomic-embed-text` (via Ollama) |
| **Language Model** | Default: `phi3` |
| **Transcript Fetching** | yt-dlp |
| **Language** | Python 3.10+ |

------------------------------------------
Steps to run the project-

🧩 1️⃣ Clone the project

Open PowerShell, Git Bash, or VS Code terminal, and run:

git clone https://github.com/kartikeyaswarup-m1/RagTube.git
cd RagTube/backend

🧩 2️⃣ Create and activate a virtual environment
🔹 On Windows:
python -m venv venv
venv\Scripts\activate


After this, your terminal should start with (venv) — this means it’s activated.

🧩 3️⃣ Install dependencies

Run:

pip install -r requirements.txt


If there’s no requirements.txt, use this instead:

pip install fastapi uvicorn yt-dlp requests ollama faiss-cpu numpy python-dotenv

🧩 4️⃣ Install and set up Ollama

Download Ollama from:
👉 https://ollama.com/download

After installation, open a new terminal and test:

ollama --version


Pull the models used in this project:

ollama pull phi3
ollama pull nomic-embed-text


⚠️ This may take a few minutes (models download once).

🧩 5️⃣ Check the .env file

In the backend folder, there’s a file named .env.
It already has all required settings.

Make sure it looks like this:

VECTORSTORE_DIR=./vectorstore

OLLAMA_MODEL=phi3
EMBED_MODEL=nomic-embed-text
OLLAMA_HOST=http://127.0.0.1:11434

BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000


🔁 If you want to use another model (like llama3), just change this line:

OLLAMA_MODEL=llama3


and make sure to pull it using ollama pull llama3.

🧩 6️⃣ Run the backend

From the project root folder (RagTube):

uvicorn backend.app.main:app --reload


If everything is okay, you’ll see:

INFO:     Uvicorn running on http://127.0.0.1:8000

🧩 7️⃣ Open the API Docs

Go to your browser and open:
👉 http://127.0.0.1:8000/docs

This page shows all available endpoints:

/ingest — to load a YouTube video transcript

/query — to ask questions about the video

🧩 8️⃣ Try it out!
🔹 Step 1 — Ingest a video

Click on /ingest

Click “Try it out”

Paste any YouTube link (with English subtitles)

Click Execute

Wait a few seconds ⏳
You’ll get something like:

{
  "video_url": "...",
  "status": "ingested",
  "chunks": 63
}


A folder named vectorstore will appear automatically — it stores your embeddings.

🔹 Step 2 — Ask a question

Click on /query

Click “Try it out”

In the question box, type something like:

What is this video about?


Click Execute

After a few seconds, you’ll see a meaningful answer from the local LLM 🎯

✅ Done!

You’ve now successfully:

Loaded a video

Built its embeddings

Queried it using RAG and a local model (no internet needed!)

🧠 Optional

If you want to stop the server:

Ctrl + C


If you want to change model:

Edit .env → OLLAMA_MODEL=llama3 (or any other model)

Pull the model using ollama pull llama3

Restart the backend.

----------------------------------------------------------------------



🏁 Future Scope
Add frontend chat interface

Multi-video ingestion

Video summarization endpoint

Cloud LLM integration for faster inference

🪄 Example Workflow
1️⃣ Run backend
2️⃣ In /docs, call /ingest with a YouTube URL
3️⃣ Once status = ingested, call /query with a question
4️⃣ Get the AI-generated answer! 🎯



---

## ✅ Next Step for You
1. Copy this full markdown text  
2. Open your repo’s `README.md` in VS Code or Notepad  
3. Replace everything inside it with this content  
4. Save the file  
5. Push it to GitHub:
   ```bash
   git add README.md
   git commit -m "Updated README with setup guide and model switch instructions"
   git push origin main

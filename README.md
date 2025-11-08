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

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/kartikeyaswarup-m1/RagTube.git
cd RagTube/backend
2️⃣ Create and Activate Virtual Environment
bash

python -m venv venv
venv\Scripts\activate
3️⃣ Install Dependencies
bash

pip install -r requirements.txt
(If there’s no requirements.txt, you can install manually)
pip install fastapi uvicorn yt-dlp requests ollama faiss-cpu numpy python-dotenv

4️⃣ Ensure Ollama is Running
Install Ollama from https://ollama.com/ and pull required models:

bash

ollama pull phi3
ollama pull nomic-embed-text
🔧 Configuration
All configuration values are stored in the .env file located in backend/.env.

Default:

bash

# ===== Backend Config =====
VECTORSTORE_DIR=./vectorstore

# ===== Ollama Config =====
OLLAMA_MODEL=phi3
EMBED_MODEL=nomic-embed-text
OLLAMA_HOST=http://127.0.0.1:11434

# ===== FastAPI Config =====
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
🔁 Switching to a Different Model
If you want to use a different model (for example, llama3 or gemma):

Pull the model in Ollama:

ollama pull llama3
Update this line in your .env file:

bash

OLLAMA_MODEL=llama3
That’s it!
The backend automatically reads the model name from the .env file —
you do not need to modify any Python code.

▶️ Running the Backend
Run the FastAPI server from the project root:

bash

cd C:\Users\HP\RagTube
uvicorn backend.app.main:app --reload
You’ll see:

arduino

INFO:     Uvicorn running on http://127.0.0.1:8000
Then open:
👉 http://127.0.0.1:8000/docs

🧩 API Endpoints
/ingest
Fetches transcript, chunks it, and builds FAISS vectorstore.

Query:

bash

GET /ingest?video_url=<YOUTUBE_URL>
Example:

bash

http://127.0.0.1:8000/ingest?video_url=https://youtu.be/RRVYpIET_RU
/query
Asks a question based on the ingested video.

Query:

bash

GET /query?question=<YOUR_QUESTION>
Example:

bash

http://127.0.0.1:8000/query?question=What is this video about?
📦 Output Files
After ingestion, you’ll see:

pgsql

backend/vectorstore/
 ├── faiss.index
 └── mapping.pkl
These files store embeddings for the ingested video transcript.



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



✨ Built with ❤️ using FastAPI, Ollama, and FAISS.

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

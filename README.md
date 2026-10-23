# Spotify Music Recommendation System

> 🌐 **Live Website:** [https://recommender-mini-proj.vercel.app](https://recommender-mini-proj.vercel.app)  
> *(Fully hosted & deployed on Vercel with zero local setup needed)*

An end-to-end Content-Based Music Recommendation Engine operating on a comprehensive Spotify dataset of **170,653 tracks** (1921–2020). Built with **StandardScaler Normalization**, **10-Component PCA Latent Space**, **K-Means Clustering (k=15)**, and **Cosine Nearest Neighbors**, served through an Apple-inspired minimalist web application.

---

## ⚡ 1-Step Quick Start on a New Laptop

Simply clone and run the automated launcher script. It will **automatically create the virtual environment, install all dependencies, launch the server, and open your browser**:

### On Linux / macOS:
```bash
git clone https://github.com/Neeraj704/Recommender-Systems-Mini-Project.git
cd Recommender-Systems-Mini-Project
./run.sh
```

### On Windows:
```cmd
git clone https://github.com/Neeraj704/Recommender-Systems-Mini-Project.git
cd Recommender-Systems-Mini-Project
run.bat
```
*(Or simply open the cloned folder in Windows Explorer and double-click `run.bat`!)*

---

### Manual Setup (Alternative)

If you prefer to configure the virtual environment manually:

1. **Create & activate venv:**
   - Linux/macOS: `python3 -m venv .venv && source .venv/bin/activate`
   - Windows: `python -m venv .venv && .\.venv\Scripts\activate`
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Start server:** `python server.py`
4. **Open in browser:** `http://localhost:8000`

---

## 🎯 What's Inside

1. **Interactive Recommendation Playground**:
   - **Single Track Similarity**: Search 170k+ tracks with live debounced autocomplete.
   - **Multi-Seed Blend**: Combine 2 to 5 songs into a weighted playlist composite vector (`[0.50, 0.25, 0.15, 0.10, 0.05]`).
   - **Acoustic Mood Sliders**: Dial custom Danceability, Energy, Valence, Acousticness, Tempo, etc.
   - **Playable 30s Audio Previews**: Play 30-second audio previews directly in the browser.
2. **Audio Feature Radar Comparator**:
   - Side-by-side radar polygon comparison between seed track and recommendation.
   - Exact mathematical divergence ($\Delta$) metrics table.
3. **Machine Learning Architecture**:
   - 6-stage pipeline: Ingestion → StandardScaler → 10-D PCA → K-Means (15 clusters) → Cosine NearestNeighbors (sub-15ms) → Hybrid Re-ranking (+1.0 artist, +0.5 genre).
4. **Empirical Proof Case Study**:
   - Demonstrates why querying Ennio Morricone's *"Friends"* recommends John Williams and Nobuo Uematsu instead of text matches.
5. **Professor & Viva Defense Master Guide**:
   - Top 8 academic questions with model answers (Cold-start, PCA variance, RAM complexity, evaluation metrics).
6. **System Specifications Card**:
   - Quick reference stats for presentations and viva exams.

---

## 📂 Project Structure

```text
├── datasets/
│   ├── data.csv              # Primary 170k track dataset
│   ├── Music.csv             # Track artworks & 30s audio preview URLs
│   ├── data_by_genres.csv    # Genre-level audio aggregates
│   └── data_by_year.csv      # Historical audio trends (1921-2020)
├── static/
│   ├── index.html            # Minimalist Apple-inspired UI
│   ├── styles.css            # Dark mode token-based design system
│   ├── app.js                # Frontend controller & Chart.js radar
│   └── assets/               # Technical blueprint & radar diagrams
├── server.py                 # Starlette + Uvicorn high-throughput backend
├── run.sh                    # 1-click Linux/macOS launcher
├── requirements.txt          # Python dependencies
├── app.py                    # Legacy Streamlit alternative
└── README.md                 # Project documentation
```

---

## 🧪 Running the Legacy Streamlit App (Optional)

If you wish to run the legacy Streamlit interface instead of the modern web app:
```bash
streamlit run app.py
```
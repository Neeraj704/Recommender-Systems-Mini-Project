import os
import time
import re
import ast
import json
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors

from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

print("🎵 Initializing Spotify Music Recommendation Engine...")
start_time = time.time()

# ======= Paths =======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ======= Load Datasets =======
data_csv = os.path.join(DATASETS_DIR, "data.csv")
music_csv = os.path.join(DATASETS_DIR, "Music.csv")

print("📂 Loading data.csv...")
df = pd.read_csv(data_csv, on_bad_lines='skip', engine='python')

# Standardize columns
column_mapping = {
    'title': 'name', 'track_name': 'name',
    'artist': 'artists', 'spotify_id': 'id',
    'img': 'image_url', 'release_date': 'year'
}
for old_col, new_col in column_mapping.items():
    if old_col in df.columns and new_col not in df.columns:
        df[new_col] = df[old_col]

# Handle 'year'
if 'release_date' in df.columns and ('year' not in df.columns or df['year'].isnull().any()):
    try:
        extracted_year = pd.to_datetime(df['release_date'], errors='coerce').dt.year
        df['year'] = df['year'].fillna(extracted_year)
    except Exception:
        pass

if 'year' not in df.columns:
    df['year'] = 2000
df['year'] = pd.to_numeric(df['year'], errors='coerce').fillna(2000).astype(int)

if 'name' not in df.columns:
    df['name'] = [f"Track {i}" for i in range(len(df))]
df['name'] = df['name'].fillna("Unknown Track").astype(str)

if 'id' not in df.columns:
    df['id'] = [f"track_{i}" for i in range(len(df))]
df['id'] = df['id'].fillna("").astype(str)

if 'popularity' not in df.columns:
    df['popularity'] = 50
df['popularity'] = pd.to_numeric(df['popularity'], errors='coerce').fillna(50).astype(int)

# Clean artists string: "['Queen']" -> "Queen"
def clean_artist_str(val):
    if not isinstance(val, str):
        return "Unknown Artist"
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return ", ".join(str(p) for p in parsed)
        except Exception:
            pass
        return val.strip("[]'\" ")
    return val

df['clean_artists'] = df['artists'].apply(clean_artist_str)

# Features definition
FEATURE_COLS = [
    'acousticness', 'danceability', 'energy', 'instrumentalness',
    'liveness', 'loudness', 'speechiness', 'tempo', 'valence', 'year'
]
RADAR_FEATURES = [
    'acousticness', 'danceability', 'energy', 'instrumentalness',
    'liveness', 'speechiness', 'valence'
]

# Keep only rows with valid feature values
df.dropna(subset=FEATURE_COLS, inplace=True)
df.reset_index(drop=True, inplace=True)

# Build Artwork and Preview URL mapping from Music.csv
name_to_img = {}
id_to_img = {}
name_to_preview = {}
id_to_preview = {}

if os.path.exists(music_csv):
    print("🎨 Loading Music.csv metadata (artwork & 30s previews)...")
    try:
        music_df = pd.read_csv(music_csv, on_bad_lines='skip', engine='python')
        music_df.columns = [c.strip().lower().replace(' ', '_') for c in music_df.columns]
        m_name_col = 'song' if 'song' in music_df.columns else 'name'
        
        for _, row in music_df.iterrows():
            s_name = str(row.get(m_name_col, '')).strip().lower()
            s_id = str(row.get('spotify_id', '')).strip()
            s_img = row.get('img', None)
            s_prev = row.get('preview', None)

            if pd.notnull(s_img) and isinstance(s_img, str) and s_img.startswith('http'):
                if s_id:
                    id_to_img[s_id] = s_img
                if s_name:
                    name_to_img[s_name] = s_img

            if pd.notnull(s_prev) and isinstance(s_prev, str) and s_prev.startswith('http'):
                if s_id:
                    id_to_preview[s_id] = s_prev
                if s_name:
                    name_to_preview[s_name] = s_prev
        print(f"✅ Indexed {len(id_to_img)} images and {len(id_to_preview)} audio previews!")
    except Exception as e:
        print(f"⚠️ Warning loading Music.csv: {e}")

# ======= Machine Learning Pipeline =======
print("⚙️ Normalizing features with StandardScaler...")
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df[FEATURE_COLS])

print("📉 Performing PCA dimensionality reduction (10 latent components)...")
pca = PCA(n_components=10, random_state=42)
data_pca = pca.fit_transform(df_scaled)

print("🎯 Clustering with K-Means (k=15 acoustic clusters)...")
kmeans = KMeans(n_clusters=15, random_state=42, n_init='auto')
clusters = kmeans.fit_predict(data_pca)
df['cluster'] = clusters

# Profile clusters for presentation
CLUSTER_NAMES = {
    0: "Acoustic & Folk Ballads",
    1: "High-Energy Dance Pop",
    2: "Symphonic & Classical Instrumental",
    3: "Vintage Golden Age (1920s–1950s)",
    4: "Electronic, Synth & Ambient",
    5: "Classic Rock & Energetic Anthems",
    6: "Moody & Melancholic Indie",
    7: "Upbeat Groovy Funk & Disco",
    8: "Spoken Word, Poetry & Audio Drama",
    9: "Live Stage & Concert Recordings",
    10: "R&B, Soul & Smooth Vocals",
    11: "Modern Chart-Topping Pop",
    12: "Cinematic Soundtracks & Orchestral",
    13: "Heavy Rock, Grunge & Metal",
    14: "Warm Acoustic Singer-Songwriter"
}

print("⚡ Fitting NearestNeighbors Cosine index...")
neigh = NearestNeighbors(n_neighbors=50, metric='cosine', algorithm='auto')
neigh.fit(data_pca)

print(f"🚀 Model Ready! Processed {len(df):,} songs in {time.time()-start_time:.2f}s.")

# Quick lookup indexes
name_lower_series = df['name'].str.lower()
clean_artist_lower_series = df['clean_artists'].str.lower()
id_to_idx = {sid: i for i, sid in enumerate(df['id']) if sid}

# Regional / Hindi detection helper
HINDI_GENRES = ['hindi', 'bollywood', 'indian', 'punjabi', 'arijit', 'lata', 'kishore', 'mohammed rafi']
def is_hindi_song(row):
    genre = str(row.get('genre', '')).lower()
    name = str(row.get('name', '')).lower()
    artists = str(row.get('clean_artists', '')).lower()
    return any(g in genre or g in name or g in artists for g in HINDI_GENRES)

def get_track_image(row):
    # Try ID first, then name
    sid = str(row.get('id', '')).strip()
    if sid in id_to_img:
        return id_to_img[sid]
    sname = str(row.get('name', '')).strip().lower()
    if sname in name_to_img:
        return name_to_img[sname]
    return None

def get_track_preview(row):
    sid = str(row.get('id', '')).strip()
    if sid in id_to_preview:
        return id_to_preview[sid]
    sname = str(row.get('name', '')).strip().lower()
    if sname in name_to_preview:
        return name_to_preview[sname]
    return None

def format_track_dict(row, dist=None, bonus=0.0):
    track_id = str(row['id'])
    cluster_id = int(row['cluster'])
    sim_score = max(0.0, round((1.0 - (dist if dist is not None else 0.0)) * 100, 1))
    
    features_dict = {
        'danceability': round(float(row['danceability']), 3),
        'energy': round(float(row['energy']), 3),
        'valence': round(float(row['valence']), 3),
        'acousticness': round(float(row['acousticness']), 3),
        'instrumentalness': round(float(row['instrumentalness']), 3),
        'liveness': round(float(row['liveness']), 3),
        'speechiness': round(float(row['speechiness']), 3),
        'loudness': round(float(row['loudness']), 1),
        'tempo': round(float(row['tempo']), 1),
        'year': int(row['year'])
    }

    return {
        'id': track_id,
        'title': str(row['name']),
        'artist': str(row['clean_artists']),
        'year': int(row['year']),
        'popularity': int(row['popularity']),
        'cluster': cluster_id,
        'cluster_name': CLUSTER_NAMES.get(cluster_id, f"Cluster {cluster_id}"),
        'distance': round(float(dist), 4) if dist is not None else None,
        'similarity': sim_score,
        'bonus': round(float(bonus), 2),
        'image_url': get_track_image(row),
        'preview_url': get_track_preview(row),
        'spotify_url': f"https://open.spotify.com/track/{track_id}" if track_id and not track_id.startswith('track_') else None,
        'features': features_dict
    }

# ======= API Handlers =======

async def api_stats(request):
    return JSONResponse({
        'total_tracks': len(df),
        'total_artists': df['clean_artists'].nunique(),
        'year_range': [int(df['year'].min()), int(df['year'].max())],
        'features': FEATURE_COLS,
        'radar_features': RADAR_FEATURES,
        'pca_components': 10,
        'kmeans_clusters': 15,
        'cluster_names': CLUSTER_NAMES,
        'engine': 'StandardScaler + PCA(10) + KMeans(15) + Cosine NearestNeighbors'
    })

async def api_quick_picks(request):
    """Curated hit tracks for instant 1-click teacher demonstration"""
    picks = [
        {"title": "Bohemian Rhapsody", "artist": "Queen", "genre": "Classic Rock / Opera", "year": 1975},
        {"title": "Blinding Lights", "artist": "The Weeknd", "genre": "Synthwave / Pop", "year": 2020},
        {"title": "Friends", "artist": "Ennio Morricone", "genre": "Film Score / Acoustic (Report Proof)", "year": 1984},
        {"title": "Tum Hi Ho", "artist": "Arijit Singh", "genre": "Bollywood / Romantic", "year": 2013},
        {"title": "Hotel California", "artist": "Eagles", "genre": "Rock / Classic", "year": 1976},
        {"title": "Bad Guy", "artist": "Billie Eilish", "genre": "Electropop / Bass", "year": 2019},
        {"title": "One More Time", "artist": "Daft Punk", "genre": "Electronic / French House", "year": 2000},
        {"title": "Smells Like Teen Spirit", "artist": "Nirvana", "genre": "Grunge / Alternative", "year": 1991},
        {"title": "Fly Me to the Moon", "artist": "Frank Sinatra", "genre": "Jazz / Vocal Standards", "year": 1964},
        {"title": "Clair de Lune", "artist": "Claude Debussy", "genre": "Classical / Piano Solo", "year": 1921}
    ]
    
    resolved_picks = []
    for p in picks:
        # Search in df
        title_q = p['title'].lower()
        artist_q = p['artist'].lower()
        mask = name_lower_series.str.contains(title_q, regex=False, na=False) & \
               clean_artist_lower_series.str.contains(artist_q, regex=False, na=False)
        m = df[mask]
        if m.empty:
            m = df[name_lower_series.str.contains(title_q, regex=False, na=False)]
        if not m.empty:
            # pick highest popularity match
            best_row = m.sort_values('popularity', ascending=False).iloc[0]
            track_dict = format_track_dict(best_row)
            track_dict['display_genre'] = p['genre']
            resolved_picks.append(track_dict)
    
    return JSONResponse({'quick_picks': resolved_picks})

async def api_search(request):
    q = request.query_params.get('q', '').strip()
    if not q or len(q) < 2:
        return JSONResponse({'results': []})
    
    q_lower = q.lower()
    # Search by title first
    mask_title = name_lower_series.str.contains(q_lower, regex=False, na=False)
    mask_artist = clean_artist_lower_series.str.contains(q_lower, regex=False, na=False)
    matches = df[mask_title | mask_artist]
    
    if matches.empty:
        return JSONResponse({'results': []})
    
    # Sort: title matches starting with query first, then popularity
    matches = matches.copy()
    matches['exact_start'] = matches['name'].str.lower().str.startswith(q_lower)
    matches.sort_values(by=['exact_start', 'popularity'], ascending=[False, False], inplace=True)
    
    # Deduplicate by lower name and artist
    results = []
    seen = set()
    for _, row in matches.head(30).iterrows():
        key = (str(row['name']).strip().lower(), str(row['clean_artists']).strip().lower())
        if key in seen:
            continue
        seen.add(key)
        results.append(format_track_dict(row))
        if len(results) >= 12:
            break
            
    return JSONResponse({'results': results, 'total_matches': len(matches)})

async def api_recommend(request):
    t_start = time.time()
    try:
        body = await request.json()
    except Exception:
        body = {}
        
    mode = body.get('mode', 'single') # 'single', 'multi', 'mood'
    limit = min(int(body.get('limit', 10)), 30)
    apply_rerank = bool(body.get('apply_rerank', True))
    filter_hindi = bool(body.get('filter_hindi', False))

    seed_tracks_info = []
    query_vector = None

    if mode == 'single':
        song_query = body.get('song_query', '').strip()
        song_id = body.get('song_id', '').strip()
        
        target_idx = None
        if song_id and song_id in id_to_idx:
            target_idx = id_to_idx[song_id]
        elif song_query:
            q_clean = song_query.strip().lower()
            # 1. Exact title match
            matches = df[name_lower_series == q_clean]
            # 2. Substring title match
            if matches.empty:
                matches = df[name_lower_series.str.contains(q_clean, regex=False, na=False)]
            # 3. Combined title + artist match
            if matches.empty:
                combined_series = name_lower_series + " " + clean_artist_lower_series
                matches = df[combined_series.str.contains(q_clean, regex=False, na=False)]
            # 4. Multi-token match (all words present)
            if matches.empty:
                tokens = [t for t in q_clean.split() if len(t) > 1]
                if tokens:
                    combined_series = name_lower_series + " " + clean_artist_lower_series
                    cond = combined_series.str.contains(tokens[0], regex=False, na=False)
                    for token in tokens[1:]:
                        cond = cond & combined_series.str.contains(token, regex=False, na=False)
                    matches = df[cond]
            
            if not matches.empty:
                # pick highest popularity match
                target_idx = matches.sort_values('popularity', ascending=False).index[0]
                
        if target_idx is None:
            # Fallback to popular songs
            popular_df = df.sort_values('popularity', ascending=False).head(limit)
            recs = [format_track_dict(r) for _, r in popular_df.iterrows()]
            return JSONResponse({
                'seed': None,
                'recommendations': recs,
                'mode': 'fallback_popular',
                'latency_ms': round((time.time() - t_start) * 1000, 2)
            })
            
        seed_row = df.iloc[target_idx]
        seed_tracks_info.append(format_track_dict(seed_row))
        query_vector = data_pca[target_idx].reshape(1, -1)
        seed_artist = seed_row['clean_artists']
        seed_is_hindi = is_hindi_song(seed_row)
        seed_indices = {target_idx}

    elif mode == 'multi':
        seed_ids = body.get('seed_ids', [])
        seed_titles = body.get('seed_titles', [])
        weights = body.get('weights', [0.5, 0.25, 0.15, 0.10, 0.05])
        
        target_indices = []
        for sid in seed_ids:
            if sid in id_to_idx:
                target_indices.append(id_to_idx[sid])
                
        if not target_indices and seed_titles:
            for title in seed_titles[:5]:
                m = df[name_lower_series.str.contains(title.lower(), regex=False, na=False)]
                if not m.empty:
                    target_indices.append(m.sort_values('popularity', ascending=False).index[0])
                    
        if not target_indices:
            popular_df = df.sort_values('popularity', ascending=False).head(limit)
            return JSONResponse({
                'seed': None,
                'recommendations': [format_track_dict(r) for _, r in popular_df.iterrows()],
                'mode': 'fallback_popular',
                'latency_ms': round((time.time() - t_start) * 1000, 2)
            })
            
        # Linear blend in PCA space with weights
        blended_vec = np.zeros(data_pca.shape[1])
        w_sum = 0.0
        seed_indices = set(target_indices)
        
        for i, idx in enumerate(target_indices[:5]):
            w = weights[i] if i < len(weights) else 0.1
            blended_vec += w * data_pca[idx]
            w_sum += w
            seed_tracks_info.append(format_track_dict(df.iloc[idx]))
            
        if w_sum > 0:
            blended_vec /= w_sum
        query_vector = blended_vec.reshape(1, -1)
        seed_artist = seed_tracks_info[0]['artist']
        seed_is_hindi = any(is_hindi_song(df.iloc[i]) for i in target_indices)

    elif mode == 'mood':
        # Custom user-dialed acoustic features
        mood_vals = body.get('mood_features', {})
        # default middle values
        sample_vec = []
        for feat in FEATURE_COLS:
            if feat in mood_vals:
                sample_vec.append(float(mood_vals[feat]))
            elif feat == 'year':
                sample_vec.append(float(mood_vals.get('year', 2010)))
            elif feat == 'loudness':
                sample_vec.append(float(mood_vals.get('loudness', -8.0)))
            elif feat == 'tempo':
                sample_vec.append(float(mood_vals.get('tempo', 120.0)))
            else:
                sample_vec.append(float(mood_vals.get(feat, 0.5)))
                
        raw_arr = np.array(sample_vec).reshape(1, -1)
        scaled_arr = scaler.transform(raw_arr)
        query_vector = pca.transform(scaled_arr)
        seed_artist = ""
        seed_is_hindi = filter_hindi
        seed_indices = set()
        seed_tracks_info.append({
            'title': "Custom Acoustic Fingerprint",
            'artist': "User Mood Synthesis",
            'year': int(mood_vals.get('year', 2020)),
            'cluster_name': "Bespoke Latent Vector",
            'features': {f: round(val, 3) for f, val in zip(FEATURE_COLS, sample_vec)}
        })

    # Retrieve nearest neighbors
    num_to_fetch = min(max(limit * 8, 80), len(df) - 1)
    dists, indices = neigh.kneighbors(query_vector, n_neighbors=num_to_fetch)
    dists = dists.flatten()
    indices = indices.flatten()

    candidates = []
    seen_songs = set()

    for d, idx in zip(dists, indices):
        if idx in seed_indices:
            continue
        row = df.iloc[idx]
        norm_title = str(row['name']).strip().lower()
        norm_artist = str(row['clean_artists']).strip().lower()
        # Avoid near duplicate song releases in results
        dedup_key = (norm_title[:30], norm_artist[:20])
        if dedup_key in seen_songs:
            continue
        seen_songs.add(dedup_key)

        bonus = 0.0
        if apply_rerank and mode != 'mood':
            # Artist loyalty bonus (+1.0)
            if seed_artist and seed_artist.lower() in norm_artist:
                bonus += 1.0
            # Cultural / Language alignment (+0.5)
            if is_hindi_song(row) == seed_is_hindi:
                bonus += 0.5

        candidates.append((bonus, d, row))

    # Re-rank: highest bonus first, then lowest cosine distance
    if apply_rerank:
        candidates.sort(key=lambda item: (-item[0], item[1]))
    else:
        candidates.sort(key=lambda item: item[1])

    # Language filter if requested
    final_candidates = []
    if filter_hindi:
        for bonus, d, row in candidates:
            if is_hindi_song(row):
                final_candidates.append(format_track_dict(row, dist=d, bonus=bonus))
                if len(final_candidates) >= limit:
                    break
        # Supplement if fewer than limit
        if len(final_candidates) < limit:
            for bonus, d, row in candidates:
                cand_dict = format_track_dict(row, dist=d, bonus=bonus)
                if cand_dict not in final_candidates:
                    final_candidates.append(cand_dict)
                    if len(final_candidates) >= limit:
                        break
    else:
        for bonus, d, row in candidates[:limit]:
            final_candidates.append(format_track_dict(row, dist=d, bonus=bonus))

    latency_ms = round((time.time() - t_start) * 1000, 2)

    return JSONResponse({
        'mode': mode,
        'seed': seed_tracks_info[0] if len(seed_tracks_info) == 1 else seed_tracks_info,
        'recommendations': final_candidates,
        'total_candidates_analyzed': len(candidates),
        'latency_ms': latency_ms
    })

async def api_clusters(request):
    """Summaries of all 15 clusters with centroids and sample tracks"""
    cluster_list = []
    for c_id in range(15):
        c_subset = df[df['cluster'] == c_id]
        avg_feats = c_subset[RADAR_FEATURES].mean().to_dict()
        top_artists = c_subset['clean_artists'].value_counts().head(5).index.tolist()
        sample_tracks = c_subset.sort_values('popularity', ascending=False).head(3)['name'].tolist()
        
        cluster_list.append({
            'cluster_id': c_id,
            'name': CLUSTER_NAMES.get(c_id, f"Cluster {c_id}"),
            'track_count': len(c_subset),
            'avg_year': int(c_subset['year'].mean()),
            'avg_tempo': round(float(c_subset['tempo'].mean()), 1),
            'avg_features': {k: round(float(v), 3) for k, v in avg_feats.items()},
            'top_artists': top_artists,
            'sample_tracks': sample_tracks
        })
    return JSONResponse({'clusters': cluster_list})

async def serve_index(request):
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "Frontend not yet generated. Please build index.html in static/"})

# ======= Starlette App & Routes =======
routes = [
    Route("/api/stats", api_stats, methods=["GET"]),
    Route("/api/quick-picks", api_quick_picks, methods=["GET"]),
    Route("/api/search", api_search, methods=["GET"]),
    Route("/api/recommend", api_recommend, methods=["POST"]),
    Route("/api/clusters", api_clusters, methods=["GET"]),
    Route("/", serve_index, methods=["GET"]),
    Mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(debug=True, routes=routes, middleware=middleware)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n✨ Server running at: http://localhost:{port}")
    print(f"📖 Open in your browser to view the interactive presentation & demo.\n")
    uvicorn.run(app, host="0.0.0.0", port=port)

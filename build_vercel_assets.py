import os
import time
import json
import gzip
import ast
import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

print("⚙️ Precomputing optimized artifacts for Vercel deployment...")
t0 = time.time()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

data_csv = os.path.join(DATASETS_DIR, "data.csv")
music_csv = os.path.join(DATASETS_DIR, "Music.csv")

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

FEATURE_COLS = [
    'acousticness', 'danceability', 'energy', 'instrumentalness',
    'liveness', 'loudness', 'speechiness', 'tempo', 'valence', 'year'
]

df.dropna(subset=FEATURE_COLS, inplace=True)
df.reset_index(drop=True, inplace=True)

print("📐 Fitting StandardScaler & PCA(10)...")
scaler = StandardScaler()
scaled = scaler.fit_transform(df[FEATURE_COLS])

pca = PCA(n_components=10, random_state=42)
data_pca = pca.fit_transform(scaled).astype(np.float32)

kmeans = KMeans(n_clusters=15, random_state=42, n_init='auto')
clusters = kmeans.fit_predict(data_pca)
df['cluster'] = clusters.astype(np.int8)

# Save numpy array
pca_path = os.path.join(DATA_DIR, "data_pca.npy")
np.save(pca_path, data_pca)
print(f"✅ Saved data_pca.npy ({os.path.getsize(pca_path)/(1024*1024):.2f} MB)")

# Save scaler and pca
with open(os.path.join(DATA_DIR, "scaler.pkl"), "wb") as f:
    pickle.dump(scaler, f)
with open(os.path.join(DATA_DIR, "pca.pkl"), "wb") as f:
    pickle.dump(pca, f)

# Build compact artwork and preview mapping
id_to_img = {}
name_to_img = {}
id_to_prev = {}
name_to_prev = {}

if os.path.exists(music_csv):
    print("🎨 Processing Music.csv...")
    m_df = pd.read_csv(music_csv, on_bad_lines='skip', engine='python')
    m_df.columns = [c.strip().lower().replace(' ', '_') for c in m_df.columns]
    m_name = 'song' if 'song' in m_df.columns else 'name'
    for _, r in m_df.iterrows():
        sid = str(r.get('spotify_id', '')).strip()
        sname = str(r.get(m_name, '')).strip().lower()
        img = r.get('img', None)
        prev = r.get('preview', None)
        if pd.notnull(img) and isinstance(img, str) and img.startswith('http'):
            if sid: id_to_img[sid] = img
            if sname and sname not in name_to_img: name_to_img[sname] = img
        if pd.notnull(prev) and isinstance(prev, str) and prev.startswith('http'):
            if sid: id_to_prev[sid] = prev
            if sname and sname not in name_to_prev: name_to_prev[sname] = prev

metadata_file = os.path.join(DATA_DIR, "metadata.json.gz")
with gzip.open(metadata_file, "wt", encoding="utf-8") as f:
    json.dump({
        'id_to_img': id_to_img,
        'name_to_img': name_to_img,
        'id_to_prev': id_to_prev,
        'name_to_prev': name_to_prev
    }, f)
print(f"✅ Saved metadata.json.gz ({os.path.getsize(metadata_file)/(1024*1024):.2f} MB)")

# Save compact tracks dataframe (using parquet for extreme compression and speed)
keep_cols = list(dict.fromkeys(['name', 'clean_artists', 'year', 'popularity', 'id', 'cluster'] + FEATURE_COLS))
tracks_df = df[keep_cols].copy()
tracks_parquet = os.path.join(DATA_DIR, "tracks.parquet")
tracks_df.to_parquet(tracks_parquet, index=False, compression='snappy')
print(f"✅ Saved tracks.parquet ({os.path.getsize(tracks_parquet)/(1024*1024):.2f} MB)")

print(f"\n✨ All Vercel artifacts ready in {time.time()-t0:.2f}s!")

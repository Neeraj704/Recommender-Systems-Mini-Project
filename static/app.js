/**
 * Spotify Music Recommender System - Minimalist Apple-Inspired Controller
 * Clean, restrained interaction logic with zero gratuitous animations or emoji clutter.
 */

// ======= Global State =======
const state = {
  currentMode: 'single', // 'single', 'multi', 'mood'
  selectedSeed: null,
  selectedRecForComparison: null,
  multiSeeds: [],
  currentAudio: null,
  currentPlayingId: null,
  radarChart: null,
  allClusters: [],
  quickPicks: []
};

// ======= DOM Elements =======
const searchInput = document.getElementById('searchInput');
const searchDropdown = document.getElementById('searchDropdown');
const btnGetRecs = document.getElementById('btnGetRecs');
const recLimitSlider = document.getElementById('recLimitSlider');
const recLimitVal = document.getElementById('recLimitVal');
const toggleRerank = document.getElementById('toggleRerank');
const toggleHindi = document.getElementById('toggleHindi');
const quickPicksContainer = document.getElementById('quickPicksContainer');
const recommendationsContainer = document.getElementById('recommendationsContainer');
const seedShowcaseContainer = document.getElementById('seedShowcaseContainer');
const metaBanner = document.getElementById('metaBanner');
const multiSeedTray = document.getElementById('multiSeedTray');
const multiSeedList = document.getElementById('multiSeedList');
const moodSlidersGrid = document.getElementById('moodSlidersGrid');

// ======= Initialize on DOM Load =======
document.addEventListener('DOMContentLoaded', () => {
  initStats();
  initQuickPicks();
  initSearchAutocomplete();
  initModeTabs();
  initSliders();
  initVivaAccordion();
  initClusters();

  // Initial demo recommendation with Queen - Bohemian Rhapsody
  setTimeout(() => {
    runRecommendation({
      mode: 'single',
      song_query: 'Bohemian Rhapsody'
    });
  }, 300);
});

// ======= API Initializers =======

async function initStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    document.getElementById('statTotalTracks').textContent = data.total_tracks.toLocaleString();
    document.getElementById('statArtists').textContent = data.total_artists.toLocaleString();
    document.getElementById('statYears').textContent = `${data.year_range[0]}–${data.year_range[1]}`;
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

async function initQuickPicks() {
  try {
    const res = await fetch('/api/quick-picks');
    const data = await res.json();
    state.quickPicks = data.quick_picks || [];
    renderQuickPicks();
  } catch (err) {
    console.error('Error fetching quick picks:', err);
  }
}

function renderQuickPicks() {
  if (!quickPicksContainer) return;
  quickPicksContainer.innerHTML = '';
  
  state.quickPicks.forEach(track => {
    const pill = document.createElement('button');
    pill.className = 'minimal-pill';
    pill.innerHTML = `<strong>${escapeHtml(track.title)}</strong> &bull; ${escapeHtml(track.artist)}`;
    pill.addEventListener('click', () => {
      selectSeedTrack(track);
      if (searchInput) {
        searchInput.value = `${track.title} - ${track.artist}`;
      }
      runRecommendation({
        mode: 'single',
        song_id: track.id,
        song_query: track.title
      });
      showToast(`Selected "${track.title}" by ${track.artist}`);
    });
    quickPicksContainer.appendChild(pill);
  });
}

async function initClusters() {
  try {
    const res = await fetch('/api/clusters');
    const data = await res.json();
    state.allClusters = data.clusters || [];
  } catch (err) {
    console.error('Error fetching clusters:', err);
  }
}

// ======= Segmented Mode Tabs =======

function initModeTabs() {
  const modeButtons = document.querySelectorAll('.segment-btn, .mode-btn');
  modeButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      modeButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.dataset.mode;
      state.currentMode = mode;

      const searchWrapper = searchInput.closest('.search-input-wrapper, .search-wrapper');

      if (mode === 'single') {
        if (searchWrapper) searchWrapper.style.display = 'block';
        multiSeedTray.classList.remove('active');
        moodSlidersGrid.classList.remove('active');
        searchInput.placeholder = "Search by title or artist (e.g. Bohemian Rhapsody, Blinding Lights, Tum Hi Ho)...";
      } else if (mode === 'multi') {
        if (searchWrapper) searchWrapper.style.display = 'block';
        multiSeedTray.classList.add('active');
        moodSlidersGrid.classList.remove('active');
        searchInput.placeholder = "Search and select up to 5 tracks to blend...";
        renderMultiSeedTray();
      } else if (mode === 'mood') {
        if (searchWrapper) searchWrapper.style.display = 'none';
        multiSeedTray.classList.remove('active');
        moodSlidersGrid.classList.add('active');
      }
    });
  });

  if (recLimitSlider && recLimitVal) {
    recLimitSlider.addEventListener('input', () => {
      recLimitVal.textContent = recLimitSlider.value;
    });
  }

  if (btnGetRecs) {
    btnGetRecs.addEventListener('click', () => {
      handleGetRecommendations();
    });
  }
}

function initSliders() {
  const moodInputs = document.querySelectorAll('.slider-group input[type="range"], .mood-item input[type="range"]');
  moodInputs.forEach(input => {
    input.addEventListener('input', () => {
      const parent = input.closest('.slider-group, .mood-item');
      const valSpan = parent ? parent.querySelector('.val') : null;
      if (valSpan) {
        if (input.name === 'tempo') {
          valSpan.textContent = `${input.value} BPM`;
        } else if (input.name === 'loudness') {
          valSpan.textContent = `${input.value} dB`;
        } else if (input.name === 'year') {
          valSpan.textContent = input.value;
        } else {
          valSpan.textContent = parseFloat(input.value).toFixed(2);
        }
      }
    });
  });
}

// ======= Search Autocomplete =======

let searchDebounceTimer = null;

function initSearchAutocomplete() {
  if (!searchInput) return;

  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim();
    clearTimeout(searchDebounceTimer);
    if (q.length < 2) {
      searchDropdown.style.display = 'none';
      return;
    }
    searchDebounceTimer = setTimeout(() => {
      performSearch(q);
    }, 200);
  });

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
      searchDropdown.style.display = 'none';
    }
  });

  searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      searchDropdown.style.display = 'none';
      handleGetRecommendations();
    }
  });
}

async function performSearch(query) {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    renderSearchDropdown(data.results || []);
  } catch (err) {
    console.error('Search error:', err);
  }
}

function renderSearchDropdown(items) {
  if (!searchDropdown) return;
  searchDropdown.innerHTML = '';
  if (items.length === 0) {
    searchDropdown.innerHTML = `<div style="padding:14px;color:var(--text-3);font-size:0.85rem;text-align:center;">No matching catalog items.</div>`;
    searchDropdown.style.display = 'block';
    return;
  }

  items.forEach(track => {
    const row = document.createElement('div');
    row.className = 'search-row';
    const imgHtml = track.image_url 
      ? `<img src="${track.image_url}" class="search-thumb" alt="Artwork">`
      : `<div class="search-thumb" style="display:flex;align-items:center;justify-content:center;color:var(--text-3);font-size:0.75rem;">SONG</div>`;
      
    row.innerHTML = `
      ${imgHtml}
      <div class="search-text">
        <div class="search-track-title">${escapeHtml(track.title)}</div>
        <div class="search-track-sub">${escapeHtml(track.artist)} &bull; ${track.year}</div>
      </div>
      <div class="search-cluster-pill">${escapeHtml(track.cluster_name)}</div>
    `;

    row.addEventListener('click', () => {
      searchDropdown.style.display = 'none';
      if (state.currentMode === 'multi') {
        addMultiSeedTrack(track);
      } else {
        searchInput.value = `${track.title} - ${track.artist}`;
        selectSeedTrack(track);
        runRecommendation({
          mode: 'single',
          song_id: track.id,
          song_query: track.title
        });
      }
    });

    searchDropdown.appendChild(row);
  });

  searchDropdown.style.display = 'block';
}

function selectSeedTrack(track) {
  state.selectedSeed = track;
}

// ======= Multi-Seed Tray =======

function addMultiSeedTrack(track) {
  if (state.multiSeeds.some(s => s.id === track.id)) {
    showToast(`"${track.title}" is already in blend.`);
    return;
  }
  if (state.multiSeeds.length >= 5) {
    showToast(`Maximum 5 seed tracks allowed.`);
    return;
  }
  state.multiSeeds.push(track);
  renderMultiSeedTray();
  showToast(`Added "${track.title}" (${state.multiSeeds.length}/5)`);
}

function removeMultiSeedTrack(index) {
  state.multiSeeds.splice(index, 1);
  renderMultiSeedTray();
}

function renderMultiSeedTray() {
  if (!multiSeedList) return;
  multiSeedList.innerHTML = '';
  
  if (state.multiSeeds.length === 0) {
    multiSeedList.innerHTML = `<span style="color:var(--text-3);font-size:0.8rem;">Select 2–5 tracks via search bar to synthesize an interpolated vector.</span>`;
    return;
  }

  const defaultWeights = [0.5, 0.25, 0.15, 0.10, 0.05];

  state.multiSeeds.forEach((track, idx) => {
    const chip = document.createElement('div');
    chip.className = 'seed-chip';
    chip.innerHTML = `
      <span><strong>${escapeHtml(track.title)}</strong> &bull; ${escapeHtml(track.artist)}</span>
      <span style="font-family:var(--font-mono);font-size:0.75rem;color:var(--accent);">w=${defaultWeights[idx] || 0.05}</span>
      <button class="chip-remove" title="Remove track">&times;</button>
    `;
    chip.querySelector('.chip-remove').addEventListener('click', () => {
      removeMultiSeedTrack(idx);
    });
    multiSeedList.appendChild(chip);
  });
}

// ======= Recommendation Execution =======

function handleGetRecommendations() {
  const limit = recLimitSlider ? parseInt(recLimitSlider.value, 10) : 10;
  const apply_rerank = toggleRerank ? toggleRerank.checked : true;
  const filter_hindi = toggleHindi ? toggleHindi.checked : false;

  if (state.currentMode === 'single') {
    const query = searchInput ? searchInput.value.trim() : '';
    const song_id = state.selectedSeed ? state.selectedSeed.id : null;
    runRecommendation({
      mode: 'single',
      song_id: song_id,
      song_query: query,
      limit,
      apply_rerank,
      filter_hindi
    });
  } else if (state.currentMode === 'multi') {
    if (state.multiSeeds.length === 0) {
      showToast('Add at least 1 or 2 seed tracks to blend.');
      return;
    }
    const seed_ids = state.multiSeeds.map(s => s.id);
    runRecommendation({
      mode: 'multi',
      seed_ids,
      limit,
      apply_rerank,
      filter_hindi
    });
  } else if (state.currentMode === 'mood') {
    const mood_features = {};
    const moodInputs = document.querySelectorAll('.slider-group input[type="range"], .mood-item input[type="range"]');
    moodInputs.forEach(inp => {
      mood_features[inp.name] = parseFloat(inp.value);
    });
    runRecommendation({
      mode: 'mood',
      mood_features,
      limit,
      apply_rerank: false,
      filter_hindi
    });
  }
}

async function runRecommendation(payload) {
  if (btnGetRecs) {
    btnGetRecs.disabled = true;
    btnGetRecs.innerHTML = `<span class="spinner-dot"></span> Computing...`;
  }

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    
    state.selectedSeed = data.seed;
    const recommendations = data.recommendations || [];

    renderSeedShowcase(data.seed, data.mode);
    renderRecommendations(recommendations, data.seed);
    renderMetaBanner(data);

    if (recommendations.length > 0 && data.seed) {
      updateRadarComparison(data.seed, recommendations[0]);
    }
  } catch (err) {
    console.error('Recommendation API error:', err);
    showToast('Failed to retrieve recommendations. Verify server status.');
  } finally {
    if (btnGetRecs) {
      btnGetRecs.disabled = false;
      btnGetRecs.innerHTML = `Compute Recommendations`;
    }
  }
}

// ======= Renderers =======

function renderMetaBanner(data) {
  if (!metaBanner) return;
  const count = (data.recommendations || []).length;
  metaBanner.innerHTML = `
    <span>Retrieved ${count} nearest candidates in ${data.latency_ms} ms</span>
    <span>Dimensionality: 10-D PCA Latent Space &bull; Metric: Cosine Distance</span>
  `;
}

function renderSeedShowcase(seed, mode) {
  if (!seedShowcaseContainer) return;
  if (!seed) {
    seedShowcaseContainer.innerHTML = '';
    return;
  }

  if (Array.isArray(seed)) {
    seedShowcaseContainer.innerHTML = `
      <div class="seed-banner">
        <div class="seed-art-square" style="display:flex;align-items:center;justify-content:center;font-size:1.4rem;">
          🎛️
        </div>
        <div class="seed-info-block">
          <div class="seed-tagline">Multi-Seed Vector Blend</div>
          <div class="seed-track-name">Composite Vector (${seed.length} Seed Tracks)</div>
          <div class="seed-track-artist">${seed.map(s => escapeHtml(s.title)).join(' + ')}</div>
          <div class="seed-stats-row">
            <span>Decay Weights: [0.50, 0.25, 0.15, 0.10, 0.05]</span>
            <span>PCA Dimensionality: 10 Components</span>
          </div>
        </div>
      </div>
    `;
    return;
  }

  const imgHtml = seed.image_url
    ? `<img src="${seed.image_url}" class="seed-art-square" alt="Artwork">`
    : `<div class="seed-art-square" style="display:flex;align-items:center;justify-content:center;color:var(--text-3);font-size:0.75rem;">ALBUM</div>`;

  const spotifyBtn = seed.spotify_url 
    ? `<a href="${seed.spotify_url}" target="_blank" class="spotify-external-link">Spotify ↗</a>`
    : '';

  const previewBtn = seed.preview_url
    ? `<button class="btn-audio-preview" onclick="toggleAudioPreview('${seed.id}', '${seed.preview_url}', this)">
         Play 30s
       </button>`
    : '';

  const feats = seed.features || {};

  seedShowcaseContainer.innerHTML = `
    <div class="seed-banner">
      ${imgHtml}
      <div class="seed-info-block">
        <div class="seed-tagline">Active Query Coordinates</div>
        <div class="seed-track-name">${escapeHtml(seed.title)}</div>
        <div class="seed-track-artist">${escapeHtml(seed.artist)} &bull; ${seed.year || ''} &bull; ${escapeHtml(seed.cluster_name || '')}</div>
        <div class="seed-stats-row">
          <span>Dance: ${feats.danceability ?? '0.5'}</span>
          <span>Energy: ${feats.energy ?? '0.5'}</span>
          <span>Valence: ${feats.valence ?? '0.5'}</span>
          <span>Acoustic: ${feats.acousticness ?? '0.5'}</span>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end;">
        ${previewBtn}
        ${spotifyBtn}
      </div>
    </div>
  `;
}

function renderRecommendations(tracks, seed) {
  if (!recommendationsContainer) return;
  recommendationsContainer.innerHTML = '';
  if (tracks.length === 0) {
    recommendationsContainer.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 32px; text-align: center; color: var(--text-3); background: var(--surface-1); border-radius: var(--r-md); border:1px solid var(--border);">
        <p>No candidates match the specified criteria.</p>
      </div>
    `;
    return;
  }

  tracks.forEach(track => {
    const card = document.createElement('div');
    card.className = 'minimal-card';

    const imgHtml = track.image_url
      ? `<img src="${track.image_url}" class="card-album-art" alt="Artwork" loading="lazy">`
      : `<div class="card-album-art" style="display:flex;align-items:center;justify-content:center;color:var(--text-3);font-size:0.75rem;">SONG</div>`;

    const previewBtn = track.preview_url
      ? `<button class="btn-audio-preview" onclick="toggleAudioPreview('${track.id}', '${track.preview_url}', this)">
           Play 30s
         </button>`
      : `<span style="font-size:0.72rem;color:var(--text-3);">No audio</span>`;

    const spotifyLink = track.spotify_url
      ? `<a href="${track.spotify_url}" target="_blank" class="spotify-external-link">Spotify ↗</a>`
      : '';

    const feats = track.features || {};

    card.innerHTML = `
      <div class="card-top">
        ${imgHtml}
        <div class="card-meta">
          <div class="card-song-title" title="${escapeHtml(track.title)}">${escapeHtml(track.title)}</div>
          <div class="card-artist-sub" title="${escapeHtml(track.artist)}">${escapeHtml(track.artist)}</div>
          <div class="card-tag-row">
            <span class="card-pill">${track.year}</span>
            <span class="card-pill">${escapeHtml(track.cluster_name)}</span>
            ${track.bonus > 0 ? `<span class="card-pill" style="color:var(--accent);">+${track.bonus} bonus</span>` : ''}
          </div>
        </div>
        <div class="card-score">
          <div class="card-score-val">${track.similarity}%</div>
          <div class="card-score-lbl">Cosine Match</div>
        </div>
      </div>

      <div class="card-meters">
        <div class="meter-unit">
          <div class="meter-lbl"><span>Energy</span> <span>${feats.energy || 0}</span></div>
          <div class="meter-track">
            <div class="meter-fill" style="width:${(feats.energy || 0) * 100}%;"></div>
          </div>
        </div>
        <div class="meter-unit">
          <div class="meter-lbl"><span>Danceability</span> <span>${feats.danceability || 0}</span></div>
          <div class="meter-track">
            <div class="meter-fill" style="width:${(feats.danceability || 0) * 100}%;"></div>
          </div>
        </div>
        <div class="meter-unit">
          <div class="meter-lbl"><span>Valence</span> <span>${feats.valence || 0}</span></div>
          <div class="meter-track">
            <div class="meter-fill" style="width:${(feats.valence || 0) * 100}%;"></div>
          </div>
        </div>
        <div class="meter-unit">
          <div class="meter-lbl"><span>Acousticness</span> <span>${feats.acousticness || 0}</span></div>
          <div class="meter-track">
            <div class="meter-fill" style="width:${(feats.acousticness || 0) * 100}%;"></div>
          </div>
        </div>
      </div>

      <div class="card-bottom-actions">
        ${previewBtn}
        <button class="btn-radar-link" data-track-id="${track.id}">
          Compare in Radar
        </button>
        ${spotifyLink}
      </div>
    `;

    card.querySelector('.btn-radar-link').addEventListener('click', () => {
      if (seed) {
        updateRadarComparison(seed, track);
        const radarElem = document.getElementById('radar');
        if (radarElem) radarElem.scrollIntoView({ behavior: 'smooth' });
        showToast(`Comparing "${seed.title || 'Seed'}" with "${track.title}" in Radar`);
      }
    });

    recommendationsContainer.appendChild(card);
  });
}

// ======= Audio Preview Player =======

window.toggleAudioPreview = function(trackId, previewUrl, btnElement) {
  if (state.currentAudio) {
    state.currentAudio.pause();
    document.querySelectorAll('.btn-audio-preview, .btn-preview').forEach(b => {
      b.classList.remove('playing');
      b.textContent = 'Play 30s';
    });

    if (state.currentPlayingId === trackId) {
      state.currentAudio = null;
      state.currentPlayingId = null;
      return;
    }
  }

  const audio = new Audio(previewUrl);
  audio.volume = 0.8;
  state.currentAudio = audio;
  state.currentPlayingId = trackId;

  btnElement.classList.add('playing');
  btnElement.textContent = 'Pause';

  audio.play().catch(e => {
    console.warn('Playback error:', e);
    showToast('Browser blocked autoplay or audio URL is unavailable.');
    btnElement.classList.remove('playing');
    btnElement.textContent = 'Play 30s';
  });

  audio.addEventListener('ended', () => {
    btnElement.classList.remove('playing');
    btnElement.textContent = 'Play 30s';
    state.currentAudio = null;
    state.currentPlayingId = null;
  });
};

// ======= Radar Chart Comparison =======

function updateRadarComparison(seedTrack, recTrack) {
  state.selectedRecForComparison = recTrack;
  
  const titleA = document.getElementById('radarTitleA');
  const titleB = document.getElementById('radarTitleB');
  if (titleA) titleA.textContent = seedTrack.title || 'Seed Track';
  if (titleB) titleB.textContent = recTrack.title || 'Candidate Track';

  const featsA = seedTrack.features || {};
  const featsB = recTrack.features || {};

  const labels = ['Danceability', 'Energy', 'Valence', 'Acousticness', 'Instrumentalness', 'Liveness', 'Speechiness'];
  const keys = ['danceability', 'energy', 'valence', 'acousticness', 'instrumentalness', 'liveness', 'speechiness'];
  
  const dataA = keys.map(k => parseFloat(featsA[k] || 0));
  const dataB = keys.map(k => parseFloat(featsB[k] || 0));

  renderRadarChart(labels, dataA, dataB, seedTrack.title || 'Seed Track', recTrack.title || 'Candidate Track');
  renderRadarMetricsTable(labels, keys, featsA, featsB);
}

function renderRadarChart(labels, dataA, dataB, labelA, labelB) {
  const canvas = document.getElementById('radarCanvas');
  if (!canvas) return;

  if (window.Chart) {
    if (state.radarChart) {
      state.radarChart.destroy();
    }
    const ctx = canvas.getContext('2d');
    state.radarChart = new Chart(ctx, {
      type: 'radar',
      data: {
        labels: labels,
        datasets: [
          {
            label: labelA,
            data: dataA,
            backgroundColor: 'rgba(48, 209, 88, 0.16)',
            borderColor: '#30d158',
            pointBackgroundColor: '#30d158',
            pointBorderColor: '#09090b',
            borderWidth: 1.5
          },
          {
            label: labelB,
            data: dataB,
            backgroundColor: 'rgba(255, 255, 255, 0.12)',
            borderColor: '#f4f4f6',
            pointBackgroundColor: '#f4f4f6',
            pointBorderColor: '#09090b',
            borderWidth: 1.5
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          r: {
            angleLines: { color: 'rgba(255, 255, 255, 0.08)' },
            grid: { color: 'rgba(255, 255, 255, 0.06)' },
            pointLabels: {
              color: '#8e8e93',
              font: { size: 11, family: 'Plus Jakarta Sans' }
            },
            ticks: {
              color: '#636366',
              backdropColor: 'transparent',
              stepSize: 0.25,
              min: 0,
              max: 1
            }
          }
        },
        plugins: {
          legend: {
            labels: { color: '#f4f4f6', font: { size: 12, family: 'Plus Jakarta Sans' } }
          }
        }
      }
    });
  } else {
    drawFallbackRadarCanvas(canvas, labels, dataA, dataB);
  }
}

function drawFallbackRadarCanvas(canvas, labels, dataA, dataB) {
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);

  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(cx, cy) - 40;
  const count = labels.length;

  ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
  ctx.lineWidth = 1;
  for (let r = 0.25; r <= 1.0; r += 0.25) {
    ctx.beginPath();
    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 / count) * i - Math.PI / 2;
      const x = cx + Math.cos(angle) * (radius * r);
      const y = cy + Math.sin(angle) * (radius * r);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.stroke();
  }

  ctx.fillStyle = '#8e8e93';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 / count) * i - Math.PI / 2;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x, y);
    ctx.stroke();

    const lx = cx + Math.cos(angle) * (radius + 18);
    const ly = cy + Math.sin(angle) * (radius + 18);
    ctx.fillText(labels[i], lx, ly);
  }

  drawPoly(ctx, cx, cy, radius, count, dataA, 'rgba(48, 209, 88, 0.2)', '#30d158');
  drawPoly(ctx, cx, cy, radius, count, dataB, 'rgba(255, 255, 255, 0.15)', '#f4f4f6');
}

function drawPoly(ctx, cx, cy, radius, count, data, fill, stroke) {
  ctx.beginPath();
  for (let i = 0; i < count; i++) {
    const val = Math.max(0, Math.min(1, data[i]));
    const angle = (Math.PI * 2 / count) * i - Math.PI / 2;
    const x = cx + Math.cos(angle) * (radius * val);
    const y = cy + Math.sin(angle) * (radius * val);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

function renderRadarMetricsTable(labels, keys, featsA, featsB) {
  const tbody = document.getElementById('radarMetricsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  keys.forEach((k, idx) => {
    const valA = parseFloat(featsA[k] || 0);
    const valB = parseFloat(featsB[k] || 0);
    const diff = Math.abs(valA - valB);

    let diffClass = 'low';
    if (diff > 0.35) diffClass = 'high';
    else if (diff > 0.15) diffClass = 'med';

    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${labels[idx]}</td>
      <td class="mono-cell" style="color:var(--accent);">${valA.toFixed(3)}</td>
      <td class="mono-cell">${valB.toFixed(3)}</td>
      <td>
        <span class="delta-badge ${diffClass}">&Delta; ${diff.toFixed(3)}</span>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// ======= Viva Defense Accordion =======

function initVivaAccordion() {
  const items = document.querySelectorAll('.accordion-item, .viva-item');
  items.forEach(item => {
    const trigger = item.querySelector('.accordion-trigger, .viva-question-header');
    if (!trigger) return;
    trigger.addEventListener('click', () => {
      const wasOpen = item.classList.contains('open');
      if (!wasOpen) {
        item.classList.add('open');
      } else {
        item.classList.remove('open');
      }
    });
  });
}

// ======= Toast Helper =======

function showToast(msg) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2800);
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

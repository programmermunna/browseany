/* ============================================================
   Browse Any — app.js
   Simple version: loads URL arrays from DB/, random selection,
   history navigation, and iframe error handling.
   ============================================================ */

(function () {
  'use strict';

  /* ----------------------------------------------------------
     1. DATABASE
     URL arrays loaded from DB/*.js files
     ---------------------------------------------------------- */
  const DB_DATA = {
    general: { urls: DB_GENERAL, label: 'General', group: 'General' },
    tools: { urls: DB_TOOLS, label: 'Tools', group: 'Technology' },
    games: { urls: DB_GAMES, label: 'Games', group: 'Entertainment' },
    art: { urls: DB_ART, label: 'Art', group: 'Culture' },
    funny: { urls: DB_FUNNY, label: 'Funny', group: 'Entertainment' },
    sports: { urls: DB_SPORTS, label: 'Sports', group: 'Entertainment' },
    news: { urls: DB_NEWS, label: 'News', group: 'Media' },
    education: { urls: DB_EDUCATION, label: 'Education', group: 'Learning' },
    health: { urls: DB_HEALTH, label: 'Health', group: 'Lifestyle' },
    finance: { urls: DB_FINANCE, label: 'Finance', group: 'Business' },
    travel: { urls: DB_TRAVEL, label: 'Travel', group: 'Lifestyle' },
    food: { urls: DB_FOOD, label: 'Food', group: 'Lifestyle' },
    music: { urls: DB_MUSIC, label: 'Music', group: 'Entertainment' },
    shopping: { urls: DB_SHOPPING, label: 'Shopping', group: 'Lifestyle' },
    technology: { urls: DB_TECHNOLOGY, label: 'Technology', group: 'Media' },
    science: { urls: DB_SCIENCE, label: 'Science', group: 'Learning' },
    social: { urls: DB_SOCIAL, label: 'Social', group: 'Media' },
    business: { urls: DB_BUSINESS, label: 'Business', group: 'Business' },
    programming: { urls: DB_PROGRAMMING, label: 'Programming', group: 'Technology' },
    design: { urls: DB_DESIGN, label: 'Design', group: 'Technology' },
    photography: { urls: DB_PHOTOGRAPHY, label: 'Photography', group: 'Technology' },
    movies: { urls: DB_MOVIES, label: 'Movies', group: 'Entertainment' },
    books: { urls: DB_BOOKS, label: 'Books', group: 'Learning' },
    fitness: { urls: DB_FITNESS, label: 'Fitness', group: 'Lifestyle' },
    crypto: { urls: DB_CRYPTO, label: 'Crypto', group: 'Business' },
    environment: { urls: DB_ENVIRONMENT, label: 'Environment', group: 'Culture' },
    history: { urls: DB_HISTORY, label: 'History', group: 'Culture' },
    comedy: { urls: DB_COMEDY, label: 'Comedy', group: 'Entertainment' },
    tvshows: { urls: DB_TVSHOWS, label: 'TV Shows', group: 'Entertainment' },
    celebrities: { urls: DB_CELEBRITIES, label: 'Celebrities', group: 'Entertainment' },
    gamingnews: { urls: DB_GAMINGNEWS, label: 'Gaming News', group: 'Entertainment' },
    streaming: { urls: DB_STREAMING, label: 'Streaming', group: 'Entertainment' },
    animation: { urls: DB_ANIMATION, label: 'Animation', group: 'Entertainment' },
    anime: { urls: DB_ANIME, label: 'Anime', group: 'Entertainment' },
    cartoons: { urls: DB_CARTOONS, label: 'Cartoons', group: 'Entertainment' },
    filmfestivals: { urls: DB_FILMFESTIVALS, label: 'Film Festivals', group: 'Entertainment' }
  };

  
  /* ----------------------------------------------------------
     3. STATE
     ---------------------------------------------------------- */
  let dbCache = {};        // { categoryKey: [url1, url2, ...] }
  let history = [];        // ordered list of visited { url, source }
  let historyIndex = -1;
  let loadTimeoutId = null;
  let currentSource = null;
  let favorites = [];      // array of { url, name, addedAt }
  let autoClickTimer = null; // auto-click timer interval
  let autoClickInterval = null; // auto-click interval in seconds

  const LOAD_TIMEOUT_MS = 6000;
  const LOADING_MESSAGES = [
    'loading…', 'finding…', 'searching…'
  ];

  function getRandomLoadTime() {
    // Weighted random: 40% for 1s, 40% for 2s, 20% for 3s
    const rand = Math.random();
    if (rand < 0.4) return 1000;      // 1s
    if (rand < 0.8) return 2000;      // 2s
    return 3000;                      // 3s
  }

  /* ----------------------------------------------------------
     4. DOM REFS
     ---------------------------------------------------------- */
  const $ = (id) => document.getElementById(id);
  const iframe         = $('siteFrame');
  const emptyState      = $('emptyState');
  const loadingOverlay  = $('loadingOverlay');
  const loadingLabel    = $('loadingLabel');
  const errorOverlay    = $('errorOverlay');
  const errorOpenBtn    = $('errorOpenBtn');
  const urlReadout      = $('urlReadout');
  const backBtn         = $('backBtn');
  const nextBtn         = $('nextBtn');
  const categorySelect  = $('categorySelect');
  const randomDbBtn     = $('randomDbBtn');
  const randomDbIcon    = $('randomDbIcon');
  const openNewTabBtn   = $('openNewTabBtn');
  const keyboardHelpBtn = $('keyboardHelpBtn');
  const addFavBtn       = $('addFavBtn');
  const favBtn          = $('favBtn');
  const favoritesDrawer = $('favoritesDrawer');
  const drawerOverlay   = $('drawerOverlay');
  const closeDrawerBtn  = $('closeDrawerBtn');
  const favoritesList   = $('favoritesList');
  const landingRandomBtn = $('landingRandomBtn');
  const autoClickBtn    = $('autoClickBtn');
  const autoClickMenu   = $('autoClickMenu');

  /* ----------------------------------------------------------
     5. DATABASE INITIALIZATION
     ---------------------------------------------------------- */
  function initDatabase() {
    categorySelect.innerHTML = '';

    const allOption = document.createElement('option');
    allOption.value = 'all';
    allOption.textContent = 'All categories';
    categorySelect.appendChild(allOption);

    // Group categories by group property
    const groups = {};
    for (const [key, data] of Object.entries(DB_DATA)) {
      const groupName = data.group || 'Other';
      if (!groups[groupName]) {
        groups[groupName] = [];
      }
      groups[groupName].push({ key, label: data.label });
    }

    // Sort groups alphabetically
    const sortedGroups = Object.keys(groups).sort();

    // Create optgroups and add sorted categories
    for (const groupName of sortedGroups) {
      const optgroup = document.createElement('optgroup');
      optgroup.label = groupName;

      // Sort categories within group alphabetically
      const sortedCategories = groups[groupName].sort((a, b) =>
        a.label.localeCompare(b.label)
      );

      for (const category of sortedCategories) {
        const opt = document.createElement('option');
        opt.value = category.key;
        opt.textContent = category.label;
        optgroup.appendChild(opt);
      }

      categorySelect.appendChild(optgroup);
    }

    categorySelect.value = 'all';
  }

  /* ----------------------------------------------------------
     6. CORE NAVIGATION
     ---------------------------------------------------------- */
  function currentSite() {
    return historyIndex >= 0 ? history[historyIndex] : null;
  }

  function loadSite(site, pushToHistory) {
    clearTimeout(loadTimeoutId);
    emptyState.classList.add('hidden');
    errorOverlay.classList.add('hidden');
    currentSource = site.source || 'db';
    showLoading();

    if (pushToHistory) {
      history = history.slice(0, historyIndex + 1);
      history.push(site);
      historyIndex = history.length - 1;
    }

    iframe.src = site.url;
    updateReadout(site);
    updateNavButtons();
    updateFavButtonState();
    openNewTabBtn.disabled = false;

    // Hide loading after random time (1/2/3s with 1 and 2 most common)
    const loadTime = getRandomLoadTime();
    loadTimeoutId = setTimeout(() => {
      hideLoading();
    }, loadTime);
  }

  function updateReadout(site) {
    const text = site.url;
    urlReadout.textContent = text;
  }

  
  function updateNavButtons() {
    backBtn.disabled = historyIndex <= 0;
    nextBtn.disabled = historyIndex >= history.length - 1;
  }

  function showLoading() {
    loadingLabel.textContent = LOADING_MESSAGES[Math.floor(Math.random() * LOADING_MESSAGES.length)];
    loadingOverlay.classList.remove('hidden');
    randomDbIcon.classList.add('animate-spin');
  }
  function hideLoading() {
    loadingOverlay.classList.add('hidden');
    randomDbIcon.classList.remove('animate-spin');
  }
  function showError() {
    hideLoading();
    errorOverlay.classList.remove('hidden');
  }
  function handleLoadTimeout() {
    hideLoading();
    showError();
  }

  iframe.addEventListener('load', () => {
    if (iframe.src === 'about:blank') return;
    // No longer needed - we use fixed 1s timeout instead
  });

  /* ----------------------------------------------------------
     7. FAVORITES
     ---------------------------------------------------------- */
  function loadFavorites() {
    const stored = localStorage.getItem('browseany_favorites');
    if (stored) {
      try {
        favorites = JSON.parse(stored);
      } catch (e) {
        favorites = [];
      }
    }
  }

  function saveFavorites() {
    localStorage.setItem('browseany_favorites', JSON.stringify(favorites));
  }

  function isFavorite(url) {
    return favorites.some(fav => fav.url === url);
  }

  function addFavorite(url) {
    if (!url || isFavorite(url)) return;
    const name = url.replace(/^https?:\/\//, '').replace(/\/$/, '').split('/')[0];
    favorites.unshift({
      url: url,
      name: name,
      addedAt: Date.now()
    });
    saveFavorites();
    renderFavorites();
    updateFavButtonState();
  }

  function removeFavorite(url) {
    favorites = favorites.filter(fav => fav.url !== url);
    saveFavorites();
    renderFavorites();
    updateFavButtonState();
  }

  function toggleDrawer() {
    favoritesDrawer.classList.toggle('open');
    drawerOverlay.classList.toggle('hidden');
  }

  function closeDrawer() {
    favoritesDrawer.classList.remove('open');
    drawerOverlay.classList.add('hidden');
  }

  function renderFavorites() {
    if (favorites.length === 0) {
      favoritesList.innerHTML = `
        <div class="empty-favorites">
          <p>No favorites yet</p>
          <p>Click the heart icon to save sites</p>
        </div>
      `;
      return;
    }

    favoritesList.innerHTML = favorites.map((fav, index) => `
      <div class="favorite-item">
        <div class="favorite-item-content">
          <div class="favorite-item-name" data-url="${fav.url}">${fav.name}</div>
          <div class="favorite-item-url">${fav.url}</div>
        </div>
        <div class="favorite-item-actions">
          <button class="favorite-delete-btn" data-index="${index}" title="Remove">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>
      </div>
    `).join('');

    // Add event listeners for favorite item names (load in iframe)
    document.querySelectorAll('.favorite-item-name').forEach(item => {
      item.addEventListener('click', () => {
        const url = item.dataset.url;
        loadSite({ url: url, source: 'db' }, true);
        closeDrawer();
      });
    });

    // Add event listeners for delete buttons
    document.querySelectorAll('.favorite-delete-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const index = parseInt(e.currentTarget.dataset.index);
        removeFavorite(favorites[index].url);
      });
    });
  }

  function updateFavButtonState() {
    const site = currentSite();
    if (site && isFavorite(site.url)) {
      addFavBtn.classList.add('ctl-btn--favorited');
    } else {
      addFavBtn.classList.remove('ctl-btn--favorited');
    }
  }

  /* ----------------------------------------------------------
     8. AUTO CLICK TIMER
     ---------------------------------------------------------- */
  function toggleAutoClickMenu() {
    autoClickMenu.classList.toggle('hidden');
  }

  function startAutoClick(intervalSeconds) {
    stopAutoClick(); // Clear any existing timer
    autoClickInterval = intervalSeconds;
    autoClickBtn.classList.add('ctl-btn--active');
    autoClickMenu.classList.add('hidden');
    
    // Start the interval
    autoClickTimer = setInterval(() => {
      randomFromDb();
    }, intervalSeconds * 1000);
  }

  function stopAutoClick() {
    if (autoClickTimer) {
      clearInterval(autoClickTimer);
      autoClickTimer = null;
    }
    autoClickInterval = null;
    autoClickBtn.classList.remove('ctl-btn--active');
    autoClickMenu.classList.add('hidden');
  }

  function toggleAutoClick() {
    if (autoClickTimer) {
      // If running, stop it
      stopAutoClick();
    } else if (autoClickInterval) {
      // If stopped but has interval, resume
      startAutoClick(autoClickInterval);
    } else {
      // If no interval set, show menu
      toggleAutoClickMenu();
    }
  }

  function handleAutoClickMenuClick(e) {
    const item = e.target.closest('.auto-click-menu-item');
    if (!item) return;

    if (item.classList.contains('auto-click-stop')) {
      stopAutoClick();
    } else {
      const time = parseInt(item.dataset.time);
      if (time) {
        startAutoClick(time);
      }
    }
  }

  /* ----------------------------------------------------------
     9. RANDOM DB — from curated URL arrays
     ---------------------------------------------------------- */
  function randomFromDb() {
    const selected = categorySelect.value || 'all';
    randomDbBtn.disabled = true;
    randomDbIcon.classList.add('animate-spin');

    let pool = [];
    if (selected === 'all') {
      for (const data of Object.values(DB_DATA)) {
        pool = pool.concat(data.urls);
      }
    } else {
      pool = DB_DATA[selected]?.urls || [];
    }

    if (pool.length === 0) {
      randomDbBtn.disabled = false;
      return;
    }

    let pick;
    const current = currentSite();
    do {
      pick = pool[Math.floor(Math.random() * pool.length)];
    } while (pool.length > 1 && current && pick === current.url);

    loadSite({ url: pick, source: 'db' }, true);
    randomDbBtn.disabled = false;
  }

  /* ----------------------------------------------------------
     8. KEYBOARD SHORTCUTS
     ---------------------------------------------------------- */
  function handleKeyboardShortcuts(e) {
    // Ignore if user is typing in an input field
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
      return;
    }

    switch (e.key) {
      case ' ':
      case 'Space':
        e.preventDefault();
        randomFromDb();
        break;
      case 'ArrowLeft':
        e.preventDefault();
        if (historyIndex > 0) {
          historyIndex--;
          loadSite(history[historyIndex], false);
        }
        break;
      case 'ArrowRight':
        e.preventDefault();
        if (historyIndex < history.length - 1) {
          historyIndex++;
          loadSite(history[historyIndex], false);
        }
        break;
      case 'f':
      case 'F':
        e.preventDefault();
        const site = currentSite();
        if (site) {
          if (isFavorite(site.url)) {
            removeFavorite(site.url);
          } else {
            addFavorite(site.url);
          }
        }
        break;
      case 'Escape':
        e.preventDefault();
        closeDrawer();
        break;
      case 'o':
      case 'O':
        e.preventDefault();
        const currentSite = currentSite();
        if (currentSite) window.open(currentSite.url, '_blank', 'noopener,noreferrer');
        break;
      case '?':
        e.preventDefault();
        showKeyboardHelp();
        break;
      case '0':
        e.preventDefault();
        history = [];
        historyIndex = -1;
        iframe.src = 'about:blank';
        emptyState.classList.remove('hidden');
        errorOverlay.classList.add('hidden');
        urlReadout.textContent = 'press Random';
        updateNavButtons();
        updateFavButtonState();
        openNewTabBtn.disabled = true;
        break;
    }
  }

  function showKeyboardHelp() {
    const helpContent = `
      <div class="keyboard-help-overlay" id="keyboardHelp" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;z-index:9999;">
        <div style="background:var(--bg-primary);padding:30px;border-radius:12px;max-width:400px;color:var(--text-primary);">
          <h2 style="margin:0 0 20px 0;">Keyboard Shortcuts</h2>
          <div style="display:grid;grid-template-columns:1fr auto;gap:10px;">
            <span>Random site</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">Space</kbd>
            <span>Back</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">←</kbd>
            <span>Next</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">→</kbd>
            <span>Toggle favorite</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">F</kbd>
            <span>Open in new tab</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">O</kbd>
            <span>Close drawer</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">Esc</kbd>
            <span>Reset to home</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">0</kbd>
            <span>Show help</span><kbd style="background:var(--bg-secondary);padding:4px 8px;border-radius:4px;font-family:monospace;">?</kbd>
          </div>
          <button id="closeHelpBtn" style="margin-top:20px;padding:8px 16px;background:var(--accent);color:white;border:none;border-radius:6px;cursor:pointer;">Close</button>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', helpContent);
    document.getElementById('closeHelpBtn').addEventListener('click', () => {
      document.getElementById('keyboardHelp').remove();
    });
    document.getElementById('keyboardHelp').addEventListener('click', (e) => {
      if (e.target.id === 'keyboardHelp') {
        e.target.remove();
      }
    });
  }

  /* ----------------------------------------------------------
     9. EVENT WIRING
     ---------------------------------------------------------- */
  document.addEventListener('keydown', handleKeyboardShortcuts);

  randomDbBtn.addEventListener('click', randomFromDb);
  landingRandomBtn.addEventListener('click', randomFromDb);

  backBtn.addEventListener('click', () => {
    if (historyIndex > 0) {
      historyIndex--;
      loadSite(history[historyIndex], false);
    }
  });
  nextBtn.addEventListener('click', () => {
    if (historyIndex < history.length - 1) {
      historyIndex++;
      loadSite(history[historyIndex], false);
    }
  });

  openNewTabBtn.addEventListener('click', () => {
    const site = currentSite();
    if (site) window.open(site.url, '_blank', 'noopener,noreferrer');
  });

  errorOpenBtn.addEventListener('click', () => {
    const site = currentSite();
    if (site) window.open(site.url, '_blank', 'noopener,noreferrer');
  });

  addFavBtn.addEventListener('click', () => {
    const site = currentSite();
    if (site) {
      addFavorite(site.url);
    }
  });

  favBtn.addEventListener('click', toggleDrawer);

  closeDrawerBtn.addEventListener('click', closeDrawer);
  drawerOverlay.addEventListener('click', closeDrawer);

  keyboardHelpBtn.addEventListener('click', showKeyboardHelp);

  autoClickBtn.addEventListener('click', toggleAutoClick);
  autoClickMenu.addEventListener('click', handleAutoClickMenuClick);

  // Close auto-click menu when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.auto-click-wrapper')) {
      autoClickMenu.classList.add('hidden');
    }
  });

  /* ----------------------------------------------------------
     10. INIT
     ---------------------------------------------------------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      console.log('[DB] DOM loaded, initializing database...');
      initDatabase();
      loadFavorites();
      renderFavorites();
    });
  } else {
    console.log('[DB] DOM already loaded, initializing database...');
    initDatabase();
    loadFavorites();
    renderFavorites();
  }
})();
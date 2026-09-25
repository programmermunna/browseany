---
name: testing-browseany
description: How to run and browser-test the Browse Any static site on this box, including the Devin managed-Chrome/CDP quirks and how to recover if the tool-attached browser dies
---

# Testing Browse Any

## Run it
- Static site, no build. Serve the repo root: `python3 -m http.server 8000` then open `http://localhost:8000`.
- All `DB/*.js` files are plain `<script>` tags loading `var DB_<NAME> = [...]` globals before `app.js`. A syntax error in ANY DB file throws `ReferenceError` in app.js's IIFE and kills the whole app — the category `<select>` stays stuck on "Loading…". A populated dropdown is proof every DB file parsed.
- No Node on this box — `node --check` is unavailable. Validate JS by loading the page (or headless `google-chrome --headless=new --dump-dom` and check the select options render).

## App behavior / UI map
- `#landingRandomBtn` = "Start Exploring" CTA on `#emptyState`; `#randomDbBtn` = Random button (`#randomDbIcon` spins); `#categorySelect` groups options in `<optgroup>`s; `#backBtn`/`#nextBtn` history; `#addFavBtn` heart (adds `ctl-btn--favorited`, persists to `localStorage.browseany_favorites`); `#favBtn` hamburger opens `#favoritesDrawer`; `#urlReadout` shows current URL; `#loadingOverlay` shows 1–3s per pick.
- `randomFromDb()` early-returns when the selected category's array is empty (e.g. Technology, TV Shows) — nothing loads, no error. Native `<select>` navigation: click to open, type a letter to jump, Home for "All categories", Enter to confirm.
- For a category pick, verify the readout URL is actually in that DB file: `grep -n "<host>" DB/<cat>.js`.
- The loading overlay hides on a fixed 1–3s timer regardless of whether the iframe rendered — a blank iframe is not necessarily an app bug; some remaining DB entries are parked domains (return 200 so filter.py keeps them).

## Chrome / CDP on this box (important)
- Devin's managed Chrome runs under `devin-remote` on CDP port **29229**. `google-chrome <url>` (bare URL, no flags) opens a tab in THAT browser — use only this form.
- Launching chrome with flags (e.g. `google-chrome --new-window <url>`) bypasses the shim and spawns an unmanaged instance the `browser_console`/`read_dom` tools cannot see. Closing the last window of the managed instance kills it and devin-remote does NOT auto-respawn.
- Recovery if the managed browser dies: relaunch with `/opt/.devin/chrome/chrome/linux-*/chrome-linux64/chrome --remote-debugging-port=29229 --new-window <url>`. `browser_console` may still refuse to attach (it binds to the devin-remote-proxied endpoint) — drive CDP directly instead: python `websockets` is installed; `curl http://localhost:29229/json/list` → `webSocketDebuggerUrl` → `Runtime.evaluate`. Working helper: `/tmp/cdp_eval.py`.
- To capture console errors across a run without the console tool: inject `window.addEventListener('error', fn, true)` + `unhandledrejection` collector into `window.__errlog` via Runtime.evaluate, then read it at the end. Re-inject after every page reload — the collector does not survive navigation.
- CDP `Emulation.setDeviceMetricsOverride` is session-scoped: it drops the moment your websocket disconnects. For responsive screenshots, keep a background process holding the ws open (see `/tmp/cdp_hold_emulate.py`), screenshot while it runs, then reload the page to fully clear.
- Screenshot-space → viewport-pixel mapping: `display_px = scaled * 1.5625` on this 1600x1200 box, and `viewport_y ≈ display_y - ~139` (browser chrome). When click coords matter (chips, FAB), read `getBoundingClientRect()` via CDP and convert rather than estimating from screenshots.

## Devin Secrets Needed
- None — app is fully static and unauthenticated.

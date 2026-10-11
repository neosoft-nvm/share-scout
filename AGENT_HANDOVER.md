# ShareScout AI Agent Handover Document

**Date**: 2026-10-10  
**Current Commit**: `d8c1586` (`main`)  
**Target Release**: `v0.6.0`  
**Authoritative Repo**: `/home/lsparks1/VsCode/share-scout` (`git@github.com:neosoft-nvm/share-scout.git`)  
**Installed Desktop App Location**: `~/.local/share/ResourceMapper/`

---

## 1. Executive Summary & Context
The user is non-technical and evaluates the application by launching it from the desktop Application Menu on Fedora 44 (MATE desktop on X11, 4K display at 100% UI scaling). The user was highly frustrated by previous scaling swings (microscopic text on 4K -> blown-up 1.62x oversized elements) and has requested a handover for the successor agent.

The user explicitly highlighted an app architecture built by Claude ("Roster"):
- **Language**: TypeScript + React 19
- **Build tool**: Vite (`src/`)
- **Desktop**: Tauri 2 wrapper (Linux & Windows)
- **Mobile**: Capacitor 8 (Android APK)
- **CI**: GitHub Actions workflow (`.github/workflows/build.yml`)
- **Testing**: Vitest (`npm test`)

---

## 2. Current Architecture & Dual-Track Status

### Track A: Python Desktop Application (Active Installed Base)
- **Files**: `resource_mapper.py`, `discovery.py`, `network.py`, `ui.py`, `vendor/customtkinter/`
- **Current State**:
  - Normalized to standard 1.0x desktop scale (`ui.py`, `vendor/.../scaling_tracker.py`).
  - Hero icons resized to crisp 48x48 (`icon_network.png`, `icon_cloud.png`, `icon_share.png`).
  - Window geometry centered: Main window 940x600, Discovery window 900x580.
  - Discovery panel overhauled to two-column card layout (`discovery.py`) matching mockup with status badges (`NAS`, `Desktop`, `[Read/Write]`, `[Password Protected]`, `[Guest]`).
  - All 96 unit tests pass: `python3 -m unittest discover -s tests`.
- **CRITICAL DEPLOYMENT DETAIL**:
  When the user launches ShareScout from the system Application Menu, the system executes `~/.local/share/ResourceMapper/Start-Resource-Mapper`. Any updates made to root `*.py` or `icon_*.png` files **must be copied** to `~/.local/share/ResourceMapper/` using the logic in `Launch-Linux.sh`, or the user will see stale code.

### Track B: Modern Web / Tauri / Capacitor (Target Architecture)
- **Files**: `src/` (`App.tsx`, `screens/Dashboard.tsx`, `screens/Discovery.tsx`), `src-tauri/`, `android/`, `package.json`, `vite.config.ts`
- **Current State**:
  - Scaffolding complete; screens for Dashboard and Network Discovery are built.
  - Capacitor 8 Android configuration in `android/` with working GitHub Actions workflow producing `app-debug.apk` (requires Java 21).
  - Vitest test suite in `tests/dashboard.test.tsx` (3/3 passing via `npm test`).
  - Tauri local builds on this Fedora system require `webkit2gtk-4.1` and `librsvg2` (not yet installed locally, but configured for GitHub Actions CI).

---

## 3. Key Operational Pitfalls & Learnings
1. **Never use manual DPI multipliers on Linux X11**:
   Applying `1.62x` via CustomTkinter inflated the window to 1555x1037 with massive 88px icons and clipped buttons, triggering the "tooooooo big" reaction. Keep scale at standard 1.0x with clean, bounded geometry.
2. **Always inspect real rendered screenshots**:
   Do not declare visual work complete based solely on unit test passes. Use `/usr/bin/import -window <id> <output.png>` to capture live windows and inspect them with `view_file` before committing.
3. **Keep responses concise and direct**:
   Per Directive 7 of `AGENTS.md`, avoid long-winded technical excuses. State exactly what was changed, verified, and delivered.

---

## 4. Verification Commands
Always run and verify both suites before and after any modification:
```bash
# Python test suite (must pass 96/96)
python3 -m unittest discover -s tests

# Vitest test suite (must pass 3/3)
npm test

# Sync to local app menu installation
cp -u ./*.py ./Launch-Linux.sh ./Start-Resource-Mapper ./sharescout.png ./sharescout.svg ./icon_*.png ~/.local/share/ResourceMapper/
cp -ru ./vendor ~/.local/share/ResourceMapper/
```

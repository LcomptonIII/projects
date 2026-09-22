# Anchor Point 1.0.0

- Promoted the validated RC2.11 codebase to the 1.0.0 production release.
- Finalized release, installer, CLI, README, and CI artifact version metadata.
- No resolver, sync-safety, startup, icon, or workflow behavior changes from RC2.11.

# Anchor Point 1.0.0 RC2.11

- Fixed Netflix and Manual Entry status-bar counts to follow the configured storage directory instead of a hardcoded install-relative `data` path.
- Fixed MAL XML CLI export to resolve relative output paths against the active config directory rather than the process working directory.
- Added regression coverage for both path-resolution fixes.
- No resolver, sync-safety, startup, or icon behavior changes.

# Anchor Point 1.0.0 RC2.10

- Restored the last known-good PNG-compressed multi-resolution Windows ICO from RC2.7 after RC2.8 introduced an all-BMP/DIB ICO associated with an immediate startup termination on Windows.
- Added persistent `startup_error.log` capture for Python-level GUI startup exceptions.
- Added `build_windows_debug.bat` to produce a console-enabled diagnostic executable without changing the normal windowed build.
- Preserved RC2.8 release-hardening changes and the validated season-aware resolver behavior.

# Anchor Point 1.0.0 RC2.8

## RC2.8

- Windows taskbar icon now uses the executable/native multi-resolution ICO path without Tk iconphoto overriding the shell HICON.
- Rebuilt the ICO with native 16/20/24/32/40/48/64/96/128/256 px frames for common Windows DPI scales.
- Removed the incomplete language selector from the 1.0 UI and pinned the shipped interface to English.
- Clarified resolver diagnostics from `cached identity reused` to `identity match reused`.
- Carries forward RC2.7's validated generic explicit-season resolver correction.

# Anchor Point 1.0.0 RC2.7

## RC2.7

- Added Windows per-monitor DPI awareness before Tk initialization.
- Reworked runtime window/taskbar icon setup to use the bundled multi-resolution ICO plus 16/24/32/48/64/128/256 px LANCZOS PhotoImages.
- Fixed Netflix explicit-season resolution so strongly matched Season 2/3/etc. candidates are not collapsed onto an unlabeled Season 1 entry.
- Added regression coverage for One-Punch Man-style Netflix season metadata and conservative no-guess behavior.


- Added atomic resolution checkpoints every 20 newly analyzed groups.
- Interrupted first-time resolution can reuse the latest safe checkpoint on the next Preview.
- Added rolling resolution ETA based only on groups requiring fresh analysis.
- Expanded first-run messaging for large libraries that may require several hours.
- HIDIVE authentication failures now preserve and clearly identify the last successful local HIDIVE history instead of presenting a failed live refresh as current.
- HIDIVE live-refresh failure no longer prevents the remaining read-only Preview pipeline from running when saved HIDIVE history exists.

# Anchor Point 1.0.0 RC2.5

- Added immediate first-run Resolution guidance and cache-reuse counts before long resolver work begins.
- Resolution progress now clearly reports analyzed groups so a clean first run does not appear frozen.
- Rebuilt the Windows ICO from cleaned, sharpened source artwork for crisper small taskbar/shortcut rendering.
- Corrected installer version metadata to match the release candidate.

# Anchor Point 1.0.0 RC2.4

- Fixed a Windows CP1252 crash in the Sync workflow log caused by Unicode box-drawing section separators.
- Workflow section separators now use ASCII-only characters so frozen/windowed subprocess output is safe on legacy Windows console encodings.
- Updated release metadata to RC2.4.

# Anchor Point 1.0.0 RC2.3

- Updated the Crunchyroll source shortcut to open Watch History directly.
- Added a HIDIVE Watch History shortcut.
- Added a Netflix profile-management shortcut with the Viewing Activity navigation note.
- No resolver, sync, authentication, or destination-write behavior changed.

# Anchor Point 1.0.0 RC2.1

- Hotfix: restore the optional `RELEASES_URL` version constant expected by Export & Sync Settings. The URL remains disabled until the public Anchor Point release repository is established.

- Hardening-only release candidate based on the independent second-pass code review; no new product features.
- Centralized writable data paths around the configured history location so CLI, GUI, resolver artifacts, imports, backups, and logs no longer depend on process CWD.
- Consolidated GUI and CLI scheduled-task registration behind one shared scheduler implementation; CLI scheduling now embeds an absolute config path.
- Pinned tray sync subprocesses to the application data root for source/dev parity.
- Added resolver-cache schema metadata so future resolver/override changes can deliberately invalidate stale identity mappings; legacy RC1 cache is adopted without forcing an unnecessary full re-resolution.
- Strengthened Cancel Workflow with terminate, bounded wait, kill escalation, and confirmed-stop feedback.
- Added focused RC2 regression tests for configured path resolution and cache versioning.
- Historical MultiSource/CrunchyExporter development entries remain below for traceability.

## 1.3.0-ms9.8.1 - Release cleanup

- Removed obsolete CrunchyExporter branding assets, tutorial media, test cache, and superseded milestone notes from the distribution.
- Updated active Windows build, locale, config, user-agent, and workflow references to Anchor Point.
- Replaced the inherited README with a concise Anchor Point release/build guide while preserving upstream attribution.

# 1.3.0-ms9.8.0 — Anchor Point brand transition

- Renamed the user-facing application from CrunchyExporter MultiSource to **Anchor Point**.
- Added tagline: *Your anime history, connected.*
- Replaced the Windows, taskbar, tray, and installer icon with the new Anchor Point anchor artwork.
- Windows executable now builds as `AnchorPoint.exe`; installer builds as `AnchorPoint-1.3.0-ms9.8.0-Setup.exe`.
- Preserved the validated resolver, source normalization, caching, quarantine, AniList safety, MAL safety, and workflow behavior from ms9.7.3.
- Retained internal/upstream CrunchyExporter references where they document lineage or avoid unnecessary compatibility risk.

# MultiSource 1.3.0-ms9.4 - 2026-09-18

- Added `sync-all`, a read-only-by-default end-to-end workflow for provider refresh/import, resolution, AniList planning, and optional protected apply.
- Preserved the validated production write engine: account/hash binding, drift detection, backup, quarantine gates, mutation logging, post-write verification, and non-regressing progress.
- Added integrated release documentation and explicit MultiSource version command.
- Resolver behavior remains frozen at the validated v9.3 baseline.

# v9.3 - Final quarantine cleanup

- Exclude Netflix `Dark` as verified live-action/non-anime.
- Map Crunchyroll KONOSUBA provider bucket 5 to the original TV series.
- Release verified KONOSUBA season 3 and Netflix Overlord II ADDs from final review.
- Preserve quarantine for Versatile Mage S8, Deadman Wonderland 13/12, and any AniList ID that still fails exact remote validation.
- Production sync/backup/drift/idempotency engine unchanged.

## MultiSource v9.2 - catalog-evidence cleanup

- Correct Crunchyroll Hunter x Hunter provider season 5 to the 2011 adaptation.
- Correct Netflix SHAMAN KING to the 2021 adaptation.
- Split Netflix Overlord II/III into their proper AniList sequel entries.
- Release Chainsmoker Cat from the exact-title hold after positive catalog evidence.
- Confirm AniList batch misses with an exact-ID query before marking IDs stale.
- Preserve quarantine for unresolved provider numbering, distinct OVAs, and genuine stale IDs.
- 150 tests passing.

# Changelog

All notable changes to CrunchyExporter GUI will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.0] — 2026-06-29

### Fixed
- **Multi-season shows collapsed into one My Library entry**: Crunchyroll
  reuses the same internal `series_id` across every season of a show — only
  `season_number` tells them apart. Local history grouping only looked at
  `series_id`, so a multi-season show (e.g. *The Rising of the Shield Hero*)
  merged all of its seasons into one combined entry with progress computed
  across the wrong combined set of episodes. Each season now gets its own
  entry and its own correct progress.
- **AniList/MAL export — wrong season overwritten**: Crunchyroll rarely puts
  the season number in the episode title, so exporting season 2+ of a show
  always matched and overwrote season 1's AniList/MAL entry. The exporter
  now follows the sequel relation chain to resolve the correct season entry.
- **AniList/MAL export — progress could be overwritten with stale data**:
  exports now check the existing remote progress first and skip the series
  instead of writing a lower episode count or status.
- **MAL export — search fails on long titles**: MAL's `/anime` search
  rejects queries past ~64 characters with `400 invalid q`, which happened
  routinely with Crunchyroll's long English subtitles (e.g. "Hensuki - Are
  you willing to fall in love with a pervert, as long as she's a cutie?").
  The search now retries with the part before a subtitle separator, then a
  hard truncation, before giving up.
- **Missing dependencies**: `click` and `rich` are used by the bundled
  `src/main.py` (invoked by the Schedule tab when running from source) but
  were never declared in `requirements.txt`, breaking scheduled syncs on a
  fresh install.

### Added
- **Export preview & confirmation**: before writing to AniList/MAL, a dry-run
  pass shows exactly what would change. Confirmation is a non-modal panel
  under the log (not a blocking dialog), so the log stays scrollable while
  reviewing. You can apply every change at once, or review and
  approve/skip each series individually per target.
- **"Only since" date filter**: optionally export only episodes watched on
  or after a given date — useful if older history is already tracked
  elsewhere (e.g. MALSync).
- **My Library — manual edit**: a pencil button per series opens an editor
  for title, season number and progress. Saved corrections are stored
  separately from the raw watch history and can be reverted.
- **Settings tab — version footer**: shows the current app version at the
  bottom, linking to the GitHub releases page, and highlights when a newer
  release is available (checked once on startup).
- **Video tutorial** in the README.

---

## [1.2.0] — 2026-06-19

### Added
- **MAL Settings — App Type selector**: a new checkbox lets you mark your
  MyAnimeList app as App Type `web`, revealing a Client Secret field. App Type
  `other` (the simpler, recommended option) still needs only the Client ID.

### Fixed
- **MAL OAuth — Client Secret never sent**: the Settings dialog always
  exchanged the authorization code with an empty client_secret, so MAL `web`
  type apps failed authentication even with a valid access token. The secret
  entered in Settings is now passed through to the token exchange.

---

## [1.1.0] — 2026-05-20

### Fixed
- **Schedule tab — GUI freeze**: creating or removing a scheduled task blocked
  the main thread while `schtasks` ran. All subprocess calls now run in daemon
  threads and marshal results back via `frame.after(0, callback)`.
- **MAL export — early stop on HTTP errors**: the exporter now continues with
  remaining entries instead of stopping at the first HTTP error.
- **MAL search — silent failures**: `search_anime()` now reports detailed error
  messages when a request fails instead of returning an empty result.

### Added
- **Export log persistence**: the sync/export log is now written to disk so
  history survives application restarts.
- **Unit tests and CI**: 73 tests across auth, history store, exporters and
  export log, with a GitHub Actions workflow.

---

## [1.0.1] — 2026-05-14

### Fixed
- **Frozen exe — config and data paths**: when running as a PyInstaller bundle,
  `config.yaml` and `data/` were being written to `sys._MEIPASS` (PyInstaller's
  temp extraction dir) and lost on every close. They now resolve correctly to the
  directory containing the executable.
- **Frozen exe — schedule command**: the scheduled task was generating a path to
  `src/main.py` inside the temp extraction dir (e.g.
  `C:\Users\<user>\AppData\Local\Temp\_MEI...\src\main.py`) which breaks after
  the dir is cleaned up. When frozen, the command is now
  `CrunchyExporter.exe --headless-sync --target <target>`.
- **Frozen exe — tray "Sync Now"**: same fix as schedule; tray sync now calls
  `CrunchyExporter.exe --headless-sync` instead of the temp path.

### Added
- `gui/paths.py`: `resource_root()` / `data_root()` helpers to distinguish
  bundled resources from user-writable files in both frozen and script modes.
- `--headless-sync` mode in `main.py` for scheduled/tray sync when running
  as a frozen executable.

---

## [1.0.0] — 2026-05-13

### Added
- **Sync tab** — fetch Crunchyroll watch history with per-page progress and cancel support
- **My Library tab** — scrollable table of all watched series with episode counts
- **Export tab** — export to AniList, MyAnimeList and local MAL XML with per-target status cards
- **Schedule tab** — register/remove a daily auto-sync task (Windows Task Scheduler / crontab)
- **Settings tab** — full config editor with inline OAuth flows for AniList and MAL
- **Status bar** — at-a-glance indicators for cookie, history, AniList, MAL and XML readiness
- **System tray** (opt-in) — minimize to background with "Sync Now" and toast notifications
- **i18n** — English and Spanish; add new languages by dropping a JSON file in `locales/`
- Custom window icon (PNG → ICO auto-generated on first run)
- Dark mode UI with CustomTkinter

## Multi-Source v6 beta
- Netflix resolution now searches progressively broader normalized title variants before classification.
- Netflix uses positive AniList title evidence; weak fuzzy collisions are excluded instead of sent to review.
- Preserves Netflix catalog qualifiers such as Limited Series and Roman-numeral franchise labels for fallback resolution.
- CR/HIDIVE exact provider-season candidate titles receive stronger confidence when progress is compatible.
- HIDIVE clipboard authentication instructions retained from v5.
- AniList sync remains read-only in resolve-all.

## MultiSource production sync hardening (2026-09-17)
- Added account-bound, SHA-256-bound AniList plan metadata.
- Added full pre-mutation AniList backup.
- Added pre-write drift detection and abort behavior.
- Added per-entry no-regression revalidation and JSONL mutation audit log.
- UPDATE now preserves existing AniList status/unrelated fields while advancing progress.
- Added post-write remote verification and applied/failure reports.
- Added production sync regression tests; combined suite: 141 tests passing.

## MultiSource v9.1 - verified catalog corrections
- Keeps the v9 production-safe AniList sync engine unchanged.
- Adds narrow, exact provider/AniList catalog corrections for 13 previously blocked Crunchyroll mappings.
- Corrections run after generic resolution, so the frozen resolver scoring is not globally loosened.
- Corrected mappings include Witch Hat Atelier S1, ROLL OVER AND DIE, Jack-of-All-Trades, Smartphone S2, Knight's & Magic, Too-Perfect Saint, Unaware Atelier Meister S1, Solo Leveling S2 cumulative numbering, Magi, Dr. STONE SCIENCE FUTURE Part 3, Code Geass S1, Misfit S2, and Rascal Does Not Dream of Santa Claus.
- Overrides refuse to AUTO-map if progress would exceed the verified AniList episode count.
- Test suite: 146 passed.

## 1.3.0-ms9.5 - MultiSource GUI
- Replaced the legacy Crunchyroll-only Sync screen with a MultiSource AniList workflow.
- Added provider refresh controls, Netflix CSV picker, Resolve & Preview, plan summary, and safe AniList Sync action.
- GUI delegates to the validated `sync-all`/production apply engine; resolver and sync safety logic are unchanged.
- Added `--multisource-cli` forwarding for source and frozen GUI builds.

## 1.3.0-ms9.7 — Integrated MultiSource GUI
- Reorganized navigation into Sync, Crunchyroll, HIDIVE, Netflix, Manual Entry, My Library, Schedule, Export, and Export & Sync Settings.
- Added dedicated provider configuration/instruction pages.
- Added persistent Include in Sync source checkboxes and source-aware resolver filtering.
- Sync My Anime automatically refreshes enabled Crunchyroll/HIDIVE sources before planning.
- HIDIVE supports visible Copy-as-PowerShell paste, local validation/extraction, and clears the raw request box after configuration.
- Netflix uses deliberate Choose CSV → validate/count → Import workflow.
- Manual Entry supports Quick Entry text and Structured Entry independently or merged, with confirmation before append.
- Global status strip now reflects Crunchyroll, HIDIVE, Netflix, Manual, and AniList readiness.
- Renamed Settings navigation to Export & Sync Settings and removed redundant Crunchyroll configuration from that page.

## 1.3.0-ms9.7.2 - GUI setup and sync hotfix
- Fixed `sync-all --fetch-hidive` crash caused by the Click flag shadowing the `fetch_hidive` command function.
- Added first-time Configure instructions for Crunchyroll, HIDIVE, and AniList.
- Added AniList Developer Page and Copy Redirect URL buttons.
- Added explicit AniList Configure/Validate flow using authenticated Viewer lookup.
- AniList status turns green only after the saved token is validated and shows the connected username.
- HIDIVE refresh now uses locally saved configuration without copying credentials back to the OS clipboard.

## 1.3.0-ms9.7.3 - Workflow UX and incremental preview

- Reformatted sync-all output into Crunchyroll, HIDIVE, Resolution, and AniList sections.
- HIDIVE log now reports HIDIVE-specific history instead of the combined store total.
- Renamed the primary action to Preview Sync Changes and clarified the empty-plan prompt.
- Added first-run narrative explaining that initial data-label resolution can take longer.
- Added incremental reuse of previously safe single-entry resolved mappings; review/error/split mappings are still re-resolved.
- Added Cancel Workflow for an active CLI refresh/preview process.
- Added Sync Safe Changes to MAL using safely resolved MAL IDs and non-regressing remote progress checks.
- Added long-running sync note and MAL progress counters.

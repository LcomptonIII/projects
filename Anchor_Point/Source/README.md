# Anchor Point 1.0.0

**Your anime history, connected.**

Anchor Point consolidates viewing history from Crunchyroll, HIDIVE, Netflix imports, and manual entries, resolves titles and seasons, deduplicates progress across sources, and safely synchronizes supported changes to AniList and MyAnimeList.

## Start here

For normal use, build and launch the Windows application, then configure each source from its own tab. The **Sync** page is the dashboard: choose the sources to include, click **Preview Sync Changes**, review the plan, then explicitly choose **Sync Safe Changes to AniList** and/or **Sync Safe Changes to MAL**.

See **USER_GUIDE.md** for first-time setup, source instructions, preview behavior, cancellation, caching, and safe-sync behavior. See **RELEASE_CHECKLIST.md** for final Windows release validation.

## Windows build

Requirements: Windows x64 and Python 3.11 x64.

1. Extract the source ZIP to a new folder.
2. Run `build_windows.bat`.
3. Launch `dist\AnchorPoint.exe` and complete the release validation checklist.
4. Only after the EXE passes, install Inno Setup 6 and run `build_installer.bat`.
5. Test the installed copy, Start Menu/desktop shortcuts, configuration persistence, and uninstall.

The build scripts deliberately use Python 3.11 so another installed Python version does not silently change the packaged runtime.

## Local data and credentials

Configuration, imported history, cached resolutions, backups, and logs remain local to the application data directory. Never distribute a personal `config.yaml`, authentication data, imported viewing-history files, backups, or logs with a public release.

## Safety model

Preview is read-only. Previously safe single-entry mappings can be reused from the local resolution cache, while new or changed items are analyzed. Destination writes remain explicit. Existing remote progress is protected from regression, ambiguous/rejected/blocked items remain quarantined, and destination state is checked before supported mutations. AniList and MAL are independent destinations.

## Project lineage

Anchor Point grew from the open-source CrunchyExporter project by ruflas and retains portions of its upstream architecture. See `UPSTREAM_1_3_INTEGRATION.md` and `LICENSE` for lineage and licensing information.

## GitHub / source-control safety

Do not commit `config.yaml` or the `data/` directory. They can contain local credentials, watch history, resolver caches, checkpoints, sync plans, and account-specific runtime data. Generated `build/`, `dist/`, and `installer/` output is also excluded by `.gitignore`; publish compiled binaries as GitHub Release assets instead. Use `config.example.yaml` as the public configuration template.

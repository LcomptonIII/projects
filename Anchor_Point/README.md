# Anchor Point

**Your anime history, connected.**

Anchor Point is a Windows desktop application for consolidating anime
watch history from multiple streaming services and safely synchronizing
that progress with anime tracking services.

It was built to solve a simple problem: watch history is often scattered
across Crunchyroll, HIDIVE, Netflix, and other services, while tracking
sites such as AniList do not always reflect what you have actually
watched.

Anchor Point brings those histories together, resolves provider-specific
season and episode numbering, and gives you a reviewable sync plan
before anything is written to your anime list.

## Features

-   Import and consolidate watch history from **Crunchyroll**,
    **HIDIVE**, and **Netflix**
-   Add history manually for **Amazon Prime Video** and other sources
-   Resolve provider titles, seasons, split cours, and unusual episode
    numbering to the appropriate anime entries
-   Use the highest credible progress across services rather than
    incorrectly adding episode counts together
-   Preview proposed changes before synchronization
-   Safely synchronize progress with **AniList**
-   Support **MyAnimeList (MAL)** export/sync workflows
-   Preserve ambiguous or potentially unsafe matches for review instead
    of silently updating them
-   Never intentionally reduce existing remote progress
-   Cache resolved titles locally so subsequent analyses are
    substantially faster
-   Resume lengthy first-time resolution runs from checkpoints
-   Preserve previously collected HIDIVE history if live authentication
    expires
-   Provide a native Windows GUI while retaining a CLI for development
    and troubleshooting

## How It Works

Anchor Point follows a review-first workflow:

1.  **Collect** watch history from enabled sources.
2.  **Normalize** provider-specific titles, seasons, and episode
    information.
3.  **Resolve** each anime against AniList/MAL identities.
4.  **Consolidate** duplicate viewing history using the highest credible
    progress.
5.  **Preview** additions, updates, skips, blocked entries, and items
    requiring review.
6.  **Sync** only approved/safe changes to the configured destination.

Anchor Point deliberately favors safety over aggressive matching.
Ambiguous entries are quarantined for review rather than guessed.

## Supported Sources

  Source               Method
  -------------------- -----------------------------
  Crunchyroll          Watch-history integration
  HIDIVE               Watch-history integration
  Netflix              Viewing Activity CSV import
  Amazon Prime Video   Manual entry
  Other services       Manual entry

## Sync Destinations

  Destination   Support
  ------------- ----------------------------------
  AniList       Safe preview and synchronization
  MyAnimeList   Export/synchronization support

## Windows Installation

The recommended installation method is the packaged Windows installer:

`AnchorPoint-1.0.0-Setup.exe`

After installation, launch **Anchor Point** normally from Windows.

For source builds, Python 3.11 is the supported build environment. The
repository includes Windows build scripts and an Inno Setup definition
for creating the distributable installer.

## Building From Source

Clone the repository and open the `Anchor_Point` directory.

Install the Python dependencies:

``` text
py -3.11 -m pip install -r requirements.txt
```

Build the Windows application:

``` text
build_windows.bat
```

The application executable is produced under:

``` text
dist\AnchorPoint.exe
```

To build the Windows installer, install **Inno Setup** and compile
`AnchorPoint.iss`, or use the included installer build script when the
Inno Setup compiler is available.

The resulting installer is configured as:

``` text
installer\AnchorPoint-1.0.0-Setup.exe
```

## Local Data and Privacy

Anchor Point stores configuration and runtime data locally.

Personal files such as the following are intentionally excluded from the
repository:

``` text
config.yaml
data\
startup_error.log
*.log
```

The `data` directory can contain watch history, resolver caches,
checkpoints, sync plans, backups, and other account-specific runtime
information.

**Do not commit your personal `config.yaml` or `data` directory to
GitHub.**

A sanitized `config.example.yaml` is included as a starting point.

### Resolver Cache

Resolved title mappings are cached locally so Anchor Point does not need
to re-identify an entire library on every run.

The primary cache is stored under:

``` text
data\resolved\resolver_cache.json
```

Associated cache metadata and temporary resolution checkpoints are also
stored under `data\resolved\`.

If moving an existing Anchor Point installation, preserve the entire
`data\resolved\` directory if you want to retain previously resolved
mappings.

## Safety Model

Anchor Point's synchronization pipeline is intentionally conservative.

It is designed to:

-   use the maximum credible progress when the same anime appears on
    multiple services
-   avoid summing progress across providers
-   avoid reducing existing AniList/MAL progress
-   preserve ambiguous matches for review
-   block unresolved or stale mappings rather than guessing
-   re-check remote state before production writes
-   create backups and mutation logs around production synchronization
-   keep preview and apply operations distinct

A successful preview does not itself modify your remote anime list.

## Project Structure

``` text
Anchor_Point/
├── gui/                       # Windows GUI and tabs
├── src/                       # Core collection, resolution, sync, and export logic
├── tests/                     # Automated test suite
├── locales/                   # Localization resources
├── main.py                    # Application/CLI entry point
├── config.example.yaml        # Sanitized configuration example
├── requirements.txt           # Python dependencies
├── AnchorPoint.iss            # Inno Setup installer definition
├── build_windows.bat          # Windows application build
├── build_windows_debug.bat    # Diagnostic console build
├── build_installer.bat        # Installer build helper
├── USER_GUIDE.md              # Detailed usage documentation
├── CHANGELOG.md               # Release history
└── LICENSE                    # License information
```

## Documentation

See `USER_GUIDE.md` for detailed configuration and usage instructions.

See `CHANGELOG.md` for release history.

See `UPSTREAM_1_3_INTEGRATION.md` for information about the upstream
CrunchyExporter lineage and integration work.

## Current Release

**Anchor Point 1.0.0**

The 1.0 release includes the multi-source GUI, season-aware resolution,
safe AniList synchronization, MAL support, persistent resolution
caching, resumable checkpointing, and Windows installer support.

## Upstream Project and Attribution

Anchor Point incorporates and extends work originating from
**CrunchyExporter**. Upstream attribution and licensing information are
preserved in this repository.

Please review `LICENSE` and `UPSTREAM_1_3_INTEGRATION.md` for details.

## Disclaimer

Anchor Point is an independent project and is not affiliated with,
endorsed by, or sponsored by Crunchyroll, HIDIVE, Netflix, Amazon,
AniList, or MyAnimeList.

Streaming services and third-party APIs can change their authentication
methods, endpoints, or data formats at any time. Review synchronization
previews before applying changes.

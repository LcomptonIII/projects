# Upstream v1.3.0 Integration

Base: ruflas/CrunchyExporter v1.3.0 (2026-06-29)
Multi-source resolver baseline: v8.2.1

This tree preserves the upstream v1.3.0 GUI/core implementation and layers the
multi-source work on top of it.

## Upstream v1.3.0 behavior retained
- Crunchyroll grouping by series_id + season_number
- AniList/MAL sequel-chain season resolution in the original exporters
- Remote-progress regression protection in the original exporters
- Export preview and confirmation UI
- Manual library title/season/progress overrides stored separately from raw history
- Only-since export filter
- MAL long-title fallback handling
- Persistent export log and v1.1 stability fixes
- GUI version/update infrastructure and v1.3 dependency set

## Multi-source additions retained
- Crunchyroll + HIDIVE history in a source-namespaced shared store
- Netflix ViewingHistory import and anime/non-anime classification
- Manual provider entries (e.g. Prime Video)
- AniList resolver with cumulative episode-number normalization
- Split-cour / sequel allocation
- Cross-provider MAX-progress consolidation (never SUM)
- REVIEW / REJECT / BLOCK safety gates
- Batched AniList plan comparison
- Read-only resolve-all and anilist-plan stages

## Shared-file reconciliation
- src/crunchyroll/models.py: upstream Episode model + source field
- src/storage/history_store.py: upstream season-aware summaries + source-aware IDs/dedupe
- src/main.py: upstream v1.3 CLI retained; multi-source commands appended/integrated
- config.example.yaml: upstream v1.3 settings retained; optional HIDIVE settings added

No AniList write is performed by resolve-all or anilist-plan.

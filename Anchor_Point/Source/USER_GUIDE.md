# Anchor Point User Guide

**Your anime history, connected.**

## 1. First-time setup

Launch Anchor Point and use the source tabs to configure the services you actually use. A source is not ready merely because authentication text was entered: when a page provides a **Configure** button, click it to save and validate that source before the first sync. The top status indicators show which sources/destinations are ready.

### Crunchyroll

Open Crunchyroll and sign in. In the browser developer tools, open **Application → Storage → Cookies → crunchyroll.com**, copy the value of the `etp_rt` cookie, paste it into Anchor Point, and click **Configure Crunchyroll**. Repeat this only if the cookie expires or changes.

### HIDIVE

Open HIDIVE Watch History. In developer tools, open **Network → Fetch/XHR**, refresh, locate the `vod?p=1&rpp=10` request, right-click it, and choose **Copy → Copy as PowerShell**. Paste that copied request into the HIDIVE text box and click **Configure HIDIVE**. Anchor Point extracts the required authentication locally and clears the raw pasted request after configuration. Repeat when HIDIVE authentication expires.

### Netflix

Export/download your Netflix viewing activity CSV. In the Netflix tab choose the CSV, verify the displayed filename/record count, then click **Import Netflix History**. Choosing a file alone does not replace the stored Netflix dataset; import is deliberate.

### Manual Entry

The Manual Entry tab supports two independent inputs. **Quick Entry** accepts human-readable lines such as `Title - Season 2 - Episode 6`. **Structured Entry** provides explicit Title, Season, Episodes Watched, and Source fields. Use the checkboxes to process either input or both; when both are enabled they are merged/appended with duplicate handling.

### AniList and MyAnimeList

Open **Export & Sync Settings**. For AniList, use the provided button to open the AniList developer page and the **Copy Redirect URL** button instead of typing the redirect URL manually. Enter the required values and click **Configure AniList**. AniList turns green only after the saved token successfully validates and Anchor Point can identify the authenticated account.

Configure MyAnimeList in the same settings page if you want MAL synchronization. AniList and MAL are separate destinations; configuring one does not configure the other.

## 2. Preview Sync Changes

On **Sync**, select the source checkboxes you want included. An unchecked source is ignored for that preview/sync but its stored data is not deleted. When enabled and authenticated, Crunchyroll and HIDIVE can refresh on demand before resolution; imported Netflix and Manual Entry data use the locally stored datasets.

Click **Preview Sync Changes**. The preview refreshes selected sources, consolidates history, resolves titles/seasons, deduplicates cross-service progress, and creates the destination plan. It does not write changes to AniList or MAL.

### Why the first preview can take longer

The initial preview of a new library must identify and match existing titles and seasons. This first-time lookup can be substantially slower than later runs. Safe resolved data labels are cached locally, so subsequent previews can reuse known mappings and focus on new or changed data. Normal episode-progress changes on an already known title should not require the title identity to be rediscovered.

The Workflow Log reports source activity and resolution progress. Keep Anchor Point open while a workflow is running.

## 3. Cancel Workflow

While refresh/preview work is active, **Cancel Workflow** requests a graceful stop. Valid mappings already saved remain available, no AniList/MAL writes are performed by a cancelled preview, and the log records the cancellation. Destination writes are handled separately because a remote change that has already completed cannot be automatically undone.

## 4. Review the plan

After preview, review the summary before writing anything. The plan distinguishes new entries, progress updates, already-current entries, review items, rejected matches, and blockers. Review/rejected/blocked items are not silently written.

## 5. Sync safe changes

Use **Sync Safe Changes to AniList** or **Sync Safe Changes to MAL** only after reviewing the preview. Each destination performs its own remote-state checks. Syncing can take time when many entries must be checked or updated; keep Anchor Point open until the Workflow Log reports completion.

AniList synchronization uses the guarded production path, including account validation, remote-state/drift checks, backup/logging, quarantine handling, and post-write verification. MAL safe sync independently checks mapped MAL entries and does not reduce existing MAL episode progress.

## 6. Other tabs

**My Library** lets you inspect the locally consolidated history. **Export** retains the supported export functions. **Schedule** retains the existing scheduling functionality. **Export & Sync Settings** contains destination authentication, export paths, and interface settings.

## Troubleshooting

If a source stays gray, return to that source tab and complete its Configure step. If AniList does not turn green, use **Configure AniList** so Anchor Point can validate the saved token. If Preview is unexpectedly slow after a successful first run, inspect the Resolution section of the Workflow Log to confirm cached mappings are being reused. If a workflow appears stuck, use **Cancel Workflow** rather than closing the application during processing.

## First Preview and resolution time

On a new installation, Anchor Point must match watch-history title/season groups to AniList before it can build a safe sync preview. Large libraries containing hundreds of titles may take several hours during this first analysis. Safe resolver results are checkpointed locally every 20 newly analyzed groups using atomic file replacement. If the analysis is interrupted, the next Preview can reuse the latest valid checkpoint. Anchor Point also reports an estimated remaining time after enough fresh groups have been analyzed. Subsequent previews reuse safe completed mappings and should normally be substantially faster.

## HIDIVE authentication expiration

HIDIVE browser Bearer credentials are short-lived. Anchor Point validates them when a live HIDIVE refresh is requested. If HIDIVE rejects the saved credential, Anchor Point does not erase previously downloaded HIDIVE history and does not report the failed refresh as current. The Workflow Log identifies the authentication problem and, when available, uses the last successful HIDIVE history snapshot for Preview. Reconfigure HIDIVE from the HIDIVE tab to retrieve newer viewing activity.

from datetime import datetime, timezone
from typing import Iterator

import requests

from src.crunchyroll.models import Episode

HIDIVE_HISTORY_URL = "https://dce-frontoffice.imggaming.com/api/v2/customer/history/vod"
DEFAULT_PAGE_SIZE = 25


class HIDIVEHistoryError(RuntimeError):
    pass


class HIDIVEHistory:
    """Fetch HIDIVE account watch history using a browser-issued Bearer token.

    The token is deliberately supplied by the caller rather than persisted here.
    HIDIVE's web token is short-lived, so this is an interim authentication layer;
    history parsing/pagination is isolated so a future automatic auth provider can
    replace token acquisition without changing storage/export code.
    """

    def __init__(self, bearer_token: str, api_key: str = "", app_version: str = "6.60.0.7f55f6c"):
        token = (bearer_token or "").strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if not token:
            raise ValueError("HIDIVE bearer token is required")

        self.session = requests.Session()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Origin": "https://www.hidive.com",
            "Referer": "https://www.hidive.com/",
            "User-Agent": "Mozilla/5.0",
            "app": "dice",
            "realm": "dce.hidive",
            "x-app-var": app_version,
        }
        if api_key:
            headers["x-api-key"] = api_key
        self.session.headers.update(headers)

    def fetch_all(self, page_size: int = DEFAULT_PAGE_SIZE) -> list[Episode]:
        return list(self._paginate(page_size=page_size))

    def _paginate(self, page_size: int = DEFAULT_PAGE_SIZE) -> Iterator[Episode]:
        page = 1
        total_pages = None
        while total_pages is None or page <= total_pages:
            payload = self._fetch_page(page, page_size)
            items = payload.get("vods") or []
            if total_pages is None:
                try:
                    total_pages = int(payload.get("totalPages") or 1)
                except (TypeError, ValueError):
                    total_pages = 1

            for item in items:
                ep = self._parse_item(item)
                if ep:
                    yield ep

            if not items:
                break
            page += 1

    def _fetch_page(self, page: int, page_size: int) -> dict:
        resp = self.session.get(
            HIDIVE_HISTORY_URL,
            params={"p": page, "rpp": page_size},
            timeout=20,
        )
        if resp.status_code in (401, 403):
            raise HIDIVEHistoryError(
                f"HIDIVE authentication failed ({resp.status_code}). "
                "The browser Bearer token may have expired."
            )
        if not resp.ok:
            raise HIDIVEHistoryError(
                f"HIDIVE history fetch failed {resp.status_code}: {resp.text[:500]}"
            )
        try:
            return resp.json()
        except ValueError as exc:
            raise HIDIVEHistoryError("HIDIVE returned a non-JSON history response") from exc

    @staticmethod
    def _parse_item(item: dict) -> Episode | None:
        info = item.get("episodeInformation") or {}
        series = info.get("seriesInformation") or {}
        series_id = str(series.get("id") or "").strip()
        series_title = str(series.get("title") or "").strip()
        episode_id = str(item.get("id") or item.get("externalAssetId") or "").strip()
        if not series_id or not series_title or not episode_id:
            return None

        try:
            season_number = int(info.get("seasonNumber") or 1)
        except (TypeError, ValueError):
            season_number = 1

        try:
            episode_number = float(info.get("episodeNumber") or 0)
        except (TypeError, ValueError):
            episode_number = 0.0

        watched_at = HIDIVEHistory._timestamp_to_iso(item.get("watchedAt"))

        # HIDIVE appears to expose watchProgress as a resume position in seconds.
        # Do not infer completion from its absence/presence until that behavior is
        # formally verified; exporters currently derive progress from watched entries.
        return Episode(
            series_id=series_id,
            series_title=series_title,
            season_number=season_number,
            episode_number=episode_number,
            episode_title=str(item.get("title") or ""),
            episode_id=episode_id,
            watched_at=watched_at,
            fully_watched=False,
            source="hidive",
        )

    @staticmethod
    def _timestamp_to_iso(value) -> str | None:
        if value in (None, ""):
            return None
        try:
            # HIDIVE's watchedAt is Unix milliseconds.
            seconds = float(value) / 1000.0
            return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError, OSError):
            return None

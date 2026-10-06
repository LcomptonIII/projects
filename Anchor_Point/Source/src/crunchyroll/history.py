import requests
from typing import Iterator
from urllib.parse import urljoin
from .models import CRToken, Episode

CR_API_BASE = "https://beta-api.crunchyroll.com"
CR_CONTENT_BASE = f"{CR_API_BASE}/content/v2"
PAGE_SIZE = 100


class CRHistoryFetchError(RuntimeError):
    """History download failed after zero or more episodes were retrieved."""

    def __init__(self, message: str, partial_episodes: list[Episode] | None = None):
        super().__init__(message)
        self.partial_episodes = partial_episodes or []


class CRHistory:
    def __init__(self, token: CRToken):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token.access_token}",
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        })

    def fetch_all(self, locale: str = "en-US") -> list[Episode]:
        episodes: list[Episode] = []
        try:
            for ep in self._paginate(locale):
                episodes.append(ep)
        except Exception as exc:
            if isinstance(exc, CRHistoryFetchError):
                raise
            raise CRHistoryFetchError(str(exc), episodes) from exc
        return episodes

    def _paginate(self, locale: str) -> Iterator[Episode]:
        """Follow Crunchyroll's opaque meta.next_page cursor until exhausted."""
        url = f"{CR_CONTENT_BASE}/{self.token.account_id}/watch-history"
        params: dict[str, object] | None = {
            "page_size": PAGE_SIZE,
            "locale": locale,
        }
        seen_urls: set[str] = set()

        while url:
            request_key = url if params is None else f"{url}?page_size={PAGE_SIZE}&locale={locale}"
            if request_key in seen_urls:
                raise RuntimeError("History fetch stopped: Crunchyroll returned a repeated pagination cursor.")
            seen_urls.add(request_key)

            items, next_page = self._fetch_page(url, params)
            for item in items:
                ep = self._parse_item(item)
                if ep:
                    yield ep

            if not next_page:
                break

            # meta.next_page is an API-relative path including its query string.
            # Treat it as opaque: do not reconstruct page/cursor parameters.
            url = urljoin(CR_API_BASE, next_page)
            params = None

    def _fetch_page(self, url: str, params: dict | None = None) -> tuple[list[dict], str | None]:
        resp = self.session.get(url, params=params, timeout=20)
        if not resp.ok:
            raise RuntimeError(f"History fetch failed {resp.status_code}: {resp.text}")
        payload = resp.json()
        return payload.get("data", []), (payload.get("meta") or {}).get("next_page")

    def _parse_item(self, item: dict) -> Episode | None:
        panel = item.get("panel", {})
        if not panel:
            return None

        ep_meta = panel.get("episode_metadata", {})
        series_id = ep_meta.get("series_id") or panel.get("id", "")
        series_title = ep_meta.get("series_title") or panel.get("title", "unknown")

        try:
            season_number = int(ep_meta.get("season_number") or 1)
        except (ValueError, TypeError):
            season_number = 1

        try:
            episode_number = float(ep_meta.get("episode_number") or 0)
        except (ValueError, TypeError):
            episode_number = 0.0

        return Episode(
            series_id=series_id,
            series_title=series_title,
            season_number=season_number,
            episode_number=episode_number,
            episode_title=panel.get("title", ""),
            episode_id=panel.get("id", ""),
            watched_at=item.get("date_played"),
            fully_watched=item.get("fully_watched", False),
        )

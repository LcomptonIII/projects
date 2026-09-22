#!/usr/bin/env python3
import sys
import os
import yaml
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crunchyroll.auth import CRAuth, CRAuthError, DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET
from src.crunchyroll.history import CRHistory
from src.storage.history_store import HistoryStore
from src.exporters.anilist import AniListExporter
from src.exporters.mal import MALExporter, get_auth_url as mal_auth_url, exchange_code as mal_exchange
from src.exporters.mal_xml import MALXMLExporter

console = Console()


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _config_dir(ctx) -> Path:
    """Directory containing the active config file, always absolute."""
    return Path(ctx.obj.get("config_path") or "config.yaml").expanduser().resolve().parent


def _resolve_config_path(ctx, value: str | Path) -> Path:
    """Resolve user-configured relative paths against the config directory, never CWD."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else (_config_dir(ctx) / p).resolve()


def _history_path(ctx) -> Path:
    value = ctx.obj["config"].get("storage", {}).get("path", "data/history.json")
    return _resolve_config_path(ctx, value)


def _data_dir(ctx) -> Path:
    """Authoritative writable data directory for all source/resolver artifacts."""
    return _history_path(ctx).parent


def _resolved_dir(ctx) -> Path:
    return _data_dir(ctx) / "resolved"


def _artifact_path(ctx, name: str) -> Path:
    return _data_dir(ctx) / name


RESOLUTION_CACHE_SCHEMA = "anchorpoint-resolver-cache-v1"


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--config", "-c", default="config.yaml", show_default=True, help="Path to config file.")
@click.pass_context
def cli(ctx, config):
    ctx.ensure_object(dict)
    config_path = Path(config).expanduser().resolve()
    if config_path.exists():
        ctx.obj["config"] = load_config(str(config_path))
    else:
        ctx.obj["config"] = {}
    ctx.obj["config_path"] = str(config_path)


@cli.command()
@click.option("--etp-rt", default=None, help="Value of the etp_rt cookie from your browser session. Can also be set in config.yaml under crunchyroll.etp_rt.")
@click.option("--replace", is_flag=True, default=False, help="Replace ALL existing local history instead of merging (incremental by default).")
@click.pass_context
def fetch(ctx, etp_rt, replace):
    """Fetch your Crunchyroll watch history and save it locally as JSON.

    \b
    HOW TO GET THE etp_rt COOKIE:
      1. Log into crunchyroll.com in your browser
      2. Open DevTools (F12) -> Application tab -> Cookies -> https://www.crunchyroll.com
      3. Copy the value of the 'etp_rt' cookie

    \b
    EXAMPLES:
      python src/main.py fetch --etp-rt "your-cookie-value"
      python src/main.py fetch                   (reads etp_rt from config.yaml)
      python src/main.py fetch --replace         (full resync, discards local cache)
    """
    cfg = ctx.obj["config"]
    store_path = str(_history_path(ctx))

    cr_cfg = cfg.get("crunchyroll", {})
    etp_rt = etp_rt or cr_cfg.get("etp_rt") or ""
    if not etp_rt:
        etp_rt = click.prompt("etp_rt cookie value", hide_input=True)

    auth = CRAuth(
        client_id=cr_cfg.get("client_id") or DEFAULT_CLIENT_ID,
        client_secret=cr_cfg.get("client_secret") or DEFAULT_CLIENT_SECRET,
    )

    with console.status("[bold green]Logging in to Crunchyroll..."):
        try:
            token = auth.login_with_etp_rt(etp_rt)
        except CRAuthError as e:
            console.print(f"[red]Authentication failed:[/red] {e}")
            raise SystemExit(1)

    console.print(f"[green]Logged in.[/green] Account ID: {token.account_id}")

    with console.status("[bold green]Fetching watch history..."):
        history = CRHistory(token)
        episodes = history.fetch_all(locale=cfg.get("locale", "en-US"))

    store = HistoryStore(Path(store_path))
    if replace:
        store.replace(episodes)
        console.print(f"[green]Saved {len(episodes)} episodes[/green] to {store_path} (replaced).")
    else:
        added = store.update(episodes)
        console.print(
            f"[green]Sync complete.[/green] {added} new episodes added. "
            f"Total: {len(store)} episodes across {len(store.series_summaries())} series."
        )


@cli.command(name="fetch-hidive")
@click.option("--token", default=None, help="HIDIVE Bearer token from your own browser session. Prefer HIDIVE_TOKEN env var or an interactive prompt.")
@click.option("--api-key", default=None, help="HIDIVE web application API key. Can also be set under hidive.api_key.")
@click.option("--replace-hidive", is_flag=True, default=False, help="Replace only previously stored HIDIVE episodes; preserve Crunchyroll history.")
@click.pass_context
def fetch_hidive(ctx, token, api_key, replace_hidive):
    """Fetch HIDIVE watch history and merge it into the same local history store.

    Authentication is intentionally local: pass a current browser-issued Bearer
    token via HIDIVE_TOKEN or enter it at the hidden prompt. The token is never
    written to history.json. HIDIVE web tokens are short-lived.
    """
    from src.hidive.history import HIDIVEHistory, HIDIVEHistoryError

    cfg = ctx.obj["config"]
    store_path = str(_history_path(ctx))
    hd_cfg = cfg.get("hidive", {})
    token = token or os.environ.get("HIDIVE_TOKEN") or hd_cfg.get("bearer_token") or ""
    api_key = api_key or os.environ.get("HIDIVE_API_KEY") or hd_cfg.get("api_key") or ""
    if not token:
        # Windows-friendly clipboard workflow: copy the Bearer token in DevTools,
        # then run fetch-hidive. This avoids pasting into getpass/PowerShell.
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            clipboard = root.clipboard_get().strip()
            # Remove copied browser credentials from the OS clipboard as soon
            # as they have been captured in memory. They are never persisted.
            root.clipboard_clear()
            root.update()
            root.destroy()

            # Accept either a bare JWT/Bearer value OR Chrome's copied request
            # headers. The latter is preferred because HIDIVE also requires the
            # web application's x-api-key. Credentials remain local.
            import re
            # Support raw headers, Chrome "Copy as PowerShell", or a bare JWT.
            raw_auth = re.search(r"(?im)^\s*authorization\s*:\s*Bearer\s+([^\r\n]+)", clipboard)
            raw_key = re.search(r"(?im)^\s*x-api-key\s*:\s*([^\r\n]+)", clipboard)
            ps_auth = re.search(r'(?is)["\']?authorization["\']?\s*=\s*["\']Bearer\s+([^"\'\r\n;]+)["\']', clipboard)
            ps_key = re.search(r'(?is)["\']?x-api-key["\']?\s*=\s*["\']([^"\'\r\n;]+)["\']', clipboard)
            ps_app_var = re.search(r'(?is)["\']?x-app-var["\']?\s*=\s*["\']([^"\'\r\n;]+)["\']', clipboard)

            auth_match = raw_auth or ps_auth
            key_match = raw_key or ps_key
            if auth_match:
                token = auth_match.group(1).strip().strip("\"\'")
                if not api_key and key_match:
                    api_key = key_match.group(1).strip().strip("\"\'")
                if ps_app_var and not hd_cfg.get("app_version"):
                    hd_cfg = dict(hd_cfg)
                    hd_cfg["app_version"] = ps_app_var.group(1).strip().strip("\"\'")
                if ps_auth:
                    console.print("[green]HIDIVE credentials read from Chrome Copy as PowerShell.[/green]")
                else:
                    console.print("[green]HIDIVE authorization headers read from Windows clipboard.[/green]")
            else:
                candidate = clipboard.strip()
                if candidate.lower().startswith("bearer "):
                    candidate = candidate[7:].strip()
                if candidate.startswith("eyJ") and candidate.count(".") == 2 and "\n" not in candidate:
                    token = candidate
                    console.print("[green]HIDIVE token read from Windows clipboard.[/green]")
                else:
                    token = ""
        except Exception:
            token = ""

    if not token:
        ctx.obj["hidive_fetch_error"] = "HIDIVE authentication is not configured."
        console.print("[yellow]No HIDIVE authentication found.[/yellow]")
        console.print("\nTo connect HIDIVE:")
        console.print("  1. Log in to HIDIVE and open Watch History.")
        console.print("  2. Press F12 to open Chrome Developer Tools.")
        console.print("  3. Select Network, then the Fetch/XHR filter.")
        console.print("  4. Refresh the HIDIVE Watch History page.")
        console.print("  5. Find [bold]vod?p=1&rpp=10[/bold].")
        console.print("  6. Right-click it -> Copy -> Copy as PowerShell.")
        console.print("  7. Leave that request on your clipboard and run this command again:")
        console.print("     [bold]python src/main.py fetch-hidive[/bold]")
        console.print("\nQuick path:")
        console.print("HIDIVE -> Watch History -> F12 -> Network -> Fetch/XHR -> Refresh ->")
        console.print("vod?p=1&rpp=10 -> Right-click -> Copy -> Copy as PowerShell")
        console.print("\n[red]Do not paste or share the copied request.[/red] Anchor Point reads it locally and clears the clipboard after capture.")
        raise SystemExit(1)

    with console.status("[bold green]Fetching HIDIVE watch history..."):
        try:
            episodes = HIDIVEHistory(
                token,
                api_key=api_key,
                app_version=hd_cfg.get("app_version") or "6.60.0.7f55f6c",
            ).fetch_all()
        except (HIDIVEHistoryError, ValueError) as e:
            ctx.obj["hidive_fetch_error"] = str(e)
            console.print(f"[red]HIDIVE fetch failed:[/red] {e}")
            raise SystemExit(1)

    store = HistoryStore(Path(store_path))
    if replace_hidive:
        # Preserve every other provider while refreshing HIDIVE atomically.
        others = [ep for ep in store.all_episodes() if ep.source != "hidive"]
        store.replace(others + episodes)
        console.print(f"[green]HIDIVE refresh complete.[/green] {len(episodes)} episodes stored.")
    else:
        added = store.update(episodes)
        hidive_eps = [ep for ep in store.all_episodes() if getattr(ep, "source", "") == "hidive"]
        hidive_series = {getattr(ep, "series_id", "") for ep in hidive_eps}
        console.print(
            f"[green]Sync complete.[/green] {added} new HIDIVE episodes added. "
            f"HIDIVE history: {len(hidive_eps)} episodes across {len(hidive_series)} series."
        )


@cli.command()
@click.pass_context
def status(ctx):
    """Show a summary of locally stored watch history.

    \b
    Displays a table with each series, number of episodes watched,
    and the highest episode number seen. Run 'fetch' first.
    """
    cfg = ctx.obj["config"]
    store_path = str(_history_path(ctx))
    store = HistoryStore(Path(store_path))

    if len(store) == 0:
        console.print("[yellow]No history found. Run [bold]fetch[/bold] first.[/yellow]")
        return

    table = Table(title="Watch History Summary", show_lines=True)
    table.add_column("Series", style="cyan", no_wrap=False)
    table.add_column("Episodes watched", justify="right")
    table.add_column("Max episode", justify="right")

    for s in sorted(store.series_summaries(), key=lambda x: x.series_title):
        table.add_row(s.series_title, str(s.total_watched), str(s.max_episode))

    console.print(table)
    console.print(f"\nLast sync: {store.last_sync or 'never'}")


@cli.command()
@click.option("--target", "-t",
              type=click.Choice(["anilist", "mal", "xml", "all"]),
              default="all", show_default=True,
              help="Where to export: anilist, mal, xml (local file), or all three at once.")
@click.pass_context
def export(ctx, target):
    """Export watch history to AniList, MyAnimeList and/or a local XML file.

    \b
    TARGETS:
      anilist   Updates your AniList anime list via API (requires token in config.yaml)
      mal       Updates your MyAnimeList via API (requires OAuth setup in config.yaml)
      xml       Generates data/animelist.xml, importable at myanimelist.net/import.php
      all       Runs all three targets (default)

    \b
    FIRST-TIME SETUP:
      AniList:  Create app at anilist.co/settings/developer, then run with --target anilist
                and follow the printed instructions to get your access token.
      MAL:      Create app at myanimelist.net/apiconfig, add client_id to config.yaml,
                then run with --target mal and follow the OAuth flow.
      XML:      No setup needed, works out of the box.

    \b
    EXAMPLES:
      python src/main.py export                    (export to all targets)
      python src/main.py export --target xml       (local XML only, no auth needed)
      python src/main.py export --target anilist   (AniList only)
    """
    cfg = ctx.obj["config"]
    store_path = str(_history_path(ctx))
    store = HistoryStore(Path(store_path))

    if len(store) == 0:
        console.print("[yellow]No history to export. Run [bold]fetch[/bold] first.[/yellow]")
        return

    summaries = store.series_summaries()
    console.print(f"Exporting {len(summaries)} series...")

    if target in ("xml", "all"):
        _export_xml(ctx, summaries)

    if target in ("anilist", "all"):
        _export_anilist(cfg, summaries)

    if target in ("mal", "all"):
        _export_mal(cfg, summaries)


def _export_xml(ctx, summaries):
    cfg = ctx.obj["config"]
    xml_path = _resolve_config_path(ctx, cfg.get("exporters", {}).get("mal_xml", {}).get("path", "data/animelist.xml"))
    with console.status("[bold]Generating MAL XML..."):
        result = MALXMLExporter(xml_path).export(summaries)
    console.print(f"[green]XML exported:[/green] {xml_path} ({len(result.updated)} series)")


def _export_anilist(cfg: dict, summaries):
    al_cfg = cfg.get("exporters", {}).get("anilist", {})
    token = al_cfg.get("access_token")
    if not token:
        client_id = al_cfg.get("client_id", "")
        url = AniListExporter.get_auth_url(client_id)
        console.print(f"\n[yellow]AniList:[/yellow] No access token found.")
        console.print(f"1. Open this URL to get your token:\n   [link]{url}[/link]")
        console.print("2. After authorizing, copy the [bold]access_token[/bold] from the redirect URL.")
        console.print("3. Add it to config.yaml under [bold]exporters.anilist.access_token[/bold].")
        return

    with console.status("[bold]Exporting to AniList..."):
        result = AniListExporter(token).export(summaries)
    _print_result("AniList", result)


def _export_mal(cfg: dict, summaries):
    mal_cfg = cfg.get("exporters", {}).get("mal", {})
    token = mal_cfg.get("access_token")
    if not token:
        client_id = mal_cfg.get("client_id", "")
        client_secret = mal_cfg.get("client_secret", "")
        if not client_id:
            console.print("[yellow]MAL:[/yellow] Set [bold]exporters.mal.client_id[/bold] in config.yaml first.")
            return
        url, verifier = mal_auth_url(client_id)
        console.print(f"\n[yellow]MAL OAuth:[/yellow] Open this URL to authorize:\n  {url}")
        console.print("After authorizing, MAL redirects to http://localhost/?code=XXXX")
        console.print("The page won't load - that's normal. Copy the [bold]code=[/bold] value from the URL bar.")
        code = click.prompt("Paste the authorization code")
        with console.status("Exchanging code for token..."):
            token = mal_exchange(client_id, code, verifier, client_secret)
        console.print(f"[green]Token obtained.[/green] Save it in config.yaml under exporters.mal.access_token")

    with console.status("[bold]Exporting to MyAnimeList..."):
        result = MALExporter(token).export(summaries)
    _print_result("MyAnimeList", result)


def _print_result(name: str, result):
    console.print(f"\n[bold]{name}[/bold] - {len(result.updated)} updated, "
                  f"{len(result.skipped)} skipped, {len(result.failed)} failed")
    for title, reason in result.failed:
        console.print(f"  [red]FAIL[/red] {title}: {reason}")


@cli.command()
@click.option("--target", "-t",
              type=click.Choice(["anilist", "mal", "xml", "all"]),
              default="all", show_default=True,
              help="Export targets to include in the sync.")
@click.pass_context
def sync(ctx, target):
    """Fetch new history from Crunchyroll then export in one step.

    \b
    Requires etp_rt set in config.yaml (unattended use, no prompts).
    Intended for scheduled/automated runs.

    \b
    EXAMPLES:
      python src/main.py sync
      python src/main.py sync --target anilist
    """
    cfg = ctx.obj["config"]
    cr_cfg = cfg.get("crunchyroll", {})
    etp_rt = cr_cfg.get("etp_rt", "")
    if not etp_rt:
        console.print("[red]sync requires etp_rt set in config.yaml[/red]")
        raise SystemExit(1)

    ctx.invoke(fetch, etp_rt=etp_rt, replace=False)
    ctx.invoke(export, target=target)


@cli.command()
@click.option("--time", "run_at", default="08:00", show_default=True,
              help="Time to run daily in HH:MM format.")
@click.option("--target", "-t",
              type=click.Choice(["anilist", "mal", "xml", "all"]),
              default="all", show_default=True,
              help="Export targets.")
@click.option("--remove", is_flag=True, default=False,
              help="Remove the scheduled task instead of creating it.")
@click.pass_context
def schedule(ctx, run_at, target, remove):
    """Register a daily auto-sync task in Windows Task Scheduler or cron.

    \b
    Requires etp_rt set in config.yaml before scheduling.

    \b
    EXAMPLES:
      python src/main.py schedule                      (daily at 08:00)
      python src/main.py schedule --time 20:00         (daily at 20:00)
      python src/main.py schedule --remove             (delete the task)
    """
    import sys
    import platform
    import subprocess
    from pathlib import Path

    task_name = "AnchorPoint"
    project_dir = Path(__file__).parent.parent.resolve()
    python = sys.executable
    config_path = ctx.obj.get("config_path", "config.yaml")
    cmd = f'"{python}" "{project_dir / "src" / "main.py"}" -c "{config_path}" sync --target {target}'

    if platform.system() == "Windows":
        _schedule_windows(task_name, cmd, run_at, remove)
    else:
        _schedule_cron(cmd, run_at, remove)


def _schedule_windows(task_name: str, cmd: str, run_at: str, remove: bool):
    from src.scheduler import create_schedule, remove_schedule
    ok, msg = remove_schedule(task_name) if remove else create_schedule(task_name, cmd, run_at)
    if ok:
        console.print(f"[green]{'Removed' if remove else 'Scheduled'}:[/green] {task_name}" + ("" if remove else f" daily at {run_at}."))
    else:
        console.print(f"[red]Scheduling failed:[/red] {msg}")


def _schedule_cron(cmd: str, run_at: str, remove: bool):
    from src.scheduler import create_schedule, remove_schedule
    task_name = "AnchorPoint"
    ok, msg = remove_schedule(task_name) if remove else create_schedule(task_name, cmd, run_at)
    if ok:
        console.print(f"[green]{'Removed' if remove else 'Scheduled'}:[/green] {task_name}" + ("" if remove else f" daily at {run_at}."))
    else:
        console.print(f"[red]Scheduling failed:[/red] {msg}")



@cli.command(name="merge-history")
@click.argument("history_file", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def merge_history(ctx, history_file):
    """Merge another Anchor Point/CrunchyExporter-compatible history.json into the active local store."""
    import json
    from src.crunchyroll.models import Episode
    cfg=ctx.obj["config"]; store_path=str(_history_path(ctx))
    raw=json.loads(Path(history_file).read_text(encoding="utf-8"))
    episodes=[Episode.from_dict(x) for x in raw.get("episodes",[])]
    store=HistoryStore(Path(store_path)); added=store.update(episodes)
    console.print(f"[green]Merged history.[/green] {added} new records; {len(store)} total.")

@cli.command(name="import-netflix")
@click.argument("csv_file", type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def import_netflix(ctx, csv_file):
    """Import Netflix ViewingActivity CSV as a raw source for AniList resolution."""
    from src.importers.netflix import save_netflix_json
    n=save_netflix_json(csv_file, str(_artifact_path(ctx, "netflix_history.json")))
    console.print(f"[green]Imported {n} Netflix viewing rows.[/green] Anime classification happens during resolve-all.")

@cli.command(name="add-manual")
@click.argument("title")
@click.option("--season", type=int, default=1, show_default=True)
@click.option("--progress", type=int, default=None)
@click.option("--source", default="amazon", show_default=True)
@click.pass_context
def add_manual_cmd(ctx, title, season, progress, source):
    """Add/replace a manual streaming entry (useful for Prime Video)."""
    from src.importers.manual import add_manual
    e=add_manual(str(_artifact_path(ctx, "manual_history.json")),title,season,progress,source)
    console.print(f"[green]Saved manual entry:[/green] {e['title']} season {e['season']}")

@cli.command(name="resolve-all")
@click.option("--sources", default="all", help="Comma-separated sources to include: crunchyroll,hidive,netflix,manual or all.")
@click.pass_context
def resolve_all(ctx, sources):
    """Resolve all imported providers against AniList. READ-ONLY; never changes AniList."""
    import csv,json,time,os
    from collections import defaultdict
    from src.resolver.anilist import AniListResolver, sim, titles
    from src.importers.netflix import series_candidates
    cfg=ctx.obj["config"]; store=HistoryStore(Path(str(_history_path(ctx))))
    enabled={"crunchyroll","hidive","netflix","manual"} if sources=="all" else {x.strip().lower() for x in sources.split(",") if x.strip()}
    groups=[]
    for s in store.series_summaries():
        src="crunchyroll"
        if s.series_id.startswith("hidive::"): src="hidive"
        if src not in enabled: continue
        from src.resolver.franchise import episode_profile
        prof=episode_profile(s.episodes_watched)
        groups.append({"source":src,"title":s.series_title,"season":s.season_number,
                       "progress":prof["local_progress"],"raw_progress":prof["raw_progress"],
                       "min_episode":prof["min_episode"],"records":s.total_watched})

    # Netflix is normalized BEFORE AniList resolution. Raw episode labels are
    # grouped into series/season buckets rather than becoming hundreds of fake series.
    np=_artifact_path(ctx, "netflix_history.json")
    if "netflix" in enabled and np.exists():
        nd=json.loads(np.read_text(encoding="utf-8")); ng=defaultdict(list)
        for v in nd.get("views",[]):
            title=v.get("series_title") or (v.get("candidates") or [v.get("raw_title")])[0]
            season=int(v.get("season") or 1)
            ng[(title,season)].append(v)
        for (title,season),views in ng.items():
            # Unique raw labels are the best progress proxy Netflix gives us.
            variants=[]
            for v in views:
                for q in (v.get("candidates") or series_candidates(v.get("raw_title") or title)):
                    if q and q not in variants: variants.append(q)
            for q in series_candidates(title):
                if q and q not in variants: variants.append(q)
            groups.append({"source":"netflix","title":title,"season":season,
                           "progress":len({v.get('raw_title') for v in views}),"records":len(views),
                           "queries":variants})

    mp=_artifact_path(ctx, "manual_history.json")
    if "manual" in enabled and mp.exists():
        for e in json.loads(mp.read_text(encoding="utf-8")).get("entries",[]):
            groups.append({"source":e.get("source","manual"),"title":e["title"],"season":e.get("season",1),"progress":e.get("progress") or 0,"records":1})

    from src.resolver.franchise import norm as franchise_norm, split_overflow
    al=AniListResolver(str(_artifact_path(ctx, "anilist_resolver_cache.json")))

    # Incremental resolution cache: mapping.csv is the durable identity cache for
    # this installation. Reuse only previously-safe single-entry AUTO decisions
    # (or stable exclusions). REVIEW/ERROR and split/cour rows are deliberately
    # re-resolved. Progress may advance without changing title identity as long as
    # it still fits the already-mapped AniList entry.
    previous = {}
    previous_path = _resolved_dir(ctx) / "mapping.csv"
    checkpoint_path = _resolved_dir(ctx) / "resolution_checkpoint.csv"
    cache_meta_path = _resolved_dir(ctx) / "cache_meta.json"
    cache_compatible = True
    if cache_meta_path.exists():
        try:
            cache_meta = json.loads(cache_meta_path.read_text(encoding="utf-8"))
            cache_compatible = cache_meta.get("schema") == RESOLUTION_CACHE_SCHEMA
        except Exception:
            cache_compatible = False
    # RC1 and earlier had no cache metadata. That legacy cache is compatible with
    # this RC2 resolver, so adopt it once rather than forcing a costly full re-resolve.
    # Load the completed durable cache plus any interrupted-run checkpoint.
    # Checkpoints contain only locally generated resolver output and are subject
    # to the same conservative reuse rules as the completed mapping.
    for prior_file in (previous_path, checkpoint_path):
        if prior_file.exists() and cache_compatible:
            try:
                with open(prior_file, newline="", encoding="utf-8-sig") as pf:
                    rows=list(csv.DictReader(pf))
                bucket=defaultdict(list)
                for r in rows:
                    k=(r.get("source",""), franchise_norm(r.get("title","")), str(r.get("season") or 1))
                    bucket[k].append(r)
                # Process mapping first and checkpoint second. A safe single-row
                # checkpoint is newer and therefore replaces the completed-cache
                # copy for that identity. Multi-row split mappings are not reused.
                for k, grouped in bucket.items():
                    if len(grouped)==1 and grouped[0].get("decision") in {"AUTO","NOT_ANIME","EXCLUDED_BONUS"}:
                        previous[k]=grouped[0]
            except Exception:
                pass
    out=[]
    reused=0

    # Give immediate feedback before the potentially long resolver loop. A clean
    # install legitimately has no durable identity cache and may need to query
    # AniList for every group; established installations should reuse most safe
    # mappings. Keep this output ASCII-only for Windows CP1252 compatibility.
    reusable_estimate = 0
    for g in groups:
        cache_key=(g.get("source",""), franchise_norm(g.get("title","")), str(g.get("season") or 1))
        prior=previous.get(cache_key)
        if not prior:
            continue
        decision=prior.get("decision")
        total=int(float(prior.get("anilist_episodes") or 0)) if prior.get("anilist_episodes") else 0
        reason=prior.get("reason") or ""
        if decision in {"NOT_ANIME","EXCLUDED_BONUS"} or (decision=="AUTO" and "split across" not in reason and (not total or int(g.get("progress") or 0)<=total)):
            reusable_estimate += 1

    fresh_required=max(0, len(groups)-reusable_estimate)
    console.print(f"Analyzing {len(groups)} history groups...")
    if reusable_estimate:
        if checkpoint_path.exists():
            console.print(f"Previous resolution checkpoint found. Up to {reusable_estimate} safe matches can be reused.")
        else:
            console.print(f"Saved resolutions available for reuse: {reusable_estimate}")
        console.print(f"New or changed groups requiring analysis: {fresh_required}")
    elif groups:
        console.print("First-time analysis detected.")
        console.print("Anchor Point is matching your watch history to AniList.")
        console.print("Large libraries may take several hours on the first analysis.")
        console.print("Safe matches are checkpointed every 20 newly analyzed groups.")
        console.print("If interrupted, the next Preview can reuse the latest checkpoint.")
    console.print("")

    # Checkpoints are written atomically: write a complete temporary CSV, flush
    # it to disk, then replace the previous checkpoint in one filesystem step.
    cols=["source","title","season","progress","raw_progress","min_episode","records","decision","score","margin","anilist_id","mal_id","anilist_title","anilist_episodes","reason","alternatives"]
    def save_checkpoint(rows):
        od=_resolved_dir(ctx); od.mkdir(parents=True,exist_ok=True)
        tmp=checkpoint_path.with_suffix(".tmp")
        with open(tmp,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, checkpoint_path)

    fresh_done=0
    started=time.monotonic()
    netflix_known_non_anime={"fate the winx saga","ex machina","maniac limited series","supergirl","lost girl"}
    provider_bonus={"cast commentary"}
    last_checkpoint=0
    for i,g in enumerate(groups,1):
        # A prior iteration may have crossed a checkpoint boundary via an early
        # continue. Persist it before starting the next group.
        if fresh_done and fresh_done % 20 == 0 and fresh_done != last_checkpoint:
            save_checkpoint(out)
            last_checkpoint=fresh_done
            elapsed=max(0.001,time.monotonic()-started)
            rate=elapsed/fresh_done
            remaining=max(0,fresh_required-fresh_done)
            eta=rate*remaining
            def fmt_duration(seconds):
                minutes=max(0,int(round(seconds/60)))
                if minutes < 5: return "less than 5 min"
                if minutes < 60: return f"~{minutes} min"
                h,m=divmod(minutes,60)
                return f"~{h} hr {m} min" if m else f"~{h} hr"
            console.print(f"Checkpoint saved: {fresh_done}/{fresh_required} newly analyzed groups. Estimated remaining: {fmt_duration(eta)}")
        try:
            nt=franchise_norm(g["title"])
            cache_key=(g.get("source",""), nt, str(g.get("season") or 1))
            prior=previous.get(cache_key)
            if prior:
                decision=prior.get("decision")
                total=int(float(prior.get("anilist_episodes") or 0)) if prior.get("anilist_episodes") else 0
                reason=prior.get("reason") or ""
                if decision in {"NOT_ANIME","EXCLUDED_BONUS"} or (decision=="AUTO" and "split across" not in reason and (not total or int(g.get("progress") or 0)<=total)):
                    row={**prior, **g}
                    row["decision"]=decision
                    row["reason"]=(reason + "; identity match reused").strip("; ")
                    out.append(row); reused+=1
                    continue
            fresh_done += 1
            if g["source"]=="netflix" and (nt in netflix_known_non_anime or nt.startswith("episode ") or nt==""):
                out.append({**g,"decision":"NOT_ANIME","reason":"Mixed Netflix history: known non-anime/malformed provider title"}); continue
            if g["source"] in {"crunchyroll","hidive"} and nt in provider_bonus:
                out.append({**g,"decision":"EXCLUDED_BONUS","reason":"Provider bonus/commentary material"}); continue
            matched_query=g["title"]
            season_correction_verified=False
            if g["source"]=="netflix":
                rawcand=al.candidates_any(g.get("queries") or series_candidates(g["title"]),g["progress"])
                cand=[(x[0],x[1],x[2]) for x in rawcand]
                if rawcand: matched_query=rawcand[0][3]
                # Netflix provides explicit season metadata separately from the
                # normalized series title.  Within an already strongly matched
                # franchise, prefer an AniList candidate carrying that exact
                # structural season label.  This prevents e.g. Season 2/3 from
                # collapsing onto an unlabeled Season 1 entry while retaining
                # the conservative behavior for split-cour/non-literal seasons.
                if cand:
                    from src.resolver.franchise import targeted_season_correction
                    cand,season_correction_verified=targeted_season_correction(
                        g["title"],g.get("season",1),cand
                    )
            else:
                cand=al.candidates(g["title"],g["progress"])
                # v8.1 hybrid: preserve v7.4 coverage, but use provider metadata to
                # re-rank candidates when it supplies positive evidence. Unlike v8,
                # ambiguity never turns an otherwise valid v7.4 candidate into REVIEW.
                # This is deliberately asymmetric: protection may improve a choice,
                # but cannot suppress an ordinary sequel merely because related media exist.
                if cand:
                    from src.resolver.franchise import hybrid_rerank, targeted_season_correction
                    cand=hybrid_rerank(g["title"], g.get("season",1), g.get("progress",0), g.get("records",0), cand)
                    # v8.2.1: a post-resolution correction may reorder only on
                    # positive structural season evidence. It never demotes a
                    # valid v8.2 mapping or creates a new ambiguity state.
                    if g["source"]=="crunchyroll":
                        cand,season_correction_verified=targeted_season_correction(g["title"],g.get("season",1),cand)
            # Netflix is a mixed movie/TV history. No AniList ANIME candidate is
            # an exclusion, not a manual-review task. It remains in mapping.csv
            # and excluded.csv so the decision is fully reversible/auditable.
            if not cand:
                decision="NOT_ANIME" if g["source"]=="netflix" else "REVIEW"
                out.append({**g,"decision":decision,"reason":"No AniList anime candidate"}); continue

            score,m,ts=cand[0]
            second=cand[1][0] if len(cand)>1 else -999; margin=score-second
            overflow=bool(m.get("episodes") and g["progress"] and g["progress"]>m["episodes"])

            # If progress overflows the top result, prefer a closely titled related
            # entry that can contain that progress. This addresses provider season/
            # cour layouts without blindly assuming Season N == Nth AniList sequel.
            if overflow:
                viable=[]
                for c in cand[1:]:
                    cs,cm,cts=c
                    if cm.get("episodes") and g["progress"]<=cm["episodes"] and cts>=max(.72,ts-.15):
                        viable.append(c)
                if viable:
                    viable.sort(key=lambda x:(x[2],x[0]),reverse=True)
                    score,m,ts=viable[0]
                    second=max([x[0] for x in cand if x[1].get("id")!=m.get("id")] or [-999])
                    margin=score-second
                    overflow=False

            # A provider bucket beginning at episode 1 may genuinely span multiple
            # AniList cours/parts. Split only across explicit SEQUEL edges and only
            # when the complete progress can be represented without specials.
            if overflow and g["source"] in {"crunchyroll","hidive"} and int(g.get("min_episode") or 0)<=1:
                pool=[x[1] for x in cand]
                split=split_overflow(m,pool,g["progress"])
                if split:
                    for sm,sp in split:
                        st=(sm.get("title") or {}).get("english") or (sm.get("title") or {}).get("romaji")
                        out.append({**g,"progress":sp,"decision":"AUTO","score":score,"margin":round(margin,2),
                                    "anilist_id":sm.get("id"),"mal_id":sm.get("idMal"),"anilist_title":st,
                                    "anilist_episodes":sm.get("episodes"),"reason":"split across AniList sequel/cour chain",
                                    "alternatives":""})
                    continue

            # Netflix title normalization makes exact/near-exact series matches
            # meaningful. CR/HIDIVE retain conservative overflow protection.
            if g["source"]=="netflix":
                # Positive identification: an arbitrary fuzzy AniList search hit is
                # not evidence that a mixed Netflix title is anime. Require a very
                # strong match to one of the progressively-normalized Netflix labels.
                # An exact structural season correction is positive anime
                # identity evidence only after targeted_season_correction has
                # established a strong title-family match.  Its direct title
                # similarity can be lower simply because AniList appends
                # "Season N" while Netflix stores season separately.
                positive = ts>=.94 or season_correction_verified
                if not positive:
                    out.append({**g,"decision":"NOT_ANIME","score":score,"margin":round(margin,2),
                                "anilist_id":m.get("id"),"mal_id":m.get("idMal"),
                                "anilist_title":(m.get("title") or {}).get("english") or (m.get("title") or {}).get("romaji"),
                                "anilist_episodes":m.get("episodes"),"reason":"No strong AniList anime title match",
                                "alternatives":""}); continue
                auto=not overflow and (season_correction_verified or ts>=.985 or (ts>=.96 and margin>=5))
            else:
                # Exact provider-season title matches are strong evidence even when
                # the franchise root has a slightly higher fuzzy score.
                cand_title=(m.get("title") or {}).get("english") or (m.get("title") or {}).get("romaji") or ""
                season_phrase=f"season {g['season']}"
                season_exact=(g["season"] and season_phrase in cand_title.lower() and sim(g["title"],cand_title)>=.72)
                auto=(not overflow and season_correction_verified) or (not overflow and season_exact) or (ts>=.97 and not overflow and (margin>=3 or g["season"]==1)) or (ts>=.90 and margin>=12 and not overflow)

            out.append({**g,"decision":"AUTO" if auto else "REVIEW","score":score,"margin":round(margin,2),
                        "anilist_id":m.get("id"),"mal_id":m.get("idMal"),
                        "anilist_title":(m.get("title") or {}).get("english") or (m.get("title") or {}).get("romaji"),
                        "anilist_episodes":m.get("episodes"),"reason":"progress exceeds selected entry" if overflow else "",
                        "alternatives":" | ".join(f'{x[1].get("id")}:{(x[1].get("title") or {}).get("english") or (x[1].get("title") or {}).get("romaji")} [{x[0]}]' for x in cand[1:4])})
        except Exception as e:
            out.append({**g,"decision":"ERROR","reason":str(e)})
        if fresh_done and fresh_done % 25 == 0:
            console.print(f"Resolution progress: {fresh_done}/{fresh_required} newly analyzed groups...")

    # Persist a final partial checkpoint before post-processing, so an interruption
    # after the resolver loop still preserves the work just completed.
    if fresh_done and fresh_done != last_checkpoint:
        save_checkpoint(out)

    # v9.1: apply only exact, catalog-verified provider corrections after generic
    # resolution. This reduces known false REVIEW rows without perturbing the
    # frozen generic resolver or raw provider history.
    from src.resolver.verified_overrides import apply_verified_override
    out=[apply_verified_override(r) for r in out]

    od=_resolved_dir(ctx); od.mkdir(parents=True,exist_ok=True)
    outputs={
        "mapping.csv":out,
        "review.csv":[r for r in out if r.get("decision") in {"REVIEW","ERROR","UNRESOLVED"}],
        "excluded.csv":[r for r in out if r.get("decision")=="NOT_ANIME"],
    }
    for name,rows in outputs.items():
        with open(od/name,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    cache_meta_path.write_text(json.dumps({"schema": RESOLUTION_CACHE_SCHEMA}, indent=2), encoding="utf-8")
    if checkpoint_path.exists():
        checkpoint_path.unlink()
    review=len(outputs["review.csv"]); excluded=len(outputs["excluded.csv"]); auto=sum(r.get("decision")=="AUTO" for r in out)
    if reused:
        console.print(f"Reused {reused} previously resolved data labels; {max(0,len(groups)-reused)} groups required fresh analysis.")
    elif len(groups):
        console.print("First-time analysis: no reusable resolved data labels were found. Initial lookup can take longer; future previews will reuse safe matches.")
    console.print(f"[green]Resolution complete.[/green] {len(out)} groups: {auto} AUTO, {review} need review, {excluded} Netflix non-anime exclusions.")
    console.print("No AniList changes were made. Results: data/resolved/mapping.csv, review.csv, excluded.csv")



@cli.command(name="anilist-plan")
@click.option("--mapping", default="data/resolved/mapping.csv", show_default=True)
@click.pass_context
def anilist_plan(ctx, mapping):
    """Build a deduplicated AniList change preview. Never writes to AniList."""
    from src.resolver.sync_plan import read_mapping, consolidate, AniListSync, write_csv, validate_sync_adds
    mapping_path = _resolved_dir(ctx) / "mapping.csv" if mapping == "data/resolved/mapping.csv" else _resolve_config_path(ctx, mapping)
    rows=read_mapping(mapping_path); plan,blockers=consolidate(rows)
    od=_resolved_dir(ctx)
    write_csv(od/"sync_plan_local.csv",plan)
    write_csv(od/"sync_blockers.csv",blockers, list(rows[0].keys()) if rows else None)
    token=(ctx.obj["config"].get("exporters",{}).get("anilist",{}).get("access_token") or "").strip()
    if token:
        console.print(f"Checking {len(plan)} consolidated entries against your current AniList list...")
        enriched,remote_blockers=AniListSync(token).enrich(plan)
        if remote_blockers:
            blockers.extend(remote_blockers)
            write_csv(od/"sync_blockers.csv",blockers)
        safe,sync_review,sync_rejected=validate_sync_adds(enriched,rows)
        write_csv(od/"sync_plan.csv",safe)
        # Bind this preview to the authenticated account and exact CSV bytes.
        # anilist-apply refuses stale/edited plans and requires a fresh preview.
        from src.resolver.sync_plan import ProductionAniListSync, write_plan_meta
        viewer=ProductionAniListSync(token).viewer()
        write_plan_meta(od/"sync_plan.csv", viewer)
        write_csv(od/"sync_review.csv",sync_review)
        write_csv(od/"sync_rejected.csv",sync_rejected)
        adds=sum(x['action']=='ADD' for x in safe); updates=sum(x['action']=='UPDATE' for x in safe); skips=sum(x['action']=='SKIP' for x in safe)
        console.print(f"[green]AniList preview ready.[/green] {adds} ADD, {updates} UPDATE, {skips} SKIP; {len(sync_review)} ADDs held for final review; {len(sync_rejected)} curated false-positive ADDs rejected; {len(blockers)} blocked ({len(remote_blockers)} stale/missing AniList IDs).")
        console.print("No AniList changes were made. Review data/resolved/sync_plan.csv, sync_review.csv, sync_rejected.csv, and sync_blockers.csv")
    else:
        console.print(f"[yellow]No AniList access_token in config.yaml.[/yellow] Local plan created for {len(plan)} entries; {len(blockers)} unresolved groups blocked.")
        console.print("No AniList changes were made. File: data/resolved/sync_plan_local.csv")

@cli.command(name="anilist-apply")
@click.option("--plan", default="data/resolved/sync_plan.csv", show_default=True)
@click.option("--confirm", default="", help="Must be exactly APPLY.")
@click.option("--allow-partial", is_flag=True, help="Allow syncing safe entries while review/blocker rows remain excluded.")
@click.pass_context
def anilist_apply(ctx, plan, confirm, allow_partial):
    """Production-safe AniList apply: backup, account/hash check, drift check, write, verify."""
    import csv, json
    from src.resolver.sync_plan import ProductionAniListSync, PlanError, load_plan_meta, write_csv
    if confirm != "APPLY":
        console.print("[red]Nothing changed.[/red] Run anilist-plan first, then use --confirm APPLY after reviewing the preview.")
        raise SystemExit(2)

    unresolved=[]
    for fn in ("sync_review.csv","sync_blockers.csv"):
        p=_resolved_dir(ctx)/fn
        if p.exists():
            with open(p,newline='',encoding='utf-8-sig') as f: unresolved.extend(list(csv.DictReader(f)))
    if unresolved and not allow_partial:
        console.print(f"[red]Nothing changed.[/red] {len(unresolved)} review/blocker rows remain. They are excluded from writes; use --allow-partial to sync only the safe plan.")
        raise SystemExit(2)

    token=(ctx.obj["config"].get("exporters",{}).get("anilist",{}).get("access_token") or "").strip()
    if not token:
        console.print("[red]Nothing changed.[/red] AniList access_token is missing from config.yaml."); raise SystemExit(2)
    try:
        plan_path = _resolved_dir(ctx) / "sync_plan.csv" if plan == "data/resolved/sync_plan.csv" else _resolve_config_path(ctx, plan)
        meta=load_plan_meta(plan_path)
        with open(plan_path,newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
        sync=ProductionAniListSync(token)
        viewer=sync.viewer()
        if int(meta.get('anilist_user_id') or 0)!=int(viewer.get('id') or 0):
            raise PlanError(f"Plan belongs to AniList user {meta.get('anilist_user_name')} ({meta.get('anilist_user_id')}), but current token is {viewer.get('name')} ({viewer.get('id')}).")

        writable=[r for r in rows if r.get('action') in {'ADD','UPDATE'}]
        console.print(f"Pre-write safety check for {len(writable)} ADD/UPDATE entries on AniList account {viewer.get('name')}...")
        current=sync.current_for_plan(writable)
        drift=sync.detect_drift(writable,current)
        if drift:
            write_csv(_resolved_dir(ctx)/"sync_drift.csv",drift)
            raise PlanError(f"{len(drift)} AniList entries changed since this plan was generated. Nothing changed. Re-run anilist-plan. Details: data/resolved/sync_drift.csv")

        backup_path,_=sync.backup(_data_dir(ctx) / "backups")
        console.print(f"[green]AniList backup created.[/green] {backup_path}")
        changed,log_path=sync.apply_production(writable, _data_dir(ctx) / "logs")

        # Post-write verification. Never infer success solely from mutation responses.
        verify=sync.current_for_plan(writable); failures=[]
        for r in writable:
            mid=int(float(r['anilist_id'])); target=int(float(r['progress']))
            got=int(float((((verify.get(mid) or {}).get('mediaListEntry') or {}).get('progress') or 0)))
            if got<target: failures.append({**r,'verified_progress':got,'verify_reason':'remote progress below planned target'})
        write_csv(_resolved_dir(ctx)/"sync_applied.csv",changed)
        write_csv(_resolved_dir(ctx)/"sync_verify_failures.csv",failures)
        if failures:
            console.print(f"[red]Sync finished with {len(failures)} verification failures.[/red] Review data/resolved/sync_verify_failures.csv and {log_path}")
            raise SystemExit(1)
        console.print(f"[green]AniList sync verified.[/green] {len(changed)} entries added/updated. Backup: {backup_path}. Log: {log_path}")
        console.print("REVIEW, REJECT, BLOCK and SKIP rows were untouched. Rerunning the same workflow will not reduce progress.")
    except PlanError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(2)


@cli.command(name="sync-all")
@click.option("--netflix", "netflix_csv", type=click.Path(exists=True, dir_okay=False), default=None, help="Import/refresh a Netflix ViewingActivity CSV before resolving.")
@click.option("--fetch-crunchyroll", is_flag=True, help="Refresh Crunchyroll history before resolving. Uses the existing secure fetch workflow.")
@click.option("--fetch-hidive", "do_fetch_hidive", is_flag=True, help="Refresh HIDIVE history before resolving. Uses the locally saved HIDIVE authentication workflow.")
@click.option("--apply", "do_apply", is_flag=True, help="After generating a fresh plan, apply only safe ADD/UPDATE rows.")
@click.option("--confirm", default="", help="When --apply is used, must be exactly APPLY.")
@click.option("--allow-partial", is_flag=True, help="Permit safe writes while review/blocker rows remain quarantined.")
@click.option("--sources", default="all", help="Comma-separated sources included in consolidation: crunchyroll,hidive,netflix,manual or all.")
@click.pass_context
def sync_all(ctx, netflix_csv, fetch_crunchyroll, do_fetch_hidive, do_apply, confirm, allow_partial, sources):
    """Run the multi-source AniList workflow from one command.

    By default this command is READ-ONLY: it optionally refreshes/imports provider
    history, resolves all sources, and creates a fresh AniList plan. AniList is
    changed only when both --apply and --confirm APPLY are supplied. All normal
    backup, account binding, plan hash, drift, quarantine, logging, and post-write
    verification protections are delegated to the validated production commands.
    """
    console.print("[bold]Anchor Point sync-all[/bold]")

    if fetch_crunchyroll:
        console.print("\n[bold cyan]== Crunchyroll ======================================[/bold cyan]")
        ctx.invoke(fetch, etp_rt=None, replace=False)
    if do_fetch_hidive:
        console.print("\n[bold cyan]== HIDIVE ===========================================[/bold cyan]")
        try:
            ctx.invoke(fetch_hidive, token=None, api_key=None, replace_hidive=False)
        except SystemExit:
            # A stale HIDIVE credential must never erase or masquerade as fresh
            # history. Continue Preview with the last successful local snapshot.
            store=HistoryStore(Path(str(_history_path(ctx))))
            hidive_eps=[ep for ep in store.all_episodes() if getattr(ep,"source","")=="hidive"]
            hidive_series={getattr(ep,"series_id","") for ep in hidive_eps}
            err=ctx.obj.get("hidive_fetch_error") or "HIDIVE authentication could not be validated."
            console.print(f"[yellow]HIDIVE live refresh was not completed: {err}[/yellow]")
            if hidive_eps:
                console.print(f"Using last successful HIDIVE history: {len(hidive_eps)} episodes across {len(hidive_series)} series.")
                console.print("Reconfigure HIDIVE to retrieve newer viewing activity. Saved HIDIVE history remains included in this Preview.")
            else:
                console.print("No previously saved HIDIVE history is available. HIDIVE will not contribute data to this Preview.")
    if netflix_csv:
        ctx.invoke(import_netflix, csv_file=netflix_csv)

    console.print("\n[bold cyan]== Resolution =======================================[/bold cyan]")
    # Always regenerate resolution and plan in the same run. This prevents an old
    # plan from being silently reused after provider history changes.
    ctx.invoke(resolve_all, sources=sources)
    console.print("\n[bold cyan]== AniList ==========================================[/bold cyan]")
    ctx.invoke(anilist_plan, mapping=str(_resolved_dir(ctx) / "mapping.csv"))

    if not do_apply:
        console.print("[yellow]Dry run complete.[/yellow] AniList was not changed. Review data/resolved/sync_plan.csv and quarantine files.")
        console.print("To write the freshly generated safe plan, rerun with --apply --confirm APPLY (and --allow-partial when quarantined rows remain).")
        return

    if confirm != "APPLY":
        console.print("[red]Nothing changed.[/red] --apply requires --confirm APPLY.")
        raise SystemExit(2)

    # anilist_apply independently rechecks the plan hash/account, detects remote
    # drift, backs up AniList, writes only ADD/UPDATE rows, and verifies remotely.
    console.print("Note: Applying list changes can take some time. Keep Anchor Point open until the sync completes.")
    ctx.invoke(anilist_apply, plan=str(_resolved_dir(ctx) / "sync_plan.csv"), confirm="APPLY", allow_partial=allow_partial)


@cli.command(name="version")
def version_cmd():
    """Show the integrated MultiSource release version."""
    console.print("Anchor Point 1.0.0 (based on CrunchyExporter upstream 1.3.0)")

if __name__ == "__main__":
    cli()


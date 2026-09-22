from pathlib import Path

def test_gui_multisource_module_exists():
    text=Path('gui/tabs/tab_multisource.py').read_text(encoding='utf-8')
    assert 'sync-all' in text and '--confirm' in text and 'APPLY' in text and '--allow-partial' in text
    assert 'sync_blockers.csv' in text and 'sync_review.csv' in text
    assert '--sources' in text and 'Include in Sync' in text

def test_gui_uses_forwarding_entrypoint():
    text=Path('gui/tabs/tab_multisource.py').read_text(encoding='utf-8'); assert '--multisource-cli' in text
    main=Path('main.py').read_text(encoding='utf-8'); assert 'if "--multisource-cli" in sys.argv' in main and 'from src.main import cli' in main

def test_app_mounts_provider_tabs():
    text=Path('gui/app.py').read_text(encoding='utf-8')
    for name in ['MultiSourceTab','CrunchyrollTab','HidiveTab','NetflixTab','ManualEntryTab','Export & Sync Settings']:
        assert name in text

def test_hidive_paste_parser_and_manual_dual_entry_exist():
    text=Path('gui/tabs/tab_sources.py').read_text(encoding='utf-8')
    assert 'Copy as PowerShell' in text and 'Configure HIDIVE' in text
    assert 'Include Quick Entry' in text and 'Include Structured Entry' in text
    assert 'Preview & Append Selected Entries' in text

def test_resolver_supports_source_selection():
    text=Path('src/main.py').read_text(encoding='utf-8')
    assert '@click.option("--sources"' in text
    assert '"netflix" in enabled' in text and 'src not in enabled' in text

def test_anilist_gui_has_explicit_setup_and_validation_controls():
    text=Path('gui/tabs/tab_config.py').read_text(encoding='utf-8')
    assert 'Open AniList Developer Page' in text
    assert 'Copy Redirect URL' in text
    assert 'Configure AniList' in text
    assert 'validate_connection' in text
    assert 'FIRST-TIME SETUP' in text


def test_hidive_sync_does_not_put_credentials_on_clipboard():
    text=Path('gui/tabs/tab_multisource.py').read_text(encoding='utf-8')
    assert 'args.append("--fetch-hidive")' in text
    assert 'clipboard_append' not in text

def test_sync_gui_has_preview_mal_cancel_and_first_run_narrative():
    text=Path('gui/tabs/tab_multisource.py').read_text(encoding='utf-8')
    assert 'Preview Sync Changes' in text
    assert 'Sync Safe Changes to MAL' in text
    assert 'Cancel Workflow' in text
    assert 'First sync may take longer' in text
    assert 'resolved data labels are saved locally' in text


def test_workflow_log_has_source_sections_and_wait_note():
    text=Path('src/main.py').read_text(encoding='utf-8')
    assert '== Crunchyroll' in text and '== HIDIVE' in text
    assert '== Resolution' in text and '== AniList' in text
    assert 'Keep Anchor Point open until the sync completes' in text


def test_resolver_reuses_safe_prior_identity_mappings():
    text=Path('src/main.py').read_text(encoding='utf-8')
    assert 'Incremental resolution cache' in text
    assert 'identity match reused' in text
    assert 'previously resolved data labels' in text


def test_mal_safe_sync_never_reduces_remote_progress():
    text=Path('gui/tabs/tab_multisource.py').read_text(encoding='utf-8')
    assert 'if old>=target' in text
    assert 'Existing MAL progress will never be reduced' in text

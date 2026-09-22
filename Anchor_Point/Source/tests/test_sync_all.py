from click.testing import CliRunner
import src.main as main


def test_sync_all_is_read_only_by_default(monkeypatch):
    calls=[]
    monkeypatch.setattr(main, 'resolve_all', lambda **kw: calls.append('resolve'))
    monkeypatch.setattr(main, 'anilist_plan', lambda **kw: calls.append('plan'))
    monkeypatch.setattr(main, 'anilist_apply', lambda **kw: calls.append('apply'))
    r=CliRunner().invoke(main.cli, ['sync-all'])
    assert r.exit_code == 0, r.output
    assert calls == ['resolve','plan']
    assert 'Dry run complete' in r.output


def test_sync_all_apply_requires_exact_confirmation(monkeypatch):
    calls=[]
    monkeypatch.setattr(main, 'resolve_all', lambda **kw: calls.append('resolve'))
    monkeypatch.setattr(main, 'anilist_plan', lambda **kw: calls.append('plan'))
    monkeypatch.setattr(main, 'anilist_apply', lambda **kw: calls.append('apply'))
    r=CliRunner().invoke(main.cli, ['sync-all','--apply'])
    assert r.exit_code == 2
    assert calls == ['resolve','plan']
    assert '--apply requires --confirm APPLY' in r.output


def test_sync_all_apply_delegates_to_production_engine(monkeypatch):
    calls=[]
    monkeypatch.setattr(main, 'resolve_all', lambda **kw: calls.append('resolve'))
    monkeypatch.setattr(main, 'anilist_plan', lambda **kw: calls.append('plan'))
    def fake_apply(**kw):
        calls.append(('apply', kw['confirm'], kw['allow_partial']))
    monkeypatch.setattr(main, 'anilist_apply', fake_apply)
    r=CliRunner().invoke(main.cli, ['sync-all','--apply','--confirm','APPLY','--allow-partial'])
    assert r.exit_code == 0, r.output
    assert calls == ['resolve','plan',('apply','APPLY',True)]


def test_version_command():
    r=CliRunner().invoke(main.cli, ['version'])
    assert r.exit_code == 0
    assert 'Anchor Point 1.0.0' in r.output
    assert 'Anchor Point' in r.output


def test_sync_all_fetch_hidive_flag_invokes_command_not_bool(monkeypatch):
    calls=[]
    monkeypatch.setattr(main, 'fetch_hidive', lambda **kw: calls.append('hidive'))
    monkeypatch.setattr(main, 'resolve_all', lambda **kw: calls.append('resolve'))
    monkeypatch.setattr(main, 'anilist_plan', lambda **kw: calls.append('plan'))
    r=CliRunner().invoke(main.cli, ['sync-all','--fetch-hidive'])
    assert r.exit_code == 0, r.output
    assert calls == ['hidive','resolve','plan']


def test_sync_all_hidive_auth_failure_uses_saved_history(monkeypatch):
    calls=[]
    def failed_hidive(**kw):
        raise SystemExit(1)
    class Ep:
        source='hidive'; series_id='hidive::series-1'
    class FakeStore:
        def __init__(self, path): pass
        def all_episodes(self): return [Ep()]
    monkeypatch.setattr(main, 'fetch_hidive', failed_hidive)
    monkeypatch.setattr(main, 'HistoryStore', FakeStore)
    monkeypatch.setattr(main, 'resolve_all', lambda **kw: calls.append('resolve'))
    monkeypatch.setattr(main, 'anilist_plan', lambda **kw: calls.append('plan'))
    r=CliRunner().invoke(main.cli, ['sync-all','--fetch-hidive'])
    assert r.exit_code == 0, r.output
    assert calls == ['resolve','plan']
    assert 'Using last successful HIDIVE history: 1 episodes across 1 series.' in r.output
    assert 'Using last successful HIDIVE history' in r.output and 'Reconfigure HIDIVE' in r.output

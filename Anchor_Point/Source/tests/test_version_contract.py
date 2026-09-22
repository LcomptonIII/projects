"""Regression tests for GUI/version module contract."""

def test_version_exports_releases_url():
    from gui.version import __version__, RELEASES_URL
    assert isinstance(__version__, str) and __version__
    assert isinstance(RELEASES_URL, str)

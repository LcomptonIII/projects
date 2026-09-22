from src.hidive.history import HIDIVEHistory


def test_parse_hidive_history_item():
    item = {
        "title": "E11 - THE LIBERATED",
        "watchedAt": 1789193706097,
        "id": 975596,
        "externalAssetId": "asset-1",
        "episodeInformation": {
            "seasonNumber": 2,
            "episodeNumber": 11,
            "seriesInformation": {
                "id": 3813,
                "title": "HELL MODE: The Hardcore Gamer Dominates in Another World with Garbage Balancing",
            },
        },
    }
    ep = HIDIVEHistory._parse_item(item)
    assert ep is not None
    assert ep.source == "hidive"
    assert ep.series_id == "3813"
    assert ep.season_number == 2
    assert ep.episode_number == 11.0
    assert ep.episode_id == "975596"
    assert ep.watched_at.endswith("+00:00")


def test_parse_skips_missing_parent_series():
    assert HIDIVEHistory._parse_item({"id": 1, "episodeInformation": {}}) is None

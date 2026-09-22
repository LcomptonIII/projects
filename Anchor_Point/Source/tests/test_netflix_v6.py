from src.importers.netflix import series_candidates
from src.resolver.anilist import AniListResolver

def test_limited_series_falls_back_to_real_title():
    q=series_candidates("Devilman Crybaby: Limited Series")
    assert "Devilman Crybaby" in q

def test_black_clover_catalog_sequel_falls_back_to_franchise():
    q=series_candidates("Black Clover: Black Clover III")
    assert q[0]=="Black Clover: Black Clover III"
    assert "Black Clover" in q

def test_demon_slayer_arc_has_progressive_fallbacks():
    q=series_candidates("Demon Slayer: Kimetsu no Yaiba: Swordsmith Village Arc: A Connected Bond")
    assert "Demon Slayer: Kimetsu no Yaiba" in q
    assert "Demon Slayer" in q

def test_candidates_any_prefers_strongest_query_match_without_network():
    r=object.__new__(AniListResolver)
    fake={
      "The Gray Man":[(86,{"id":1},.81)],
      "Gray Man":[(100,{"id":2},1.0)],
    }
    r.candidates=lambda q,max_ep=0: fake.get(q,[])
    got=r.candidates_any(["The Gray Man","Gray Man"],1)
    assert got[0][1]["id"]==2 and got[0][3]=="Gray Man"

from src.resolver.franchise import targeted_season_correction


def _media(mid, title, episodes=12):
    return {"id": mid, "episodes": episodes, "format": "TV",
            "title": {"english": title, "romaji": title}, "synonyms": []}


def test_netflix_explicit_season_can_select_matching_anilist_sequel():
    # Mirrors the real Netflix shape: provider title is the franchise root while
    # season number is stored in a separate field.
    candidates = [
        (105.0, _media(21087, "One-Punch Man"), 1.0),
        (97.86, _media(153800, "One-Punch Man Season 3"), .7429),
        (97.86, _media(97668, "One-Punch Man Season 2"), .7429),
    ]
    fixed, verified = targeted_season_correction("One-Punch Man", 3, candidates)
    assert verified is True
    assert fixed[0][1]["id"] == 153800


def test_netflix_season_correction_does_not_guess_without_structural_label():
    candidates = [
        (105.0, _media(1, "Example Show"), 1.0),
        (98.0, _media(2, "Example Show: New Arc"), .80),
    ]
    fixed, verified = targeted_season_correction("Example Show", 2, candidates)
    assert verified is False
    assert fixed[0][1]["id"] == 1

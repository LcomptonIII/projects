from src.importers.netflix import parse_netflix_title

def test_sakamoto_episode_groups_to_series():
    x=parse_netflix_title("SAKAMOTO DAYS: Welcome to Sugar Park")
    assert x["series_title"]=="SAKAMOTO DAYS"

def test_overlord_subseries_preserved():
    x=parse_netflix_title("Overlord: Overlord III: A Ruler's Melancholy")
    assert x["series_title"]=="Overlord: Overlord III"

def test_mob_season_extracted():
    x=parse_netflix_title("Mob Psycho 100: Season 2: Boss Fight ~The Final Light~")
    assert x["series_title"]=="Mob Psycho 100"
    assert x["season"]==2

def test_demon_slayer_arc_preserved():
    x=parse_netflix_title("Demon Slayer: Kimetsu no Yaiba: Swordsmith Village Arc: Someone's Dream")
    assert x["series_title"]=="Demon Slayer: Kimetsu no Yaiba: Swordsmith Village Arc"

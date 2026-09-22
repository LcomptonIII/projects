import json
from pathlib import Path
from src.importers.netflix import series_candidates, save_netflix_json
from src.importers.manual import add_manual
from src.resolver.anilist import titles

def test_netflix_candidates_series_prefix():
    assert series_candidates("KenIchi: The Mightiest Disciple: Episode")[0] == "KenIchi: The Mightiest Disciple"

def test_netflix_season_candidate():
    c=series_candidates("Overlord: Overlord III: A Ruler's Melancholy")
    assert "Overlord: Overlord III" in c

def test_netflix_import(tmp_path):
    src=tmp_path/'n.csv'; src.write_text('Title,Date\nChainsmoker Cat: Episode 1,7/7/26\n',encoding='utf-8')
    out=tmp_path/'n.json'; assert save_netflix_json(src,out)==1
    d=json.loads(out.read_text()); assert d['source']=='netflix' and len(d['views'])==1

def test_manual_replaces_same_entry(tmp_path):
    p=tmp_path/'m.json'; add_manual(p,'Show',1,2); add_manual(p,'Show',1,4)
    d=json.loads(p.read_text()); assert len(d['entries'])==1 and d['entries'][0]['progress']==4

def test_anilist_synonyms_are_media_level():
    m={'title':{'english':'A','romaji':'B','native':'C'},'synonyms':['D']}
    assert titles(m)==['A','B','C','D']

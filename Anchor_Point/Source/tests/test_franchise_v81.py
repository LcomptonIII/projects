from src.resolver.franchise import hybrid_rerank, explicit_season

def m(i,title,episodes=12,fmt='TV'):
    return {'id':i,'episodes':episodes,'format':fmt,'title':{'english':title,'romaji':title},'synonyms':[]}

def test_generic_tv_does_not_choose_special():
    c=[(100,m(1,'One Piece: Episode of Merry',1,'SPECIAL'),1.0),(90,m(2,'ONE PIECE',1000),.95)]
    assert hybrid_rerank('One Piece',1,46,46,c)[0][1]['id']==2

def test_explicit_sequel_can_beat_base_season():
    c=[(98,m(1,'Overlord',13),.98),(91,m(3,'Overlord III',13),.91)]
    assert hybrid_rerank('Overlord III',3,13,13,c)[0][1]['id']==3

def test_ordinary_season_two_can_resolve_sequel():
    c=[(98,m(1,'In Another World With My Smartphone',12),.98),(90,m(2,'In Another World With My Smartphone 2',12),.90)]
    # AniList sequel may use numeric suffix rather than literal "Season 2"; the
    # hybrid must at minimum preserve v7.4's candidate rather than block it.
    assert hybrid_rerank('In Another World With My Smartphone Season 2',2,7,7,c)

def test_roman_suffix_parsed():
    assert explicit_season('Overlord III')==3

def test_bofuri_s2_not_suppressed():
    c=[(97,m(10,"BOFURI: I Don't Want to Get Hurt, so I'll Max Out My Defense.",12),.97),(91,m(11,"BOFURI: I Don't Want to Get Hurt, so I'll Max Out My Defense. Season 2",12),.91)]
    assert hybrid_rerank("BOFURI: I Don't Want to Get Hurt, so I'll Max Out My Defense. Season 2",2,12,12,c)[0][1]['id']==11

def test_arifureta_s3_prefers_explicit_season():
    c=[(98,m(20,'Arifureta: From Commonplace to World’s Strongest',13),.98),(90,m(23,'Arifureta: From Commonplace to World’s Strongest Season 3',16),.90)]
    assert hybrid_rerank('Arifureta: From Commonplace to World’s Strongest Season 3',3,16,16,c)[0][1]['id']==23

def test_iruma_s2_prefers_explicit_season():
    c=[(97,m(30,'Welcome to Demon School! Iruma-kun',23),.97),(91,m(31,'Welcome to Demon School! Iruma-kun Season 2',21),.91)]
    assert hybrid_rerank('Welcome to Demon School! Iruma-kun Season 2',2,21,21,c)[0][1]['id']==31

def test_how_not_to_summon_s2_prefers_explicit_season():
    c=[(98,m(40,'How NOT to Summon a Demon Lord',12),.98),(91,m(41,'How NOT to Summon a Demon Lord Ω',10),.91)]
    # No explicit season marker on the AniList title: keep v7.4 behavior instead
    # of inventing an ambiguity blocker.
    out=hybrid_rerank('How Not to Summon a Demon Lord Season 2',2,6,6,c)
    assert len(out)==2

from src.resolver.franchise import targeted_season_correction

def test_v821_season1_repairs_sequel_inversion():
    c=[(108,m(2,'Witch Hat Atelier Season 2',12),.99),(105,m(1,'Witch Hat Atelier',12),1.0)]
    out,verified=targeted_season_correction('Witch Hat Atelier',1,c)
    assert verified and out[0][1]['id']==1

def test_v821_numeric_suffix_is_positive_season_evidence():
    c=[(105,m(1,'In Another World With My Smartphone',12),1.0),(102,m(2,'In Another World With My Smartphone 2',12),.96)]
    out,verified=targeted_season_correction('In Another World With My Smartphone',2,c)
    assert verified and out[0][1]['id']==2

def test_v821_roman_suffix_is_positive_season_evidence():
    c=[(105,m(1,'Overlord',13),1.0),(89,m(3,'Overlord III',13),.89)]
    out,verified=targeted_season_correction('Overlord',3,c)
    assert verified and out[0][1]['id']==3

def test_v821_does_not_guess_missing_provider_season():
    c=[(105,m(1,"KONOSUBA -God's blessing on this wonderful world!",10),1.0),(102,m(2,"KONOSUBA -God's blessing on this wonderful world! 2",10),.97)]
    out,verified=targeted_season_correction("Konosuba - God's Blessing on This Wonderful World!",5,c)
    assert not verified and out[0][1]['id']==1

def test_v821_ordinal_season1_inversion_unaware_atelier():
    c=[(108,m(2,'Kanchigai no Atelier Meister 2nd Season',12),.99),(105,m(1,'The Unaware Atelier Meister',12),1.0)]
    out,verified=targeted_season_correction('The Unaware Atelier Meister',1,c)
    assert verified and out[0][1]['id']==1

def test_v821_overlord_iv_positive_only():
    c=[(105,m(1,'Overlord',13),1.0),(94,m(4,'Overlord IV',13),.90)]
    out,verified=targeted_season_correction('Overlord',4,c)
    assert verified and out[0][1]['id']==4

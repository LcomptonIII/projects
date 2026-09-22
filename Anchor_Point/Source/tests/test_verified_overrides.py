from src.resolver.verified_overrides import apply_verified_override

def row(title, season, progress=1):
    return {'source':'crunchyroll','title':title,'season':season,'progress':progress,'decision':'REVIEW','anilist_id':999}

def test_witch_hat_s1():
    r=apply_verified_override(row('Witch Hat Atelier',1,9))
    assert r['decision']=='AUTO' and r['anilist_id']==147105 and r['anilist_episodes']==13

def test_smartphone_s2():
    r=apply_verified_override(row('In Another World With My Smartphone',2,7))
    assert r['decision']=='AUTO' and r['anilist_id']==147571

def test_solo_cumulative_bucket():
    r=apply_verified_override(row('Solo Leveling',3,13))
    assert r['decision']=='AUTO' and r['anilist_id']==176496 and r['anilist_episodes']==13

def test_unknown_is_untouched():
    r=row('Some Unknown Show',9,4)
    assert apply_verified_override(r)==r

def test_override_cannot_make_overflow_writable():
    r=apply_verified_override(row('Witch Hat Atelier',1,99))
    assert r['decision']=='REVIEW'

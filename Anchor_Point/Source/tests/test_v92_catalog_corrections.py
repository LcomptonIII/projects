from src.resolver.verified_overrides import apply_verified_override
from src.resolver.sync_plan import validate_sync_adds


def row(source,title,season=1,progress=1):
    return {'source':source,'title':title,'season':season,'progress':progress,'decision':'REVIEW'}


def test_hunter_x_hunter_cr_provider_s5_is_2011_adaptation():
    r=apply_verified_override(row('crunchyroll','Hunter x Hunter',5,4))
    assert r['decision']=='AUTO' and r['anilist_id']==11061 and r['anilist_episodes']==148


def test_netflix_shaman_king_is_2021_adaptation():
    r=apply_verified_override(row('netflix','SHAMAN KING',1,1))
    assert r['decision']=='AUTO' and r['anilist_id']==119675 and r['anilist_episodes']==52


def test_netflix_overlord_sequels_do_not_collapse_to_s1():
    r2=apply_verified_override(row('netflix','Overlord: Overlord II',1,13))
    r3=apply_verified_override(row('netflix','Overlord: Overlord III',1,1))
    assert (r2['anilist_id'],r2['anilist_episodes'])==(98437,13)
    assert (r3['anilist_id'],r3['anilist_episodes'])==(101474,13)


def test_chainsmoker_exact_add_no_longer_held():
    plan=[{'anilist_id':207141,'title':'Chainsmoker Cat','progress':2,'episodes':12,'status':'CURRENT','sources':'netflix','source_groups':1,'remote_progress':0,'remote_status':'','action':'ADD'}]
    mapping=[{'source':'netflix','title':'Chainsmoker Cat','decision':'AUTO','anilist_id':'207141','anilist_title':'Chainsmoker Cat','anilist_episodes':'12','records':'2'}]
    safe,review,rejected=validate_sync_adds(plan,mapping)
    assert len(safe)==1 and not review and not rejected

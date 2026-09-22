from src.resolver.verified_overrides import apply_verified_override
from src.resolver.sync_plan import validate_sync_adds


def row(source,title,season,progress):
    return {'source':source,'title':title,'season':season,'progress':progress,'decision':'REVIEW'}


def test_konosuba_provider_bucket_5_maps_to_original_series():
    r=apply_verified_override(row('crunchyroll',"Konosuba - God's Blessing on This Wonderful World!",5,1))
    assert r['decision']=='AUTO'
    assert r['anilist_id']==21202
    assert r['progress']==1
    assert r['anilist_episodes']==10


def test_netflix_dark_is_non_anime():
    r=apply_verified_override(row('netflix','Dark',1,1))
    assert r['decision']=='NOT_ANIME'
    assert not r['anilist_id']


def test_overlord_ii_and_konosuba_3_are_released_from_final_add_hold():
    enriched=[
      {'anilist_id':98437,'title':'Overlord II','progress':13,'episodes':13,'status':'COMPLETED','sources':'netflix','source_groups':1,'remote_progress':0,'remote_status':'','action':'ADD'},
      {'anilist_id':136804,'title':"KONOSUBA -God's blessing on this wonderful world! 3",'progress':11,'episodes':11,'status':'COMPLETED','sources':'crunchyroll','source_groups':1,'remote_progress':0,'remote_status':'','action':'ADD'},
    ]
    mapping=[
      {'source':'netflix','title':'Overlord: Overlord II','decision':'AUTO','anilist_id':'98437','anilist_title':'Overlord II','records':'13','anilist_episodes':'13'},
      {'source':'crunchyroll','title':"Konosuba - God's Blessing on This Wonderful World!",'decision':'AUTO','anilist_id':'136804','anilist_title':"KONOSUBA -God's blessing on this wonderful world! 3",'records':'11','anilist_episodes':'11'},
    ]
    safe,review,rejected=validate_sync_adds(enriched,mapping)
    assert {x['anilist_id'] for x in safe}=={98437,136804}
    assert not review and not rejected

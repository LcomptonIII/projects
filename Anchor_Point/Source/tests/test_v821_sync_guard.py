from src.resolver.sync_plan import validate_sync_adds

def test_chainsmoker_cat_released_after_positive_catalog_evidence():
    enriched=[{'action':'ADD','anilist_id':207141,'title':'Chainsmoker Cat','progress':2,'episodes':12,'sources':'netflix','source_groups':1}]
    mapping=[{'decision':'AUTO','anilist_id':207141,'source':'netflix','title':'Chainsmoker Cat','anilist_title':'Chainsmoker Cat','records':2,'anilist_episodes':12}]
    safe,review,rejected=validate_sync_adds(enriched,mapping)
    assert len(safe)==1 and not review and not rejected

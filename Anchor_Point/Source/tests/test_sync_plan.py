from src.resolver.sync_plan import consolidate

def row(src,mid,p,total=12,decision='AUTO',title='X'):
    return {'source':src,'anilist_id':str(mid),'progress':str(p),'anilist_episodes':str(total),'decision':decision,'anilist_title':title,'title':title}

def test_dedupe_uses_max_not_sum():
    plan,b=consolidate([row('crunchyroll',1,5),row('hidive',1,8)])
    assert plan[0]['progress']==8 and plan[0]['sources']=='crunchyroll+hidive'

def test_review_is_blocked():
    plan,b=consolidate([row('crunchyroll',1,5,decision='REVIEW')])
    assert not plan and len(b)==1

def test_overflow_is_blocked():
    plan,b=consolidate([row('crunchyroll',1,13,total=12)])
    assert not plan and len(b)==1

def test_completed_only_at_total():
    plan,_=consolidate([row('crunchyroll',1,12,total=12)])
    assert plan[0]['status']=='COMPLETED'



def test_enrich_batches_and_blocks_missing_ids():
    from src.resolver.sync_plan import AniListSync
    sync=AniListSync('dummy')
    calls=[]
    def fake(q,v):
        if 'ids' in v:
            calls.append(list(v['ids']))
            return {'Page': {'media': [
                {'id':i,'mediaListEntry': {'progress': 2, 'status': 'CURRENT'}}
                for i in v['ids'] if i != 1
            ]}}
        # Exact-ID fallback confirms the batch miss is genuinely stale.
        raise __import__('src.resolver.sync_plan',fromlist=['PlanError']).PlanError('404')
    sync.gql=fake
    rows=[{'anilist_id':i,'title':str(i),'progress':5,'episodes':12,'status':'CURRENT','sources':'x','source_groups':1} for i in range(1,83)]
    safe,blocked=sync.enrich(rows)
    assert len(calls)==3
    assert max(len(c) for c in calls)<=40
    assert len(safe)==81 and len(blocked)==1 and blocked[0]['anilist_id']==1

def test_gql_exhausted_retry_never_reports_none(monkeypatch):
    from src.resolver.sync_plan import AniListSync, PlanError
    class R:
        status_code=429; headers={'Retry-After':'0'}; ok=False; text='rate limited'
    sync=AniListSync('dummy')
    sync.s.post=lambda *a,**k:R()
    monkeypatch.setattr('src.resolver.sync_plan.time.sleep',lambda n:None)
    try:
        sync.gql('x',{})
        assert False
    except PlanError as e:
        assert 'None' not in str(e) and '429' in str(e)

def test_sync_add_gate_blocks_known_netflix_collision():
    from src.resolver.sync_plan import validate_sync_adds
    p={'anilist_id':125785,'title':'Evangelion x KATE CM','progress':1,'episodes':1,'status':'COMPLETED','sources':'netflix','source_groups':1,'action':'ADD'}
    m=[row('netflix',125785,1,total=1,title='Kate')]
    m[0]['anilist_title']='Evangelion x KATE CM'; m[0]['records']='1'
    safe,review,rejected=validate_sync_adds([p],m)
    assert not safe and (len(review)==1 or len(rejected)==1)

def test_sync_add_gate_keeps_strong_netflix_series():
    from src.resolver.sync_plan import validate_sync_adds
    p={'anilist_id':120377,'title':'Cyberpunk: Edgerunners','progress':10,'episodes':10,'status':'COMPLETED','sources':'netflix','source_groups':1,'action':'ADD'}
    m=[row('netflix',120377,10,total=10,title='Cyberpunk: Edgerunners')]
    m[0]['records']='10'
    safe,review,rejected=validate_sync_adds([p],m)
    assert len(safe)==1 and not review

def test_sync_add_gate_never_hides_updates():
    from src.resolver.sync_plan import validate_sync_adds
    p={'anilist_id':1,'title':'X','progress':4,'episodes':12,'status':'CURRENT','sources':'netflix','source_groups':1,'action':'UPDATE'}
    safe,review,rejected=validate_sync_adds([p],[])
    assert safe==[p] and not review


def test_v74_curated_approval_moves_death_note_to_safe():
    from src.resolver.sync_plan import validate_sync_adds
    e=[{'anilist_id':1535,'title':'Death Note','progress':26,'episodes':37,'sources':'netflix','action':'ADD'}]
    m=[{'decision':'AUTO','anilist_id':'1535','source':'netflix','title':'DEATH NOTE: Death Note','anilist_title':'Death Note','records':'26','anilist_episodes':'37'}]
    safe,review,rejected=validate_sync_adds(e,m)
    assert len(safe)==1 and not review and not rejected

def test_v74_curated_rejection_never_enters_write_plan():
    from src.resolver.sync_plan import validate_sync_adds
    e=[{'anilist_id':139074,'title':'Destiny','progress':1,'episodes':1,'sources':'netflix','action':'ADD'}]
    m=[{'decision':'AUTO','anilist_id':'139074','source':'netflix','title':'Fate: The Winx Saga','anilist_title':'Destiny'}]
    safe,review,rejected=validate_sync_adds(e,m)
    assert not safe and not review and len(rejected)==1

def test_v92_hunter_1999_is_no_longer_a_special_sync_hold():
    # v9.2 fixes the provider mapping upstream to the 2011 adaptation, so the old
    # AniList-136 write-boundary hold is retired. This test only verifies the gate.
    from src.resolver.sync_plan import validate_sync_adds
    e=[{'anilist_id':136,'title':'Hunter x Hunter','progress':4,'episodes':62,'sources':'crunchyroll','action':'ADD'}]
    m=[{'decision':'AUTO','anilist_id':'136','source':'crunchyroll','title':'Hunter x Hunter','season':'5'}]
    safe,review,rejected=validate_sync_adds(e,m)
    assert len(safe)==1 and not review and not rejected

def test_v74_holds_one_piece_special_collision():
    from src.resolver.sync_plan import validate_sync_adds
    e=[{'anilist_id':19123,'title':'One Piece: Episode of Merry - The Tale of One More Friend','progress':1,'episodes':1,'sources':'crunchyroll','action':'ADD'}]
    m=[{'decision':'AUTO','anilist_id':'19123','source':'crunchyroll','title':'One Piece'}]
    safe,review,rejected=validate_sync_adds(e,m)
    assert not safe and len(review)==1 and not rejected

import csv, json
from pathlib import Path
from src.resolver.sync_plan import ProductionAniListSync, write_plan_meta, load_plan_meta, PlanError

def test_detect_drift_clean_and_changed():
    rows=[{'action':'UPDATE','anilist_id':'1','remote_progress':'3','remote_status':'CURRENT','progress':'5'}]
    clean={1:{'id':1,'mediaListEntry':{'progress':3,'status':'CURRENT'}}}
    assert ProductionAniListSync.detect_drift(rows,clean)==[]
    changed={1:{'id':1,'mediaListEntry':{'progress':4,'status':'CURRENT'}}}
    assert len(ProductionAniListSync.detect_drift(rows,changed))==1

def test_plan_meta_detects_edit(tmp_path):
    p=tmp_path/'sync_plan.csv'; p.write_text('action,anilist_id\nADD,1\n',encoding='utf-8')
    write_plan_meta(p,{'id':7,'name':'tester'})
    assert load_plan_meta(p)['anilist_user_id']==7
    p.write_text('action,anilist_id\nADD,2\n',encoding='utf-8')
    try: load_plan_meta(p); assert False
    except PlanError: pass

def test_apply_never_regresses_and_preserves_update_status(tmp_path):
    s=ProductionAniListSync('x'); calls=[]
    def gql(q,v):
        if 'query($id:Int!)' in q:
            return {'Media':{'mediaListEntry':{'progress':4,'status':'PAUSED'}}}
        calls.append(v); return {'SaveMediaListEntry':{'progress':6,'status':'PAUSED'}}
    s.gql=gql
    rows=[{'action':'UPDATE','anilist_id':'1','title':'X','progress':'6','status':'COMPLETED'}]
    changed,log=s.apply_production(rows,tmp_path)
    assert calls[0]['status'] is None
    assert changed[0]['applied_progress']==6
    assert Path(log).exists()

def test_apply_skips_remote_ahead(tmp_path):
    s=ProductionAniListSync('x'); writes=[]
    def gql(q,v):
        if 'query($id:Int!)' in q: return {'Media':{'mediaListEntry':{'progress':9,'status':'CURRENT'}}}
        writes.append(v); return {}
    s.gql=gql
    changed,_=s.apply_production([{'action':'UPDATE','anilist_id':'1','title':'X','progress':'6'}],tmp_path)
    assert changed==[] and writes==[]

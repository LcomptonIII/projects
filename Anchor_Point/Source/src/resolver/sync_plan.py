from __future__ import annotations
import csv, json, time
from collections import defaultdict
from pathlib import Path
import requests

API='https://graphql.anilist.co'
ENTRY='''query($id:Int!){Media(id:$id,type:ANIME){id episodes title{english romaji} mediaListEntry{progress status}}}'''
BATCH_ENTRY='''query($ids:[Int]){Page(page:1,perPage:50){media(id_in:$ids,type:ANIME){id episodes title{english romaji} mediaListEntry{progress status}}}}'''
UPSERT='''mutation($mediaId:Int!,$status:MediaListStatus!,$progress:Int!){SaveMediaListEntry(mediaId:$mediaId,status:$status,progress:$progress){id status progress}}'''

class PlanError(RuntimeError): pass

def read_mapping(path):
    with open(path,newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))

def _i(v,default=0):
    try: return int(float(v))
    except: return default

def consolidate(mapping_rows):
    """Consolidate only AUTO mappings. Same AniList ID uses MAX progress, never SUM."""
    by=defaultdict(list); blockers=[]
    for r in mapping_rows:
        if r.get('decision')!='AUTO':
            if r.get('decision') not in {'NOT_ANIME','EXCLUDED_BONUS'}: blockers.append(r)
            continue
        mid=_i(r.get('anilist_id'))
        if not mid: blockers.append(r); continue
        by[mid].append(r)
    plan=[]
    for mid,rows in by.items():
        progress=max(_i(r.get('progress')) for r in rows)
        totals=[_i(r.get('anilist_episodes')) for r in rows if _i(r.get('anilist_episodes'))>0]
        total=max(totals) if totals else 0
        # Never send impossible progress. An overflow belongs in provider review.
        if total and progress>total:
            blockers.extend(rows); continue
        title=next((r.get('anilist_title') for r in rows if r.get('anilist_title')),rows[0].get('title',''))
        sources=sorted(set(r.get('source','') for r in rows))
        plan.append({'anilist_id':mid,'title':title,'progress':progress,'episodes':total,
                     'status':'COMPLETED' if total and progress>=total else 'CURRENT',
                     'sources':'+'.join(sources),'source_groups':len(rows)})
    return sorted(plan,key=lambda x:(x['title'].lower(),x['anilist_id'])),blockers

class AniListSync:
    def __init__(self,token):
        self.s=requests.Session(); self.s.headers.update({'Authorization':f'Bearer {token}','Content-Type':'application/json','Accept':'application/json','User-Agent':'AnchorPoint/1.3.0'})
    def gql(self,q,v):
        last=None
        for a in range(10):
            try:
                r=self.s.post(API,json={'query':q,'variables':v},timeout=30)
                if r.status_code==429:
                    # AniList can rate-limit for longer than Retry-After. Honor both
                    # Retry-After and X-RateLimit-Reset when supplied.
                    retry=0
                    try: retry=int(float(r.headers.get('Retry-After','0') or 0))
                    except Exception: pass
                    try:
                        reset=int(float(r.headers.get('X-RateLimit-Reset','0') or 0))
                        if reset: retry=max(retry, reset-int(time.time())+1)
                    except Exception: pass
                    retry=max(2,min(retry or (4+a*2),60))
                    last=PlanError(f'AniList rate limit (HTTP 429); retrying in {retry}s')
                    time.sleep(retry); continue
                if not r.ok: raise PlanError(f'AniList HTTP {r.status_code}: {r.text[:500]}')
                j=r.json()
                if j.get('errors'): raise PlanError(str(j['errors']))
                time.sleep(.4); return j['data']
            except requests.RequestException as e:
                last=e; time.sleep(min(10,a+1))
        raise PlanError(str(last or 'AniList request failed after retries'))

    def enrich(self,plan):
        """Compare the local plan with AniList in batches.

        v7.1 queried every media ID separately, which could exhaust AniList's request
        budget and end with PlanError(None). v7.2 validates up to 40 IDs per GraphQL
        request, so a 459-entry library normally needs only about a dozen requests.
        Missing/deleted IDs are blocked individually and the rest continue.
        """
        out=[]; blockers=[]
        by_id={_i(p.get('anilist_id')):p for p in plan}
        ids=[i for i in by_id if i]
        found={}
        for pos in range(0,len(ids),40):
            chunk=ids[pos:pos+40]
            d=self.gql(BATCH_ENTRY,{'ids':chunk})
            media=((d or {}).get('Page') or {}).get('media') or []
            for m in media:
                if m and _i(m.get('id')): found[_i(m['id'])]=m

        for p in plan:
            mid=_i(p.get('anilist_id'))
            m=found.get(mid)
            if not m:
                # AniList's Page(id_in:) response can occasionally omit an otherwise
                # valid media ID. Confirm a batch miss with the exact-ID query before
                # declaring it stale. A genuine 404 remains blocked.
                try:
                    exact=self.gql(ENTRY,{'id':mid})
                    m=(exact or {}).get('Media')
                except PlanError:
                    m=None
            if not m:
                q=dict(p); q['blocker_reason']='AniList media ID not found during batch and exact-ID remote validation'
                blockers.append(q); continue
            cur=m.get('mediaListEntry') or {}
            old=_i(cur.get('progress')); oldstatus=cur.get('status') or ''
            q=dict(p); q['remote_progress']=old; q['remote_status']=oldstatus
            if old>=p['progress']:
                q['action']='SKIP'
            else:
                q['action']='UPDATE' if cur else 'ADD'
            out.append(q)
        return out,blockers

    def apply(self,rows):
        done=[]
        for r in rows:
            if r.get('action') not in {'ADD','UPDATE'}: continue
            self.gql(UPSERT,{'mediaId':_i(r['anilist_id']),'status':r['status'],'progress':_i(r['progress'])})
            done.append(r)
        return done

def write_csv(path,rows,cols=None):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    if cols is None:
        cols=list(rows[0].keys()) if rows else ['anilist_id','title','progress','episodes','status','sources','source_groups']
    with open(p,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); w.writeheader(); w.writerows(rows)

# v7.4 curated + final pre-sync validation.
# Decisions here are deliberately narrow and come from the user's audited v7.3
# plan. A curated rejection is never written to AniList; a final-audit hold is
# returned to sync_review.csv for explicit inspection.
import re
from difflib import SequenceMatcher

CURATED_APPROVE_IDS={177687,21498,142455,4690,1535,98460,139643,185,100356,107727,392,98437,136804}
CURATED_REJECT_IDS={139074,125785,13115,20947,6535,142567,7375,109020,138060,5027,205374,102578,118620}
FINAL_AUDIT_HOLDS={
    19123:'Provider title One Piece resolved to the Episode of Merry special',
    100256:"The Ancient Magus' Bride resolved to a different Mahoyome entry while the main TV entry is an alternative",
    136804:'Generic KONOSUBA provider title resolved directly to season 3',
}

def _norm_title(s):
    s=(s or '').lower().replace('’',"'")
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def _sim(a,b):
    a,b=_norm_title(a),_norm_title(b)
    return SequenceMatcher(None,a,b).ratio() if a and b else 0.0

def validate_sync_adds(enriched, mapping_rows):
    """Return (safe, review, rejected) for the remote plan.

    UPDATE/SKIP rows are preserved. New ADDs receive curated decisions first,
    then a conservative final audit. Curated approvals bypass generic Netflix
    ambiguity checks; curated rejections are removed from the writable plan.
    """
    prov=defaultdict(list)
    for r in mapping_rows:
        if r.get('decision')=='AUTO' and _i(r.get('anilist_id')):
            prov[_i(r['anilist_id'])].append(r)

    safe=[]; review=[]; rejected=[]
    promo=re.compile(r'\b(cm|pv|commercial|promo(?:tional)?|trailer|music video)\b',re.I)
    collision_titles={
        'fate the winx saga','kate','ragnarok','moon','the gift','3 season 1 chapter 01',
        'star wars the clone wars','frontier','lilo stitch','love','the crow','paradise'
    }

    for p in enriched:
        if p.get('action')!='ADD':
            safe.append(p); continue
        mid=_i(p.get('anilist_id')); rows=prov.get(mid,[])
        if mid in CURATED_REJECT_IDS:
            q=dict(p); q['sync_reject_reason']='Curated false-positive mapping from v7.3 final audit'
            q['provider_titles']=' | '.join(dict.fromkeys(r.get('title','') for r in rows if r.get('title')))
            rejected.append(q); continue
        if mid in CURATED_APPROVE_IDS:
            safe.append(p); continue
        if mid in FINAL_AUDIT_HOLDS:
            q=dict(p); q['sync_review_reason']=FINAL_AUDIT_HOLDS[mid]
            q['provider_titles']=' | '.join(dict.fromkeys(r.get('title','') for r in rows if r.get('title')))
            review.append(q); continue

        reasons=[]
        if promo.search(p.get('title','')):
            reasons.append('AniList candidate appears to be promotional/advertising media')
        if p.get('sources')=='netflix':
            nrows=[r for r in rows if r.get('source')=='netflix']
            # v8.2.1: exact same-name Netflix collisions with insufficient catalog
            # evidence are held at the write boundary, without changing resolver
            # coverage or globally penalizing exact anime titles.
            if not nrows:
                reasons.append('No Netflix mapping provenance found for new entry')
            else:
                for r in nrows:
                    raw=r.get('title',''); nt=_norm_title(raw); at=r.get('anilist_title') or p.get('title','')
                    records=_i(r.get('records'),1); eps=_i(r.get('anilist_episodes')) or _i(p.get('episodes'))
                    if nt in collision_titles: reasons.append(f'Known Netflix title collision: {raw}')
                    if re.match(r'^\s*:\s*episode\s+\d+',raw,re.I): reasons.append(f'Malformed Netflix episode title: {raw}')
                    if _sim(raw,at)<0.72: reasons.append(f'Provider/AniList title mismatch: {raw} -> {at}')
                    if records<=1 and len(_norm_title(raw).split())<=2 and eps<=1:
                        reasons.append(f'Ambiguous short Netflix movie/special title: {raw}')
        if reasons:
            q=dict(p); q['sync_review_reason']='; '.join(dict.fromkeys(reasons))
            q['provider_titles']=' | '.join(dict.fromkeys(r.get('title','') for r in rows if r.get('title')))
            review.append(q)
        else:
            safe.append(p)
    return safe,review,rejected

# Production-safe AniList synchronization (v9).
# The resolver remains frozen; these helpers only harden the write boundary.
import hashlib
from datetime import datetime, timezone

VIEWER='''query{Viewer{id name}}'''
BACKUP='''query($userId:Int!){MediaListCollection(userId:$userId,type:ANIME,forceSingleCompletedList:false){lists{name isCustomList isSplitCompletedList status entries{id mediaId status score progress repeat priority private notes hiddenFromStatusLists customLists advancedScores startedAt{year month day} completedAt{year month day} updatedAt createdAt media{id episodes title{english romaji native}}}}}}'''
UPSERT_SAFE='''mutation($mediaId:Int!,$progress:Int!,$status:MediaListStatus){SaveMediaListEntry(mediaId:$mediaId,progress:$progress,status:$status){id mediaId status progress}}'''

def utc_stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

def file_sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def write_plan_meta(plan_path, viewer, resolver_version='v8.2.1+upstream1.3'):
    p=Path(plan_path)
    meta={
        'schema_version':1,
        'generated_at':datetime.now(timezone.utc).isoformat(),
        'resolver_version':resolver_version,
        'plan_file':p.name,
        'plan_sha256':file_sha256(p),
        'anilist_user_id':_i((viewer or {}).get('id')),
        'anilist_user_name':(viewer or {}).get('name',''),
    }
    mp=p.with_suffix('.meta.json')
    mp.write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    return mp,meta

def load_plan_meta(plan_path):
    p=Path(plan_path); mp=p.with_suffix('.meta.json')
    if not mp.exists(): raise PlanError(f'Missing plan metadata: {mp}. Re-run anilist-plan before applying.')
    try: meta=json.loads(mp.read_text(encoding='utf-8'))
    except Exception as e: raise PlanError(f'Invalid plan metadata: {e}')
    if meta.get('plan_sha256')!=file_sha256(p):
        raise PlanError('sync_plan.csv changed after preview. Re-run anilist-plan before applying.')
    return meta

class ProductionAniListSync(AniListSync):
    def viewer(self):
        return (self.gql(VIEWER,{}) or {}).get('Viewer') or {}

    def backup(self, backup_dir='data/backups'):
        viewer=self.viewer(); uid=_i(viewer.get('id'))
        if not uid: raise PlanError('Could not identify the authenticated AniList account.')
        data=self.gql(BACKUP,{'userId':uid})
        payload={
            'schema_version':1,
            'created_at':datetime.now(timezone.utc).isoformat(),
            'viewer':viewer,
            'media_list_collection':(data or {}).get('MediaListCollection'),
        }
        d=Path(backup_dir); d.mkdir(parents=True,exist_ok=True)
        path=d/f'anilist_{utc_stamp()}.json'
        path.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
        return path,payload

    def current_for_plan(self, rows):
        """Re-fetch only planned IDs and return current state keyed by media ID."""
        ids=[]
        for r in rows:
            mid=_i(r.get('anilist_id'))
            if mid and mid not in ids: ids.append(mid)
        found={}
        for pos in range(0,len(ids),40):
            d=self.gql(BATCH_ENTRY,{'ids':ids[pos:pos+40]})
            for m in (((d or {}).get('Page') or {}).get('media') or []):
                if m and _i(m.get('id')): found[_i(m['id'])]=m
        return found

    @staticmethod
    def detect_drift(rows,current):
        drift=[]
        for r in rows:
            if r.get('action') not in {'ADD','UPDATE'}: continue
            mid=_i(r.get('anilist_id')); m=current.get(mid)
            if not m:
                drift.append({**r,'drift_reason':'AniList media ID missing during pre-write validation'}); continue
            entry=m.get('mediaListEntry') or {}
            now_progress=_i(entry.get('progress')); now_status=entry.get('status') or ''
            planned_old=_i(r.get('remote_progress')); planned_status=r.get('remote_status') or ''
            # Any remote change since planning invalidates the write. Re-plan rather
            # than guessing whether another client/user edit should win.
            if now_progress!=planned_old or now_status!=planned_status:
                drift.append({**r,'current_progress':now_progress,'current_status':now_status,
                              'drift_reason':f'remote changed since plan ({planned_status} {planned_old} -> {now_status} {now_progress})'})
        return drift

    def apply_production(self, rows, log_dir='data/logs'):
        """Apply ADD/UPDATE rows one at a time with no progress regression.

        UPDATE preserves the user's existing AniList status and unrelated fields;
        only progress is changed. ADD uses the planned CURRENT/COMPLETED status.
        A failure is logged and aborts the run so a rerun can safely continue.
        """
        d=Path(log_dir); d.mkdir(parents=True,exist_ok=True)
        log_path=d/f'anilist_sync_{utc_stamp()}.jsonl'
        changed=[]
        with open(log_path,'a',encoding='utf-8') as log:
            for r in rows:
                if r.get('action') not in {'ADD','UPDATE'}: continue
                mid=_i(r.get('anilist_id')); target=_i(r.get('progress'))
                # Re-fetch immediately before each mutation. This is intentionally
                # conservative; a changed entry is skipped/aborted rather than overwritten.
                data=self.gql(ENTRY,{'id':mid}); media=(data or {}).get('Media') or {}
                cur=media.get('mediaListEntry') or {}
                old=_i(cur.get('progress')); old_status=cur.get('status') or ''
                event={'timestamp':datetime.now(timezone.utc).isoformat(),'media_id':mid,
                       'title':r.get('title',''),'action':r.get('action'),'old_progress':old,
                       'old_status':old_status,'planned_progress':target,'result':None}
                if old>=target:
                    event['result']='SKIP_ALREADY_AT_OR_AHEAD'; log.write(json.dumps(event,ensure_ascii=False)+'\n'); log.flush(); continue
                # UPDATE keeps existing status. ADD receives the planned status.
                status=None if cur else (r.get('status') or 'CURRENT')
                try:
                    resp=self.gql(UPSERT_SAFE,{'mediaId':mid,'progress':target,'status':status})
                    saved=(resp or {}).get('SaveMediaListEntry') or {}
                    event['new_progress']=_i(saved.get('progress')); event['new_status']=saved.get('status') or ''
                    event['result']='OK'; log.write(json.dumps(event,ensure_ascii=False)+'\n'); log.flush()
                    changed.append({**r,'applied_progress':event['new_progress'],'applied_status':event['new_status']})
                except Exception as e:
                    event['result']='ERROR'; event['error']=str(e)
                    log.write(json.dumps(event,ensure_ascii=False)+'\n'); log.flush()
                    raise PlanError(f'AniList write failed for {mid} {r.get("title","")}: {e}. Sync stopped; rerun is safe.')
        return changed,log_path

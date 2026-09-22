from __future__ import annotations
import re
from dataclasses import dataclass
from difflib import SequenceMatcher

SPECIAL_FORMATS={'SPECIAL','OVA','ONA','MUSIC'}
SPECIAL_WORDS=re.compile(r'\b(ova|ona|special|movie|film|recap|episode of|memorial|pv|cm|commercial|trailer|music video)\b',re.I)
SEASON_RE=re.compile(r'\b(?:season|series)\s*([0-9]+|[ivx]+)\b',re.I)
PART_RE=re.compile(r'\b(?:part|cour)\s*([0-9]+|[ivx]+)\b',re.I)
ROMAN={'i':1,'ii':2,'iii':3,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,'ix':9,'x':10}

def norm(s):
    s=(s or '').lower().replace('’',"'")
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def _num(x):
    x=(x or '').lower()
    return int(x) if x.isdigit() else ROMAN.get(x,0)

def explicit_season(title):
    m=SEASON_RE.search(title or '')
    if m:return _num(m.group(1))
    # Roman numeral suffixes are common: Overlord II/III, Black Clover III.
    m=re.search(r'\s([ivx]{2,4})\s*$',title or '',re.I)
    return _num(m.group(1)) if m else 0

def explicit_part(title):
    m=PART_RE.search(title or '')
    return _num(m.group(1)) if m else 0

def franchise_root(title):
    s=norm(title)
    s=re.sub(r'\b(?:season|series|part|cour)\s*(?:[0-9]+|[ivx]+)\b.*$','',s)
    s=re.sub(r'\b(?:ii|iii|iv|v|vi|vii|viii|ix|x)\b$','',s)
    return s.strip()

def similarity(a,b):
    a,b=norm(a),norm(b)
    return SequenceMatcher(None,a,b).ratio() if a and b else 0.0

def title_list(m):
    t=m.get('title') or {}
    return [x for x in [t.get('english'),t.get('romaji'),t.get('native'),*(m.get('synonyms') or [])] if x]

def is_special(m):
    fmt=(m.get('format') or '').upper()
    return fmt in SPECIAL_FORMATS or any(SPECIAL_WORDS.search(x or '') for x in title_list(m))

def provider_requests_special(title):
    return bool(SPECIAL_WORDS.search(title or ''))

def best_title_sim(provider,m):
    return max([similarity(provider,x) for x in title_list(m)] or [0.0])

def family_sim(provider,m):
    root=franchise_root(provider)
    return max([similarity(root,franchise_root(x)) for x in title_list(m)] or [0.0])

def candidate_score(provider, provider_season, min_ep, max_ep, count, m):
    """Score provider metadata against one AniList media node.

    The rules intentionally model common provider/AniList differences instead of
    naming individual shows: explicit sequel labels, provider season numbers,
    episode-range evidence, and TV-vs-special discrimination.
    """
    ts=best_title_sim(provider,m); fs=family_sim(provider,m)
    score=ts*70+fs*30
    cand=' '.join(title_list(m))
    ps=explicit_season(provider)
    cs=explicit_season(cand)
    pp=explicit_part(provider); cp=explicit_part(cand)
    if ps and cs: score += 22 if ps==cs else -18
    elif ps and ps>1 and not cs: score -= 7
    if pp and cp: score += 12 if pp==cp else -10
    total=int(m.get('episodes') or 0)
    span=max(0,int(max_ep or 0)-int(min_ep or 0)+1) if max_ep else int(count or 0)
    if total:
        if span and span==total: score+=12
        elif count and int(count)==total: score+=10
        elif max_ep and int(max_ep)<=total: score+=4
        elif max_ep and int(max_ep)>total: score-=10
    if is_special(m) and not provider_requests_special(provider): score-=45
    if not is_special(m) and provider_requests_special(provider): score-=8
    # Provider season is weak evidence only. It breaks ties inside an already
    # identified franchise but never overrides a poor title-family match.
    if provider_season and fs>=.78 and cs:
        score += 8 if int(provider_season)==cs else -4
    return round(score,2)

def choose_candidate(provider, provider_season, min_ep, max_ep, count, candidates):
    ranked=[]
    for m in candidates:
        ranked.append((candidate_score(provider,provider_season,min_ep,max_ep,count,m),m))
    ranked.sort(key=lambda x:x[0],reverse=True)
    if not ranked:return None,[], 'no candidates'
    best=ranked[0]; second=ranked[1][0] if len(ranked)>1 else -999
    fs=family_sim(provider,best[1])
    if fs<.68:return None,ranked,'weak franchise match'
    if best[0]-second<3 and len(ranked)>1:return None,ranked,'adaptation/franchise ambiguity'
    return best[1],ranked,''

def allocate_progress(entries, watched_count):
    """Allocate one provider bucket across sequential AniList entries.

    Used only when the provider bucket demonstrably spans more episodes than one
    AniList TV/cour entry. Unknown episode totals stop automatic allocation.
    """
    left=max(0,int(watched_count or 0)); out=[]
    for m in entries:
        total=int(m.get('episodes') or 0)
        if not total or left<=0:break
        p=min(left,total); out.append((m,p)); left-=p
    return out,left

def hybrid_rerank(provider, provider_season, progress, records, candidates):
    """Conservative v8.1 candidate re-ranking.

    Keeps v7.4's candidate set and AUTO thresholds. We only reorder when provider
    metadata gives positive evidence. This avoids v8's regression where generic
    franchise ambiguity converted ordinary sequels into manual-review rows.
    """
    if not candidates:
        return candidates
    ps=explicit_season(provider)
    wants_special=provider_requests_special(provider)
    base=candidates[0]
    ranked=[]
    for original_score,m,ts in candidates:
        bonus=0.0
        fam=family_sim(provider,m)
        cand_text=' '.join(title_list(m))
        cs=explicit_season(cand_text)
        # Generic TV provider labels should strongly prefer normal series entries.
        if is_special(m) and not wants_special:
            bonus-=55.0
        elif not is_special(m) and not wants_special:
            bonus+=2.0
        # Explicit provider labels such as "Season 2" / "Overlord III" are strong
        # positive evidence *inside an already identified franchise*.
        if fam>=.76 and ps and cs:
            bonus += 24.0 if ps==cs else -16.0
        # Provider season field is weaker because some services use internal values.
        elif fam>=.84 and provider_season and int(provider_season)>1 and cs:
            bonus += 8.0 if int(provider_season)==cs else -3.0
        # Episode totals/ranges are tie-breakers, not franchise identity evidence.
        total=int(m.get('episodes') or 0)
        if total and progress:
            if int(progress)<=total: bonus+=2.0
            else: bonus-=3.0
        ranked.append((original_score+bonus,m,ts,original_score))
    ranked.sort(key=lambda x:(x[0],x[2],x[3]), reverse=True)
    chosen=ranked[0]
    # Do not let weak family evidence replace v7.4's original winner. The special
    # guard is the exception because a generic TV title mapping to a recap/OVA is
    # structurally unsafe even when fuzzy title similarity is high.
    if chosen[1].get('id') != base[1].get('id'):
        chosen_fam=family_sim(provider,chosen[1])
        base_is_bad_special=is_special(base[1]) and not wants_special
        if chosen_fam < .76 and not base_is_bad_special:
            return candidates
    # Return original score values so v7.4 confidence thresholds/margins retain
    # their established behavior; only candidate ordering changes.
    order=[(x[3],x[1],x[2]) for x in ranked]
    return order

def episode_profile(episode_numbers):
    """Translate provider episode numbering into local-season progress.

    Streaming services often keep a cumulative counter across seasons (25-48,
    26-50, etc.).  The contiguous tail ending at the highest watched episode is
    the reliable local progress for those buckets. Episode 0 is provider bonus
    material and is ignored for progress allocation.
    """
    nums=sorted({int(float(x)) for x in episode_numbers if x is not None and int(float(x))>0})
    if not nums:
        return {'min_episode':0,'max_episode':0,'local_progress':1 if episode_numbers else 0,'raw_progress':0}
    mx=nums[-1]; tail=1
    for i in range(len(nums)-2,-1,-1):
        if nums[i]==nums[i+1]-1: tail+=1
        else: break
    mn=nums[0]
    cumulative=(mn>1) or (tail<len(nums) and nums[-tail]>1)
    local=tail if cumulative else mx
    return {'min_episode':mn,'max_episode':mx,'local_progress':local,'raw_progress':mx}

def sequel_chain(start, candidates, max_entries=8):
    """Walk explicit AniList SEQUEL edges within an already fetched candidate pool."""
    byid={int(m.get('id')):m for m in candidates if m.get('id')}
    cur=start; out=[]; seen=set()
    while cur and len(out)<max_entries and int(cur.get('id',0)) not in seen:
        cid=int(cur.get('id')); seen.add(cid); out.append(cur)
        nxt=[]
        for e in ((cur.get('relations') or {}).get('edges') or []):
            if e.get('relationType')=='SEQUEL':
                nid=int(((e.get('node') or {}).get('id')) or 0)
                if nid in byid and nid not in seen: nxt.append(byid[nid])
        if not nxt: break
        # Prefer normal episodic entries. Specials are never silently inserted
        # into a provider TV season/cour allocation.
        nxt.sort(key=lambda m:(is_special(m), -(int(m.get('episodes') or 0)>0), int(m.get('id') or 0)))
        cur=nxt[0]
    return out

def split_overflow(start, candidates, watched_count):
    """Allocate a contiguous provider bucket across explicit sequel/cour nodes.

    Returns [] unless the whole watched count can be represented by a chain of
    normal episodic AniList entries. This intentionally leaves OVAs/specials and
    incomplete chains for manual review.
    """
    chain=[m for m in sequel_chain(start,candidates) if not is_special(m)]
    alloc,left=allocate_progress(chain,watched_count)
    return alloc if alloc and left==0 and len(alloc)>1 else []

def structural_season(title):
    """Season number from explicit sequel syntax used only for verified correction."""
    n=explicit_season(title)
    if n:return n
    text=title or ''
    m=re.search(r'\b([0-9]+)(?:st|nd|rd|th)\s+season\b',text,re.I)
    if m:return int(m.group(1))
    m=re.search(r'\s([2-9])\s*$',text)
    return int(m.group(1)) if m else 0

def targeted_season_correction(provider, provider_season, candidates):
    """v8.2.1 post-resolver correction with positive structural evidence only.

    It may reorder v8.2 candidates, but never creates ambiguity or demotes a
    valid baseline mapping. Returns (candidates, verified_correction).
    """
    if not candidates:
        return candidates, False
    try: ps=int(provider_season or 0)
    except Exception: ps=0
    if ps < 1 or ps > 9:
        return candidates, False
    base=candidates[0]
    base_m=base[1]
    base_cs=structural_season(' '.join(title_list(base_m)))
    # Require a strongly identified title family before season correction.
    pool=[]
    for item in candidates:
        m=item[1]
        fam=family_sim(provider,m)
        if fam < .82 or is_special(m):
            continue
        cs=structural_season(' '.join(title_list(m)))
        pool.append((item,fam,cs))

    # Season 1: undo a sequel inversion only when a strong main/base entry is
    # already present among AniList candidates.
    if ps == 1 and base_cs > 1:
        mains=[x for x in pool if x[2] in (0,1) and x[1] >= .90]
        if mains:
            chosen=max(mains,key=lambda x:(x[1],x[0][2],x[0][0]))[0]
            return [chosen]+[x for x in candidates if x[1].get('id')!=chosen[1].get('id')], True

    # Seasons 2+: exact structural season labels (Season 2, 2nd Season,
    # numeric suffix, Roman suffix) are positive evidence. If no exact label
    # exists, leave v8.2 untouched; provider numbering can be non-literal.
    exact=[x for x in pool if x[2] == ps]
    if exact:
        chosen=max(exact,key=lambda x:(x[1],x[0][2],x[0][0]))[0]
        if chosen[1].get('id') != base_m.get('id'):
            return [chosen]+[x for x in candidates if x[1].get('id')!=chosen[1].get('id')], True
    return candidates, False

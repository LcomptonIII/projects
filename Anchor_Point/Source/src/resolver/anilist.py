from __future__ import annotations
import json,re,time,unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import requests
API="https://graphql.anilist.co"
Q_SEARCH='''query($s:String!){Page(perPage:10){media(search:$s,type:ANIME){id idMal episodes format status seasonYear synonyms title{romaji english native}}}}'''
Q_MEDIA='''query($id:Int!){Media(id:$id,type:ANIME){id idMal episodes format status seasonYear synonyms title{romaji english native} relations{edges{relationType(version:2) node{id}}}}}'''

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "")).encode("ascii","ignore").decode().lower().replace("&"," and ")
    s=re.sub(r"[^a-z0-9]+"," ",s); return " ".join(s.split())
def titles(m):
    t=m.get("title") or {}; return [x for x in [t.get("english"),t.get("romaji"),t.get("native"),*(m.get("synonyms") or [])] if x]
def sim(a,b):
    a,b=norm(a),norm(b); return SequenceMatcher(None,a,b).ratio() if a and b else 0
class AniListResolver:
    def __init__(self, cache_path):
        self.path=Path(cache_path); self.cache=json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.s=requests.Session(); self.s.headers.update({"Accept":"application/json","Content-Type":"application/json","User-Agent":"AnchorPoint/1.3.0"})
    def save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True); self.path.write_text(json.dumps(self.cache,ensure_ascii=False,indent=2),encoding="utf-8")
    def gql(self,q,v):
        last=None
        for attempt in range(7):
            try:
                r=self.s.post(API,json={"query":q,"variables":v},timeout=30)
                if r.status_code==429:
                    time.sleep(max(2,int(r.headers.get("Retry-After","4")))); continue
                if r.status_code==404: return None
                if not r.ok:
                    try: detail=r.json()
                    except Exception: detail=r.text[:500]
                    raise RuntimeError(f"AniList HTTP {r.status_code}: {detail}")
                j=r.json()
                if j.get("errors"): raise RuntimeError(j["errors"])
                time.sleep(.35); return j.get("data")
            except (requests.RequestException,RuntimeError) as e:
                last=e; time.sleep(min(8,1+attempt))
        raise RuntimeError(str(last))
    def search(self,s):
        k="s:"+norm(s)
        if k not in self.cache:
            d=self.gql(Q_SEARCH,{"s":s}); self.cache[k]=(d or {}).get("Page",{}).get("media",[]); self.save()
        return self.cache[k]
    def media(self,i):
        k="m:"+str(i)
        if k not in self.cache:
            d=self.gql(Q_MEDIA,{"id":int(i)}); self.cache[k]=(d or {}).get("Media"); self.save()
        return self.cache[k]
    def expand(self,seeds,depth=5,max_nodes=50):
        out={}; q=[(int(x),0) for x in seeds]
        while q and len(out)<max_nodes:
            mid,d=q.pop(0)
            if mid in out or d>depth: continue
            m=self.media(mid)
            if not m: continue
            out[mid]=m
            if d==depth: continue
            for e in ((m.get("relations") or {}).get("edges") or []):
                if e.get("relationType") in {"SEQUEL","PREQUEL","SIDE_STORY","PARENT"}:
                    nid=(e.get("node") or {}).get("id")
                    if nid and nid not in out: q.append((nid,d+1))
        return list(out.values())
    def candidates(self,title,max_ep=0):
        found=self.search(title); pool=self.expand([m["id"] for m in found[:5]])
        scored=[]
        for m in pool:
            ts=max([sim(title,x) for x in titles(m)] or [0]); score=ts*100
            total=m.get("episodes")
            # Episode count is evidence, never a hard provider-season assumption.
            if total and max_ep:
                if max_ep<=total: score+=5
                else: score-=8
            scored.append((round(score,2),m,ts))
        return sorted(scored,key=lambda x:x[0],reverse=True)

    def candidates_any(self, queries, max_ep=0):
        """Search several provider-title variants and merge candidates by AniList ID.

        The similarity stored for each result is measured against the query that
        found it. This lets a Netflix franchise/root fallback rescue genuine anime
        without making an unrelated fuzzy AniList hit count as positive evidence.
        """
        merged={}
        for q in dict.fromkeys(x for x in queries if x):
            for score,m,ts in self.candidates(q,max_ep):
                mid=m.get("id")
                prev=merged.get(mid)
                item=(score,m,ts,q)
                if prev is None or (ts,score)>(prev[2],prev[0]): merged[mid]=item
        return sorted(merged.values(),key=lambda x:(x[2],x[0]),reverse=True)

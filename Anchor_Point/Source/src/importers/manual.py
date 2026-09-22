import json
from pathlib import Path

def add_manual(path, title, season=1, progress=None, source="amazon"):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    data={"entries":[]}
    if p.exists():
        try: data=json.loads(p.read_text(encoding="utf-8"))
        except Exception: pass
    entry={"source":source,"title":title,"season":int(season),"progress":None if progress is None else int(progress)}
    # Replace same source/title/season rather than duplicate it.
    data["entries"]=[x for x in data.get("entries",[]) if not (x.get("source")==source and x.get("title")==title and int(x.get("season",1))==int(season))]
    data["entries"].append(entry)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return entry

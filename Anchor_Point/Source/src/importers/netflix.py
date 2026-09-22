import csv, json, re
from datetime import datetime
from pathlib import Path


def _date_iso(value: str) -> str | None:
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except Exception:
            pass
    return None


def parse_netflix_title(title: str) -> dict:
    """Normalize a Netflix ViewingActivity label into a likely series label.

    Netflix TV rows are usually one of:
      Series: Episode title
      Series: Season N: Episode title
      Series: Franchise subtitle: Episode title
      Series: Franchise subtitle: Arc: Episode title

    We keep season/arc/franchise information when it is useful for AniList, while
    removing the final episode-title component. The raw label is always retained.
    """
    raw=(title or "").strip()
    parts=[p.strip() for p in raw.split(":") if p.strip()]
    season=1
    for p in parts[1:-1]:
        m=re.fullmatch(r"(?i)season\s+(\d+)",p)
        if m:
            season=int(m.group(1)); break

    if len(parts) <= 1:
        series=raw
    elif len(parts) == 2:
        # Most two-part rows are Series: Episode. Preserve obvious Netflix catalog
        # metadata/franchise labels so AniList fallback searches can use them.
        qualifier=parts[1]
        roman_catalog=bool(re.search(r"(?i)\b(?:II|III|IV|V|VI|VII|VIII|IX|X)\s*$",qualifier))
        metadata=bool(re.fullmatch(r"(?i)(?:limited series|season\s+\d+|part\s+\d+|cour\s+\d+)",qualifier))
        if roman_catalog or metadata:
            series=raw
        else:
            series=parts[0]
    else:
        # Keep all metadata before the final episode title, then strip a plain
        # "Season N" suffix because the numeric season is stored separately.
        meta=parts[:-1]
        if len(meta) >= 2 and re.fullmatch(r"(?i)season\s+\d+",meta[-1]):
            meta=meta[:-1]
        series=": ".join(meta)

    return {"series_title":series or raw,"season":season,"raw_title":raw}


def series_candidates(title: str) -> list[str]:
    """Return progressively broader AniList search labels for a Netflix row/group.

    Netflix frequently inserts franchise, cour, arc, or catalog labels that are
    not the exact AniList title. We therefore try the normalized label first and
    then progressively remove right-most qualifiers. This is a search strategy,
    not an anime classification decision.
    """
    parsed=parse_netflix_title(title)
    series=parsed["series_title"]
    out=[series]

    # Netflix's "Limited Series" is catalog metadata, not part of the anime title.
    series=re.sub(r"(?i)\s*:\s*limited series\s*$", "", series).strip()
    if series and series not in out: out.append(series)

    parts=[p.strip() for p in series.split(":") if p.strip()]
    # Repeated franchise labels such as "Black Clover: Black Clover III" should
    # also search the franchise root. Roman-numeral/cour information remains in
    # the more-specific first query and can be used during review.
    while len(parts)>1:
        parts=parts[:-1]
        out.append(": ".join(parts))

    # A few Netflix labels use a dash as a catalog qualifier.
    if " - " in series:
        out.append(series.split(" - ",1)[0].strip())
    return list(dict.fromkeys(x for x in out if x))


def load_netflix_csv(path: str | Path) -> list[dict]:
    rows=[]
    with open(path,newline="",encoding="utf-8-sig") as f:
        for i,r in enumerate(csv.DictReader(f),1):
            title=(r.get("Title") or "").strip()
            if not title: continue
            parsed=parse_netflix_title(title)
            rows.append({"raw_title":title,"date":_date_iso(r.get("Date") or ""),
                         "series_title":parsed["series_title"],"season":parsed["season"],
                         "candidates":series_candidates(title),"row":i})
    return rows


def save_netflix_json(csv_path: str | Path, out_path: str | Path) -> int:
    rows=load_netflix_csv(csv_path)
    p=Path(out_path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"source":"netflix","views":rows},ensure_ascii=False,indent=2),encoding="utf-8")
    return len(rows)

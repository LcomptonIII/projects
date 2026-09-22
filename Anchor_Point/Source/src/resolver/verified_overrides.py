"""Narrow provider-to-AniList corrections verified against AniList catalog metadata.

These are intentionally exact (source, normalized provider title, provider season)
keys. They repair catalog/provider metadata pathologies without changing generic
resolver scoring. Raw history remains untouched and every correction is auditable.
"""
from .franchise import norm

# (source, normalized provider title, provider season) -> AniList media metadata
VERIFIED_PROVIDER_OVERRIDES = {
    ('crunchyroll', norm('Witch Hat Atelier'), 1): (147105, 'Witch Hat Atelier', 13),
    ('crunchyroll', norm('ROLL OVER AND DIE'), 1): (191718, 'ROLL OVER AND DIE: I Will Fight for an Ordinary Life with My Love and Cursed Sword!', 12),
    ('crunchyroll', norm('Jack-of-All-Trades, Party of None'), 1): (187264, 'Jack-of-All-Trades, Party of None', 12),
    ('crunchyroll', norm('In Another World With My Smartphone'), 2): (147571, 'In Another World With My Smartphone 2', 12),
    ('crunchyroll', norm("Knight’s & Magic"), 1): (97663, "Knight's & Magic", 13),
    ('crunchyroll', norm('The Too-Perfect Saint: Tossed Aside by My Fiancé and Sold to Another Kingdom'), 1): (183275, 'The Too-Perfect Saint: Tossed Aside by My Fiancé and Sold to Another Kingdom', 12),
    ('crunchyroll', norm('The Unaware Atelier Meister'), 1): (183133, 'The Unaware Atelier Meister', 12),
    # Crunchyroll exposes S2 episodes as cumulative 13-25 and labels this bucket season 3.
    ('crunchyroll', norm('Solo Leveling'), 3): (176496, 'Solo Leveling Season 2 -Arise from the Shadow-', 13),
    ('crunchyroll', norm('Magi'), 1): (14513, 'Magi: The Labyrinth of Magic', 25),
    # Crunchyroll's provider season counter is not the AniList season/cour number.
    ('crunchyroll', norm('Dr. STONE'), 6): (199221, 'Dr. STONE: SCIENCE FUTURE Part 3', 13),
    ('crunchyroll', norm('Code Geass'), 1): (1575, 'Code Geass: Lelouch of the Rebellion', 25),
    ('crunchyroll', norm('The Misfit of Demon King Academy'), 2): (130588, "The Misfit of Demon King Academy Ⅱ: History's Strongest Demon King Reincarnates and Goes to School with His Descendants", 12),
    ('crunchyroll', norm('Rascal Does Not Dream Series'), 1): (171046, 'Rascal Does Not Dream of Santa Claus', 13),
    # Crunchyroll's current Hunter x Hunter catalog is the 2011 adaptation; its
    # language/packaging buckets can be labelled as provider season 5.
    ('crunchyroll', norm('Hunter x Hunter'), 5): (11061, 'Hunter x Hunter (2011)', 148),
    # Crunchyroll's 2026 provider bucket 5 is a re-release/repackage of the
    # original KONOSUBA season; episode 1 is the original series premiere.
    ('crunchyroll', norm("Konosuba - God's Blessing on This Wonderful World!"), 5): (21202, "KONOSUBA -God's blessing on this wonderful world!", 10),
    # Netflix title 81239555 is the 2021 remake, not the 2001 adaptation.
    ('netflix', norm('SHAMAN KING'), 1): (119675, 'SHAMAN KING (2021)', 52),
    # Netflix embeds the franchise title before the actual sequel title.
    ('netflix', norm('Overlord: Overlord II'), 1): (98437, 'Overlord II', 13),
    ('netflix', norm('Overlord: Overlord III'), 1): (101474, 'Overlord III', 13),
}

VERIFIED_NON_ANIME = {
    # Netflix's German live-action series Dark, not anime. The old AniList ID
    # 3393 candidate was a false exact-title collision and is no longer valid.
    ('netflix', norm('Dark'), 1): 'Verified Netflix live-action title; exclude from AniList anime sync',
}

def apply_verified_override(row):
    key=(row.get('source',''), norm(row.get('title','')), int(row.get('season') or 1))
    if key in VERIFIED_NON_ANIME:
        q=dict(row)
        q.update({'decision':'NOT_ANIME','anilist_id':'','anilist_title':'','anilist_episodes':'',
                  'reason':VERIFIED_NON_ANIME[key],'alternatives':''})
        return q
    hit=VERIFIED_PROVIDER_OVERRIDES.get(key)
    if not hit:
        return row
    media_id,title,episodes=hit
    progress=int(row.get('progress') or 0)
    # The override may identify the right entry, but it must never make impossible
    # progress writable. Preserve REVIEW in that unexpected case.
    decision='AUTO' if not episodes or progress <= episodes else 'REVIEW'
    q=dict(row)
    q.update({
        'decision':decision,
        'anilist_id':media_id,
        'anilist_title':title,
        'anilist_episodes':episodes,
        'reason':'verified provider/AniList catalog override' if decision=='AUTO' else 'verified override but progress exceeds selected entry',
        'alternatives':'',
    })
    return q

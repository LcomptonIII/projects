from src.resolver.franchise import episode_profile, split_overflow

def media(i,eps, sequel=None, fmt='TV'):
    edges=[] if sequel is None else [{'relationType':'SEQUEL','node':{'id':sequel}}]
    return {'id':i,'episodes':eps,'format':fmt,'title':{'english':f'Show {i}'},'relations':{'edges':edges}}

def test_cumulative_provider_numbering_becomes_local_progress():
    assert episode_profile(range(25,49))['local_progress']==24
    assert episode_profile(range(26,51))['local_progress']==25
    assert episode_profile([25])['local_progress']==1

def test_gap_uses_contiguous_tail():
    assert episode_profile([1,13,14,15,16,17,18])['local_progress']==6

def test_zero_bonus_does_not_inflate_progress():
    assert episode_profile([0,*range(49,73)])['local_progress']==24

def test_two_cour_split_11_plus_12():
    a=media(1,11,2); b=media(2,12)
    assert [(m['id'],p) for m,p in split_overflow(a,[a,b],23)]==[(1,11),(2,12)]

def test_two_part_split_13_plus_13():
    a=media(1,13,2); b=media(2,13)
    assert [(m['id'],p) for m,p in split_overflow(a,[a,b],26)]==[(1,13),(2,13)]

def test_special_not_silently_used_for_overflow():
    a=media(1,12,2); b=media(2,1,fmt='OVA')
    assert split_overflow(a,[a,b],13)==[]

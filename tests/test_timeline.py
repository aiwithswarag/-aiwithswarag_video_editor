import pytest
from swarag.timeline import keeps_from_silence, remap_items, validate_words, validate_keeps
from swarag.captions import safe_text, clock
from swarag.timeline import frame_aligned_keeps


def test_silence_padding_preserves_word_edges():
    log = 'silence_start: 0\nsilence_end: 1\nsilence_start: 3\nsilence_end: 5\nsilence_start: 9'
    assert keeps_from_silence(log,10,.15) == [[.85,3.15],[4.85,9.15]]


def test_cut_splits_effect_and_remaps_words():
    keeps = [[0,2],[4,8]]
    assert remap_items([{'start':1,'end':6,'fx':'orbit'}],keeps) == [
        {'start':1.,'end':2.,'fx':'orbit'},{'start':2.,'end':4.,'fx':'orbit'}]
    assert remap_items([{'w':'hello','s':5,'e':5.5}],keeps,'s','e') == [{'w':'hello','s':3.,'e':3.5}]


def test_silent_clip_cannot_disappear_successfully():
    with pytest.raises(ValueError): keeps_from_silence('silence_start: 0',10)


@pytest.mark.parametrize('data',[[{'w':'a','s':2,'e':1}],[{'w':'a','s':float('nan'),'e':3}],[{'w':'a','s':2,'e':3},{'w':'b','s':1,'e':2}]])
def test_bad_word_times_rejected(data):
    with pytest.raises(ValueError): validate_words(data)


def test_overlapping_cuts_rejected():
    with pytest.raises(ValueError): validate_keeps([[0,3],[2,5]],10)


def test_caption_control_sequences_are_literal():
    assert '{' not in safe_text(r'{\pos(0,0)}')
    assert '\\' not in safe_text(r'{\pos(0,0)}')
    assert clock(59.999) == '0:01:00.00'


def test_frame_alignment_expands_speech_edges_and_merges_touching_ranges():
    assert frame_aligned_keeps([[.111,.48],[.49,.991]],10,1)==[[.1,1]]


def test_compositing_order_survives_timeline_mapping():
    items=[{'fx':'lean-in','start':2,'end':4},{'fx':'backdrop-word','start':1,'end':5}]
    assert [x['fx'] for x in remap_items(items,[[0,6]],sort=False)]==['lean-in','backdrop-word']


def test_caption_cues_never_overlap(tmp_path):
    from swarag.captions import write_ass
    words=[{'w':f'word{i}','s':i*.2,'e':(i+1)*.2} for i in range(20)]
    output=tmp_path/'captions.ass'
    write_ass(output,words,width=1080,height=1920)
    events=[line.split(',') for line in output.read_text(encoding='utf-8-sig').splitlines() if line.startswith('Dialogue:')]
    for left,right in zip(events,events[1:]): assert left[2]<=right[1]

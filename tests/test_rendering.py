import json
from pathlib import Path
import numpy as np
import pytest
from swarag.effect_runner import engine, validate_effects, MaskCache, render
from swarag.runtime import ffmpeg, probe, executable
from swarag.pipeline import edit


def test_catalog_has_51_distinct_effects():
    assert len(engine().EFFECTS) == 51


def test_metrics_must_be_supplied():
    with pytest.raises(ValueError,match='real values'):
        validate_effects([{'fx':'liquid-glass-graph','start':0,'end':2}],3)


def test_cache_is_lossless_across_interleaved_reads():
    cache=MaskCache()
    try:
        a=np.arange(400,dtype=np.uint8).reshape(20,20)
        cache.put(0,a); cache.put(3,a[::-1])
        np.testing.assert_array_equal(cache.get(0),a)
        np.testing.assert_array_equal(cache.get(3),a[::-1])
        assert cache.get(8) is None
    finally: cache.close()


@pytest.fixture
def clip(tmp_path):
    try: executable('ffmpeg')
    except FileNotFoundError: pytest.skip('FFmpeg not installed')
    target=tmp_path/'input.mp4'
    ffmpeg(['-y','-f','lavfi','-i','testsrc2=s=240x426:r=12:d=3',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=3',
            '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',target])
    return target


def test_complete_cut_caption_audio_pipeline(clip,tmp_path):
    words=tmp_path/'words.json'
    words.write_text(json.dumps([{'w':'Local','s':.2,'e':.6},{'w':'render','s':2.2,'e':2.6}]))
    output=tmp_path/'output.mp4'
    report=edit({'input':str(clip),'output':str(output),'width':240,'fps':12,
                 'trim':{'keep':[[0,1],[2,3]]},'captions':{'words':str(words),'style':'emphasis'},
                 'audio':{'sfx':[{'kind':'click','at':2.1}],'normalize':True},'effects':[]})
    assert output.is_file() and report['caption_words']==2
    assert abs(probe(output)['duration']-2)<.12
    assert probe(output)['audio']
    timed=json.loads(output.with_suffix('.words.json').read_text())['words']
    assert timed[1]['s']==pytest.approx(1.2)
    with pytest.raises(FileExistsError): edit({'input':str(clip),'output':str(output)})


def test_renderer_rejects_source_overwrite(clip):
    with pytest.raises(ValueError,match='source'): render(clip,clip,[])


def test_encoder_failure_does_not_publish(clip,tmp_path,monkeypatch):
    import swarag.effect_runner as runner
    original=runner.verify_video
    def fail(*a,**kw): raise RuntimeError('verification failed')
    monkeypatch.setattr(runner,'verify_video',fail)
    target=tmp_path/'must-not-exist.mp4'
    with pytest.raises(RuntimeError,match='verification failed'):
        render(clip,target,[],width=240,fps=12)
    assert not target.exists()


def test_silent_video_and_padded_social_export(tmp_path):
    source=tmp_path/'silent.mp4'
    ffmpeg(['-y','-f','lavfi','-i','color=c=navy:s=320x180:r=12:d=1','-c:v','libx264',source])
    output=tmp_path/'finished.mp4'
    report=edit({'input':str(source),'output':str(output),'width':180,'captions':{'enabled':False},'exports':['square']})
    assert not probe(output)['audio']
    exported=probe(tmp_path/'finished_square.mp4')
    assert (exported['width'],exported['height'])==(1080,1080)


def test_music_and_sfx_mix_runs(clip,tmp_path):
    from swarag.audio import finish_audio
    music=tmp_path/'music.wav'
    ffmpeg(['-y','-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=1',music])
    output=tmp_path/'mix.wav'
    report=finish_audio(clip,output,3,{'music':str(music),'sfx':[{'kind':'whoosh','at':1},{'kind':'chime','at':2}]},tmp_path,True)
    assert report['normalized'] and output.stat().st_size>1000


def test_asymmetric_camera_keeps_face_in_frame():
    fx=engine(); c=fx.Ctx(); c.W=270; c.H=480; c.fx=135.;c.fy=230.;c.fw=80.
    c.img=np.zeros((480,270,3),np.float32); c.m=np.zeros((480,270),np.float32)
    fx.camera(c,2,65,230)
    assert c.fx-c.fw*.65>=0 and c.fx+c.fw*.65<=c.W


def test_invalid_effect_range_rejected():
    with pytest.raises(ValueError): validate_effects([{'fx':'orbit','start':2,'end':1}],3)


def test_tick_count_must_match_rows():
    with pytest.raises(ValueError,match='per row'):
        validate_effects([{'fx':'todo','start':0,'end':3,'text':'One|Two','ticks':'1'}],3)


def test_apple_toggles_obey_absolute_tick_time():
    fx=engine()
    def result(start,tick):
        c=fx.Ctx();c.W=270;c.H=480;c.fx=135.;c.fy=240.;c.fw=70.;c.lt=1.3;c.t=start+c.lt
        c.img=np.zeros((480,270,3),np.float32);c.m=np.zeros((480,270),np.float32)
        e=fx.Fx({'fx':'apple-toggles','start':start,'end':start+3,'text':'One','ticks':str(tick),'pos':'below'},12)
        fx.fx_apple_toggles(c,e)
        return c.img
    np.testing.assert_allclose(result(0,1),result(10,11))

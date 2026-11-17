"""Render every effect and named look against a supplied private test clip.

All numbers below are explicit technical-test values, not claims about a creator.
Outputs stay in the directory the caller supplies and must not be published as
finished creative work. Exit nonzero if any rendering or decoding fails.
"""
from pathlib import Path
import argparse
import json
import sys
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from swarag.effect_runner import engine, render
from swarag.runtime import probe, ffmpeg, write_json


def main():
    p=argparse.ArgumentParser(); p.add_argument('input'); p.add_argument('output'); p.add_argument('--width',type=int,default=270)
    p.add_argument('--only',nargs='*'); a=p.parse_args()
    directory=Path(a.output).resolve(); directory.mkdir(parents=True,exist_ok=True)
    duration=probe(a.input)['duration']
    entries=[(name,{'fx':name}) for name in engine().EFFECTS]
    entries += [('glitter-spotlight',{'fx':'glitter-spotlight'}),('cover-star-editorial',{'fx':'cover-star','look':'editorial'}),
                ('liquid-glass-graph-bento',{'fx':'liquid-glass-graph','look':'bento'}),
                ('glass-widgets-simple',{'fx':'glass-widgets','look':'simple'}),('apple-toggles-below',{'fx':'apple-toggles','pos':'below'})]
    results=[]
    for name,options in entries:
        if a.only and name not in a.only: continue
        item={'start':0,'end':duration,**options}
        if options['fx']=='profile-wall': item['count']=3
        if options['fx']=='liquid-glass-graph': item.update(text='TEST DATA',to='3',donut='30%::TEST',kpi='3::TEST',bars='1|2|3::TEST')
        if options['fx']=='over-the-shoulder-zoom': item.update(text='TEST A|TEST B',to='3|7')
        target=directory/f'{name}.mp4'
        try:
            report=render(a.input,target,[item],width=a.width,fps=12,overwrite=True)
            for moment in (.4,1.3,2.5):
                if moment>=duration: continue
                ffmpeg(['-v','error','-y','-ss',str(moment),'-i',target,'-frames:v','1',directory/f'{name}-{moment}.jpg'])
            results.append({'effect':name,'passed':True,'frames':report['frames'],'face_found':report['face_found']})
            print('PASS',name,flush=True)
        except Exception as exc:
            results.append({'effect':name,'passed':False,'error':str(exc)})
            print('FAIL',name,repr(exc),flush=True); traceback.print_exc()
        write_json(directory/'catalog-results.json',results)
    return int(any(not r['passed'] for r in results))

if __name__=='__main__': raise SystemExit(main())

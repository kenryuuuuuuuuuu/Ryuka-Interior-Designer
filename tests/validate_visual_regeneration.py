"""Integration acceptance: move a window in a COPY; regenerate Blender and UE.

Never changes the working tree's canonical data. Keeps the test package for review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--blender',required=True,type=Path)
    parser.add_argument('--engine',required=True,type=Path)
    parser.add_argument('--cache',required=True,type=Path)
    args=parser.parse_args()
    baseline=args.baseline.resolve(); out=args.output.resolve()
    if out.exists(): parser.error('Choose a new output directory.')
    source_hash=hashlib.sha256((ROOT/'data/openings.json').read_bytes()).hexdigest()
    fixture=out/'fixture'
    shutil.copytree(baseline/'inputs',fixture)
    window_file=fixture/'data/openings.json'
    data=read(window_file)
    window=next(o for o in data['items'] if o['id']=='op-006')
    window['offset']+=.1
    window_file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def run(command,cwd=ROOT):
        subprocess.run([str(v) for v in command],cwd=cwd,check=True)
    run(['node','scripts/build-web-data.mjs'],fixture)
    package=out/'updated-package'
    run([sys.executable,fixture/'scripts/build-visual-twin.py','--blender',args.blender,
         '--interior','--width',640,'--samples',16,'--output',package],fixture)
    before=read(baseline/'verification.json')['meshBoundsBlenderMetres']
    after=read(package/'verification.json')['meshBoundsBlenderMetres']
    key='opening.op-006.glass'
    delta=[b-a for a,b in zip(before[key],after[key])]
    assert all(abs(a-b)<1e-5 for a,b in zip(delta,[.1,0,0,.1,0,0])),delta
    for name in before:
        if name.startswith('furniture.'):
            assert before[name]==after[name],name
    old_study,new_study=read(baseline/'study.json'),read(package/'study.json')
    for key in ('camera','variants'):
        assert old_study['settings'][key]==new_study['settings'][key],key
    project=out/'unreal'
    run([sys.executable,ROOT/'scripts/build-unreal-study.py','--engine',args.engine,
         '--package',package,'--output',project,'--cache',args.cache.resolve()])
    assert hashlib.sha256((ROOT/'data/openings.json').read_bytes()).hexdigest()==source_hash
    result=dict(windowMovedMetres=.1,blenderBoundsDelta=delta,cameraAndPalettePreserved=True,
                canonicalSourceUnchanged=True,unreal=read(project/'import-verification.json'))
    (out/'regeneration-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Window update propagated through Blender and Unreal; canonical data unchanged.')


if __name__=='__main__': main()

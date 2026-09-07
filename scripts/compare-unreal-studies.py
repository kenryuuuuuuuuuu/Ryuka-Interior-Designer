"""Capture a fixed-camera finish/daylight matrix and create a local review gallery."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from solar_position import validate_cases, matches


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint(project):
    paths=list((project/'Content/Generated').rglob('*.uasset'))+list((project/'Content/Generated').rglob('*.umap'))
    paths += [project/name for name in ('study-state.json','import-verification.json','finish-settings.json',
               'sun-cases.json','site-context.json') if (project/name).exists()]
    return {p.relative_to(project).as_posix():digest(p) for p in sorted(paths)}


def check_capture(report, case, variant, baseline=None):
    state=report['comparisonState']
    if not report.get('levelFileUnchanged') or state['variant']!=variant or not matches(case,state):
        raise ValueError('Capture does not match requested comparison conditions')
    if state.get('solar')!=case: raise ValueError('Solar provenance missing or changed')
    if baseline:
        for key in ('camera','sunLux','exposureEV100','roomId','siteContextSHA256'):
            if state.get(key)!=baseline['comparisonState'].get(key):
                raise ValueError('Comparison changed fixed condition: '+key)
        for key in ('finishSettingsSHA256','floorShaderSHA256','siteContext','width','height','hardwareRayTracingEnabled'):
            if report.get(key)!=baseline.get(key): raise ValueError('Comparison changed '+key)


def gallery(document):
    esc=lambda value:html.escape(str(value),quote=True)
    cards=[]
    for entry in document['captures']:
        if entry['status']!='complete': continue
        report=entry['report']; state=report['comparisonState']; solar=state['solar']
        label={'natural':'白壁・ナチュラルオーク','warm':'グレージュ・ウォルナット','reference':'石調の床・木板天井'}[state['variant']]
        precision='概算の位置・方位' if 'estimated' in (solar['locationStatus'],solar['northStatus']) else '位置・方位の入力確認済み'
        cards.append(f'<figure><a href="{esc(entry["image"])}"><img src="{esc(entry["image"])}" alt="{esc(label)}"></a>'
            f'<figcaption><strong>{esc(label)}</strong><br>{esc(solar["localTimestamp"])}'
            f'<br>太陽高度 {state["elevationDeg"]:.1f}° ／ 図面方位 {state["azimuthDeg"]:.1f}°'
            f'<br>{esc(precision)} ／ EV100 {state["exposureEV100"]:g}'
            f'<br><a href="{esc(entry["conditions"])}">撮影条件</a></figcaption></figure>')
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>ゲストLDK 内装・採光比較</title><style>body{font-family:system-ui,sans-serif;background:#f3f1ed;color:#292722;margin:0;padding:24px}'
        'main{max-width:1600px;margin:auto}h1{font-size:26px}p{line-height:1.7}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}'
        'figure{margin:0;background:white;border-radius:10px;overflow:hidden}img{display:block;width:100%}figcaption{padding:16px;line-height:1.7}'
        'a{color:#415f70}@media(max-width:800px){.grid{grid-template-columns:1fr}}@media print{figure{break-inside:avoid}body{padding:0}}</style>'
        '<main><h1>ゲストLDK 内装・採光比較</h1><p><strong>'+esc(document.get('note','実敷地との対応は未確認です。'))+'</strong></p><p>同じ視点・光源強度・露出で比較しています。'
        '同じ日時の仕上げ違いを並べています。画像を選ぶと原寸で開きます。</p>'
        '<p>仮仕上げによる比較です。日時・位置・方位の確度は各画像に表示しています。'
        '天候・ガラス透過率・室内照度は未校正です。所在地に関わる条件を含むため、このフォルダはローカルで保管してください。</p>'
        '<div class="grid">'+''.join(cards)+'</div><p><a href="comparison.json">比較条件と検証記録</a></p></main></html>')


def write_manifest(output,document):
    path=output/'comparison.json'; temp=output/'comparison.tmp'
    temp.write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',type=Path,required=True)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--note',default='実敷地との対応は未確認です。',help='Visible note identifying sample/site conditions')
    parser.add_argument('--sun-cases',type=int,nargs='+',help='Zero-based case indices; defaults to all usable cases')
    parser.add_argument('--variants',choices=('natural','warm','reference'),nargs='+',default=['natural','warm'])
    args=parser.parse_args()
    project=args.project.resolve(); output=args.output.resolve()
    if not output.is_relative_to(ROOT/'build'): parser.error('Keep comparison output inside this worktree build/.')
    if output.exists(): parser.error('Output exists; choose a new directory.')
    cases=validate_cases(read(project/'sun-cases.json'))['cases']
    indices=args.sun_cases if args.sun_cases is not None else [i for i,c in enumerate(cases) if c['usable']]
    if not indices or len(set(indices))!=len(indices) or any(not 0<=i<len(cases) or not cases[i]['usable'] for i in indices):
        parser.error('Choose unique, usable solar case indices.')
    if len(set(args.variants))!=len(args.variants) or len(indices)*len(args.variants)>24:
        parser.error('Choose unique variants and at most 24 images per batch.')
    if not (args.engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe').is_file(): parser.error('Unreal engine not found.')
    imported=read(project/'import-verification.json')
    if not imported.get('unrealImportVerified'): parser.error('Verified project required.')
    before=fingerprint(project)
    prefix='matrix-'+uuid.uuid4().hex[:12]
    document=dict(schemaVersion='1.0.0',status='running',siteDaylightCalibrated=False,note=args.note,
                  projectFingerprint=before,sourceManifestSHA256=imported['sourceManifestSHA256'],captures=[])
    for i in indices:
        for variant in args.variants:
            name=f'{prefix}-{i}-{variant}'
            document['captures'].append(dict(caseIndex=i,variant=variant,name=name,status='pending'))
    output.mkdir(parents=True); write_manifest(output,document)
    baseline=None
    try:
        for count,entry in enumerate(document['captures'],1):
            print(f'[{count}/{len(document["captures"])}] case {entry["caseIndex"]} / {entry["variant"]}',flush=True)
            if fingerprint(project)!=before: raise RuntimeError('Project changed during comparison')
            subprocess.run([sys.executable,str(ROOT/'scripts/capture-unreal-study.py'),'--engine',str(args.engine),
                '--project',str(project),'--cache',str(args.cache),'--name',entry['name'],'--variant',entry['variant'],
                '--sun-case',str(entry['caseIndex'])],check=True)
            report=read(project/'Saved'/(entry['name']+'.json'))
            source=project/'Saved'/(entry['name']+'.png')
            conditions=project/'Saved'/(entry['name']+'-conditions.json')
            if digest(source)!=report['imageSHA256'] or digest(conditions)!=report['conditionsSHA256']:
                raise RuntimeError('Capture artifact checksum mismatch')
            check_capture(report,cases[entry['caseIndex']],entry['variant'],baseline)
            if fingerprint(project)!=before: raise RuntimeError('Project changed during capture')
            baseline=baseline or report
            stem=f'case-{entry["caseIndex"]}-{entry["variant"]}'
            shutil.copy2(source,output/(stem+'.png')); shutil.copy2(conditions,output/(stem+'.json'))
            entry.update(status='complete',image=stem+'.png',conditions=stem+'.json',report=report)
            write_manifest(output,document)
        document['status']='complete'
        (output/'index.html').write_text(gallery(document),encoding='utf-8')
        write_manifest(output,document)
    except Exception as error:
        document.update(status='failed',error=str(error)); write_manifest(output,document)
        raise
    print(output/'index.html')


if __name__=='__main__': main()

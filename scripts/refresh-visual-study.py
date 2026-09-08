"""Regenerate Blender and Unreal from current source, retaining a saved study."""
import argparse
from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
sys.path.insert(0,str(ROOT/'scripts'))
from finish_settings import validate_finishes
from refresh_inputs import read, sha, retained_inputs, scenario_inputs
import source_changes
import surface_registry


def sources():
    result={}
    for folder in ('data','blender','unreal','scripts','generated','tests'):
        for path in (ROOT/folder).rglob('*'):
            if path.is_file() and path.suffix in ('.json','.py','.mjs','.js','.hlsl','.ini','.uproject','.cpp','.h','.cs'):
                result[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    return result


def save(output,report):
    temp=output/'refresh.tmp'
    temp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(output/'refresh.json')


def summary(report):
    esc=lambda s:html.escape(str(s),quote=True)
    changes=''.join('<li>'+esc(name)+'</li>' for name in report['changedSourceFiles'])
    links='<li><a href="blender/interior.blend">Blenderモデル</a></li><li><a href="ue/RyukaInterior.uproject">Unrealプロジェクト</a></li>'
    if report['gallery']: links+='<li><a href="comparison/index.html">日時・仕上げの比較一覧</a></li>'
    scenario_html=''
    selected=report.get('selectedScenario')
    if selected:
        note_html=('<br>メモ：'+esc(selected['note'])) if selected.get('note') else ''
        scenario_html=('<p>選択した案「'+esc(selected['name'])+'」の比較条件を、'
            '現在の建物にこの案の比較条件を適用しました。'+note_html+'</p>')
    src=report.get('sourceChanges')
    source_changes_html=''
    if src:
        if src['baselineStatus']=='available':
            s=src['summary']
            parts=[]
            for label,key in (('部屋','rooms'),('家具','furniture'),('家具カタログ','catalog')):
                c=s.get(key)
                if c: parts.append(f'{esc(label)}：追加{c["added"]}・削除{c["removed"]}・変更{c["modified"]}')
            source_changes_html=('<h2>前回モデルからの変更</h2><p>'+'、'.join(parts)+
                '。<a href="'+esc(src['htmlPath'])+'">詳細</a></p>')
        else:
            source_changes_html=('<h2>前回モデルからの変更</h2><p>前回との詳細比較はできませんでした（'
                +esc(src.get('baselineReason',''))+'）。<a href="'+esc(src['htmlPath'])+'">詳細</a></p>')
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>内装シミュレーション更新結果</title><style>body{font:16px/1.8 system-ui;max-width:960px;margin:40px auto;padding:0 20px;background:#f5f3ef;color:#292722}a{color:#365d70}</style>'
        '<h1>内装シミュレーションの更新が完了しました</h1><p>'+esc(report['note'])+'</p>'+scenario_html+
        '<p>保存済みの仕上げ・視点・太陽条件を引き継ぎ、現在の正本から建物を再生成しました。'
        '実敷地への適用と室内照度の校正は別途確認が必要です。</p><ul>'+links+'</ul>'
        '<p>Unrealの「ツール → 内装比較」で条件を変更できます。変更を次回へ残すには「比較条件とレベルを保存」を使ってください。</p>'
        +source_changes_html+
        '<h2>前回パッケージから変わった入力ファイル</h2><ul>'+changes+'</ul>'
        '<p><a href="refresh.json">工程・入力・引き継ぎの検証記録</a></p></html>')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',type=Path,required=True,help='Previously generated UE project directory')
    parser.add_argument('--output',type=Path,required=True,help='New directory within this worktree build/')
    parser.add_argument('--blender',type=Path,default=Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'))
    parser.add_argument('--engine',type=Path,default=Path('C:/Program Files/Epic Games/UE_5.8'))
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--gallery',action='store_true',help='Also capture all usable solar cases with both finishes')
    parser.add_argument('--note',default='実敷地の位置・真北・採用品番は確認待ちです。')
    parser.add_argument('--scenario',type=Path,help='Saved named scenario directory (see save-study-scenario.py); '
        'overrides retained study state/sun-cases/site-context from --previous')
    args=parser.parse_args()
    output=args.output.resolve(); previous=args.previous.resolve()
    if not output.is_relative_to(ROOT/'build'): parser.error('Output must be within this worktree build/.')
    if output.exists(): parser.error('Output exists; choose a new directory. Previous studies are never overwritten.')
    if not args.blender.is_file() or not (args.engine/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe').is_file():
        parser.error('Blender or Unreal not found; specify --blender and --engine.')
    if len(str(args.cache.resolve()))>119: parser.error('Cache path must be at most 119 characters.')
    if shutil.which('node') is None: parser.error('Node is required.')
    validate_finishes(read(ROOT/'data/visual/unreal-finishes.json'))
    prev_report=read(previous/'import-verification.json')
    if not prev_report.get('unrealImportVerified'): parser.error('Previous project must have a successful import report')
    scenario=None; scenario_dir=None
    if args.scenario:
        # --scenario reads state/sun-cases/site-context only from the saved
        # package, never from --previous's own saved state: an unrelated
        # broken or mid-recovery runtime save sitting in --previous must not
        # be able to block reapplying a valid, independently-verified scenario.
        scenario_dir=args.scenario.resolve()
        if not scenario_dir.is_dir(): parser.error('Scenario directory not found: '+str(scenario_dir))
        retained,scenario=scenario_inputs(scenario_dir,args.gallery)
    else:
        retained=retained_inputs(previous,args.gallery)
    before=sources(); retained_hashes={k:sha(v) for k,v in retained.items()}
    old=read(previous/'SourcePackage/manifest.json')['sourceHashes']
    changed=sorted(k for k in set(old)|set(before) if old.get(k)!=before.get(k))
    report=dict(schemaVersion='1.0.0',status='running',startedAt=datetime.now().astimezone().isoformat(),
        note=args.note,gallery=args.gallery,siteDaylightCalibrated=False,sourceHashes=before,
        changedSourceFiles=changed,retainedHashes=retained_hashes,steps=[])
    if scenario:
        report['selectedScenario']=dict(id=scenario['id'],name=scenario['name'],note=scenario.get('note',''),
            scenarioSHA256=sha(scenario_dir/'scenario.json'),origin=scenario['origin'])
    output.mkdir(parents=True); saved=output/'retained'; saved.mkdir()
    for key,path in retained.items(): shutil.copy2(path,saved/('study-state.json' if key=='state' else path.name))
    if scenario: shutil.copy2(scenario_dir/'scenario.json',saved/'scenario.json')
    save(output,report)
    def unchanged():
        if sources()!=before: raise RuntimeError('Source files changed during regeneration; use a new output after edits finish')
        if any(sha(retained[k])!=h for k,h in retained_hashes.items()):
            raise RuntimeError('Previous saved conditions changed during regeneration')
        if any(sha(saved/('study-state.json' if k=='state' else retained[k].name))!=h for k,h in retained_hashes.items()):
            raise RuntimeError('Retained condition snapshot changed during regeneration')
    def run(name,command):
        step=dict(name=name,status='running'); report['steps'].append(step); save(output,report)
        print(name,flush=True)
        try:
            unchanged()
            with (output/(name+'.log')).open('w',encoding='utf-8') as log:
                result=subprocess.run([str(x) for x in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode: raise RuntimeError('Step failed: '+name+'; inspect '+name+'.log')
            unchanged()
        except Exception:
            step['status']='failed'
            raise
        step['status']='complete'; save(output,report)
    try:
        # Verify browser-derived data first; never silently rewrite tracked outputs.
        run('01-source-check',['node',ROOT/'scripts/build-web-data.mjs','--check'])
        # Compare --previous's frozen inputs against the current source, and
        # check the current source's cross-file references, before Blender
        # starts. --previous is always the comparison basis, even with
        # --scenario (a scenario's origin is a separate, already-recorded
        # thing -- see W03-A -- not what "changed since" means here).
        step=dict(name='01b-source-changes',status='running'); report['steps'].append(step); save(output,report)
        changes=source_changes.compare(previous,ROOT)
        (output/'source-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (output/'changes.html').write_text(source_changes.render_html(changes),encoding='utf-8')
        report['sourceChanges']=dict(baselineStatus=changes['baselineStatus'],baselineReason=changes.get('baselineReason'),
            summary=source_changes.summarize(changes),jsonPath='source-changes.json',htmlPath='changes.html')
        save(output,report)
        if changes['issues']:
            step['status']='failed'; save(output,report)
            raise RuntimeError('Current source has unresolved reference issues; inspect '+str(output/'changes.html'))
        step['status']='complete'; save(output,report)
        # Persistent surface IDs (W03-C): resolved purely against the current
        # source, independent of --previous/--scenario. An unresolved
        # registered surface (moved/split wall, deleted room) stops here,
        # before Blender, the same way a reference issue does above.
        step=dict(name='01c-surface-registry',status='running'); report['steps'].append(step); save(output,report)
        surfaces=surface_registry.resolve_from(ROOT)
        (output/'surface-resolution.json').write_text(json.dumps(surfaces,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        report['surfaceRegistry']=dict(issueCount=len(surfaces['issues']),jsonPath='surface-resolution.json')
        save(output,report)
        if surfaces['issues']:
            step['status']='failed'; save(output,report)
            raise RuntimeError('Current surface registry has unresolved entries; inspect '+str(output/'surface-resolution.json'))
        step['status']='complete'; save(output,report)
        # --state (not just --variant) so Blender also reflects surfaceOverrides
        # (W04); build_interior.py uses state.variant over --variant when both
        # are given, so --variant here is only a readable fallback/log value.
        run('02-blender',[sys.executable,ROOT/'scripts/build-visual-twin.py','--blender',args.blender,
            '--interior','--output',output/'blender','--variant',read(saved/'study-state.json')['variant'],
            '--state',saved/'study-state.json'])
        command=[sys.executable,ROOT/'scripts/build-unreal-study.py','--engine',args.engine,
            '--package',output/'blender','--output',output/'ue','--cache',args.cache,
            '--state',saved/'study-state.json']
        for key,flag in [('sunCases','--sun-cases'),('context','--context')]:
            if key in retained: command += [flag,saved/retained[key].name]
        run('03-unreal',command)
        if (previous/'walkthrough.json').exists():
            run('04-walkthrough',[sys.executable,ROOT/'scripts/enable-unreal-walkthrough.py','--engine',args.engine,'--project',output/'ue','--cache',args.cache])
        run('04-state-check',[sys.executable,ROOT/'tests/validate_study_transfer.py',
            '--state',saved/'study-state.json','--project',output/'ue'])
        if args.gallery:
            run('05-comparison',[sys.executable,ROOT/'scripts/compare-unreal-studies.py',
                '--engine',args.engine,'--project',output/'ue','--cache',args.cache,
                '--output',output/'comparison','--note',args.note])
        unchanged()
        report['status']='complete'; report['completedAt']=datetime.now().astimezone().isoformat()
        report['unrealVerification']=read(output/'ue/import-verification.json')
        report['stateVerification']=read(output/'ue/state-transfer-verification.json')
        (output/'index.html').write_text(summary(report),encoding='utf-8')
        save(output,report)
    except Exception as error:
        report.update(status='failed',error=str(error)); save(output,report)
        raise
    print(output/'index.html')


if __name__=='__main__': main()

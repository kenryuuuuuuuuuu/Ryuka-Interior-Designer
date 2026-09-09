"""Create an isolated Unreal editor study from a verified Blender package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from study_state import default_state, validate_state
from solar_position import validate_cases, validate_site, cases_match_site, case_matches_site
from site_context import validate_context
from finish_settings import validate_finishes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine',type=Path,required=True,help='UE installation directory')
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='New project directory; never overwrite')
    parser.add_argument('--cache',type=Path,required=True,help='Writable DDC path, at most 119 characters')
    parser.add_argument('--sun-lux',type=float,default=50000,help='Provisional UE light intensity')
    parser.add_argument('--exposure-ev100',type=float,default=7.5,help='Fixed UE exposure (not Blender EV)')
    parser.add_argument('--state',type=Path,help='Saved study-state.json; overrides finish, light, exposure and camera')
    parser.add_argument('--sun-cases',type=Path,help='Local solar case list from plan-sun-study.py')
    parser.add_argument('--site',type=Path,help='Local site input (lat/long/plan-north); see solar_position.validate_site()')
    parser.add_argument('--context',type=Path,help='Local neighbouring buildings/walls; box approximations')
    args=parser.parse_args()
    validate_finishes(json.loads((ROOT/'data/visual/unreal-finishes.json').read_text(encoding='utf-8')))
    sun_cases=None
    site=None
    if args.sun_cases: sun_cases=validate_cases(json.loads(args.sun_cases.read_text(encoding='utf-8')))
    if args.site:
        site=validate_site(json.loads(args.site.read_text(encoding='utf-8-sig')))
        # W05: same rule as refresh_inputs.py -- a site input that doesn't
        # match the sun-cases it is generated alongside would silently make
        # every "date" comparison show the wrong angles for this project.
        if sun_cases and not cases_match_site(sun_cases['cases'],site):
            parser.error('--site does not match --sun-cases; regenerate the cases for this site first (plan-sun-study.py)')
    if args.context:
        if not args.context.resolve().is_relative_to(ROOT/'build') or not args.output.resolve().is_relative_to(ROOT/'build'):
            parser.error('Keep context inputs and generated projects within this worktree build/.')
        validate_context(json.loads(args.context.read_text(encoding='utf-8-sig')))
    exe=args.engine.resolve()/'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    output=args.output.resolve(); package=args.package.resolve(); cache=args.cache.resolve()
    if not exe.is_file(): parser.error('UnrealEditor-Cmd.exe not found.')
    if output.exists(): parser.error('Output exists. Choose a new project directory.')
    if len(str(cache))>119: parser.error('Unreal filesystem DDC requires a cache path of at most 119 characters.')
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    for name,info in manifest['artifacts'].items():
        if hashlib.sha256((package/name).read_bytes()).hexdigest()!=info['sha256']:
            parser.error('Package artifact checksum mismatch: '+name)
    verified=json.loads((package/'verification.json').read_text(encoding='utf-8'))
    if not verified.get('meshBoundsBlenderMetres'): parser.error('Rebuild package with current Blender verifier.')
    study=json.loads((package/'study.json').read_text(encoding='utf-8'))
    if args.state:
        saved=validate_state(json.loads(args.state.read_text(encoding='utf-8')),study)
        if saved.get('siteContextSHA256') and not args.context:
            parser.error('This saved state used site context. Supply --context to preserve surrounding shade geometry.')
        # W05-v1 review R1: same contract as the editor/refresh paths -- a
        # --state whose own solar case does not match --site must not be
        # silently accepted (e.g. a state saved before the site was changed).
        if site is not None and saved.get('solar') is not None and not case_matches_site(saved['solar'],site):
            parser.error("--state's solar case does not match --site; reapply a current-site datetime case before saving that state")
    else:
        default_state(study,dict(sunLux=args.sun_lux,exposureEV100=args.exposure_ev100))
    shutil.copytree(ROOT/'unreal/template',output)
    shutil.copytree(package,output/'SourcePackage')
    shutil.copy2(ROOT/'unreal/import_study.py',output/'import_study.py')
    shutil.copy2(ROOT/'unreal/floor_finish.hlsl',output/'floor_finish.hlsl')
    shutil.copy2(ROOT/'unreal/surface_finish.hlsl',output/'surface_finish.hlsl')
    scripts=output/'Content/Python'; scripts.mkdir(parents=True,exist_ok=True)
    # UE adds <Project>/Content/Python to sys.path for all editor Python
    # execution, so import_study.py (run once, from the project root, via the
    # commandlet) can import these too without a separate root-level copy.
    for name in ('study_controls.py','study_state.py','solar_position.py','site_context.py',
                 'finish_settings.py','material_builder.py','surface_finish_overrides.py','lighting.py'):
        shutil.copy2(ROOT/'unreal'/name,scripts/name)
    (scripts/'init_unreal.py').write_text('import study_controls\nstudy_controls.register_menu()\n',encoding='utf-8')
    # W04: lets study_controls.py's menu (named-scenario save/list/A-B) shell
    # out to this worktree's scripts/*.py, which the generated project itself
    # has no other reference to (it is a standalone copy).
    (output/'repo-root.json').write_text(json.dumps(dict(root=str(ROOT)))+'\n',encoding='utf-8')
    shutil.copy2(ROOT/'data/visual/unreal-finishes.json',output/'finish-settings.json')
    shutil.copy2(ROOT/'data/visual/lighting-settings.json',output/'lighting-settings.json')
    if args.state: shutil.copy2(args.state,output/'study-state.json')
    if args.sun_cases: shutil.copy2(args.sun_cases,output/'sun-cases.json')
    if args.site: shutil.copy2(args.site,output/'site.local.json')
    if args.context: shutil.copy2(args.context,output/'site-context.json')
    (output/'import-job.json').write_text(json.dumps(dict(sunLux=args.sun_lux,
        exposureEV100=args.exposure_ev100),indent=2)+'\n',encoding='utf-8')
    cache.mkdir(parents=True,exist_ok=True)
    # Commandlet Python unescapes backslashes (e.g. \\r); always pass forward-slash paths.
    command=[str(exe),(output/'RyukaInterior.uproject').as_posix(),'-run=pythonscript',
             '-script='+(output/'import_study.py').as_posix(),'-unattended','-NullRHI','-NoSound',
             '-nosplash','-NoSourceControl','-DDC=InstalledNoZenLocalFallback','-LocalDataCachePath='+cache.as_posix()]
    with (output/'import.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=output,stdout=log,stderr=subprocess.STDOUT,
            env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    report=output/'import-verification.json'
    if result.returncode or not report.is_file():
        raise RuntimeError(f'Unreal import failed. Inspect {output / "import.log"}; source package is untouched.')
    print(report.read_text(encoding='utf-8'))
    print('Project: '+str(output/'RyukaInterior.uproject'))


if __name__=='__main__': main()

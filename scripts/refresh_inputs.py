"""Shared input selection/validation for refresh-visual-study.py and
save-study-scenario.py. Extracted so both tools apply the exact same rules for
which saved comparison state is valid and safe to use -- no logic is
duplicated between them.
"""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
# Separate name for save_scenario_package()'s "is this output path allowed"
# confinement check specifically: a test can mock just SCENARIO_ROOT to
# redirect where scenarios are allowed to be written, without also
# redirecting ROOT (which retained_inputs()/scenario_inputs() use to read
# real repo fixtures like data/visual/guest-ldk-study.json and must not be
# faked out from under them).
SCENARIO_ROOT=ROOT
sys.path.insert(0,str(ROOT/'unreal'))
from study_state import validate_state
from solar_position import validate_cases
from site_context import validate_context

ALLOWED_SCENARIO_FILES=('study-state.json','sun-cases.json','site-context.json')


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def retained_inputs(previous, gallery=False):
    report=read(previous/'import-verification.json')
    if not report.get('unrealImportVerified'): raise ValueError('Previous study must have a successful import report')
    settings=read(ROOT/'data/visual/guest-ldk-study.json')
    state_path=previous/'study-state.json'
    runtime=previous/'Saved/walkthrough-state.json'
    # A runtime save mid-recovery (SaveView()'s final replace and its own
    # restore-from-backup both failed; see Walkthrough.cpp's
    # RecoverSaveIfNeeded) leaves exactly this disk signature: no current
    # save, but its .bak still present. Silently falling back to
    # study-state.json here would hide that from whoever is retaining/saving
    # from this state. This is only a presence check -- the actual recovery
    # stays exclusively in the C++ side, not duplicated here.
    if not runtime.exists() and (previous/'Saved/walkthrough-state.json.bak').exists():
        raise ValueError('Runtime save is mid-recovery (backup present, no current save); resolve it in Unreal (F9) first')
    if runtime.exists() and runtime.stat().st_mtime>state_path.stat().st_mtime: state_path=runtime
    state=validate_state(read(state_path),dict(roomId=settings['roomId'],settings=settings))
    paths={'state':state_path}
    if (previous/'sun-cases.json').exists():
        cases=validate_cases(read(previous/'sun-cases.json'))['cases']
        paths['sunCases']=previous/'sun-cases.json'
        if gallery and (not any(c['usable'] for c in cases) or sum(c['usable'] for c in cases)*2>24):
            raise ValueError('Gallery requires 1–12 usable solar cases')
    elif gallery:
        raise ValueError('The previous study has no solar cases for a comparison gallery')
    context=previous/'site-context.json'
    expected=state.get('siteContextSHA256')
    imported=report.get('siteContext')
    if context.exists():
        validate_context(read(context))
        if not expected: raise ValueError('Save comparison conditions with the current study controls before retaining site context')
        if expected and expected!=sha(context): raise ValueError('Context changed after saving the study; rebuild explicitly with --context first')
        if imported and imported['sha256']!=sha(context): raise ValueError('Context differs from the imported study')
        paths['context']=context
    elif expected or imported:
        raise ValueError('Previous study is missing required site-context.json')
    return paths


def scenario_inputs(scenario_dir, gallery=False):
    """Same shape/validation as retained_inputs(), but reading only from a saved
    scenario package (see save-study-scenario.py) -- never from a --previous
    project's own saved state, so an unrelated broken or mid-recovery runtime
    save there can never block reapplying a valid scenario. Returns
    (paths, scenario) where paths matches retained_inputs()'s shape."""
    scenario=read(scenario_dir/'scenario.json')
    if scenario.get('schemaVersion')!='1.0.0': raise ValueError('Unsupported scenario schema')
    files=scenario.get('files')
    if not isinstance(files,dict) or 'study-state.json' not in files: raise ValueError('Scenario is missing study-state.json')
    if not set(files)<=set(ALLOWED_SCENARIO_FILES): raise ValueError('Scenario references unexpected files')
    resolved={}
    for name,info in files.items():
        path=scenario_dir/name
        if not path.is_file(): raise ValueError(f'Scenario is missing {name}')
        if sha(path)!=info.get('sha256'): raise ValueError(f'Scenario file {name} does not match its recorded hash')
        resolved[name]=path
    settings=read(ROOT/'data/visual/guest-ldk-study.json')
    state=validate_state(read(resolved['study-state.json']),dict(roomId=settings['roomId'],settings=settings))
    paths={'state':resolved['study-state.json']}
    if 'sun-cases.json' in resolved:
        cases=validate_cases(read(resolved['sun-cases.json']))['cases']
        paths['sunCases']=resolved['sun-cases.json']
        if gallery and (not any(c['usable'] for c in cases) or sum(c['usable'] for c in cases)*2>24):
            raise ValueError('Gallery requires 1–12 usable solar cases')
    elif gallery:
        raise ValueError('The scenario has no solar cases for a comparison gallery')
    context_expected=state.get('siteContextSHA256')
    if 'site-context.json' in resolved:
        validate_context(read(resolved['site-context.json']))
        if context_expected!=sha(resolved['site-context.json']):
            raise ValueError('Scenario site context does not match its saved study state')
        paths['context']=resolved['site-context.json']
    elif context_expected:
        raise ValueError('Scenario is missing site context required by its saved study state')
    return paths, scenario


SCENARIO_SCHEMA = '1.0.0'


def save_scenario_package(project, name, note, output):
    """Save `project`'s current comparison scenario as a named package under
    `output` (must not exist, must be within this worktree's build/).
    Shared by scripts/save-study-scenario.py's CLI and the UE editor's
    save_scenario() (study_controls.py) -- both must apply the exact same
    validation and staging, and neither can rely on subprocess-invoking the
    other's file as a plain Python interpreter (W04 review R3: inside UE's
    embedded Python, sys.executable is UnrealEditor(-Cmd).exe itself, not a
    usable `python script.py` launcher). Returns (scenario, output)."""
    name = name.strip()
    if not name: raise ValueError('name must not be blank')
    if len(name) > 120: raise ValueError('name must be at most 120 characters')
    output = Path(output).resolve()
    if not output.is_relative_to(SCENARIO_ROOT/'build'): raise ValueError('Output must be within this worktree build/.')
    if output.exists(): raise ValueError('Output exists; scenarios are append-only, choose a new directory.')
    project = Path(project).resolve()

    # Same selection/validation refresh-visual-study.py uses: newest of
    # editor/runtime saves, schema/room/variant checked against current
    # settings, a mid-recovery runtime save (backup present, no current save)
    # refused rather than silently falling back. Raises ValueError with a
    # specific reason on any of those; this function does not catch it, so
    # the message reaches the caller directly and nothing partial is written.
    retained = retained_inputs(project)
    state = read(retained['state'])

    manifest_path = project/'SourcePackage/manifest.json'
    manifest = read(manifest_path) if manifest_path.is_file() else {}

    scenario = dict(schemaVersion=SCENARIO_SCHEMA, id=str(uuid.uuid4()), name=name, note=note,
        createdAt=datetime.now().astimezone().isoformat(), roomId=state['roomId'],
        origin=dict(sourceCommit=manifest.get('sourceCommit'), sourceHashes=manifest.get('sourceHashes', {}),
            stateSource='runtime' if retained['state'].parent.name == 'Saved' else 'editor'),
        files={})

    # Stage under a hidden temp name next to the target, then rename into
    # place -- a failure partway through never leaves a half-written
    # directory at the final `output` path.
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.parent/('.scenario-'+scenario['id'])
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        for key, path in retained.items():
            disk_name = 'study-state.json' if key == 'state' else path.name
            dest = staging/disk_name
            shutil.copy2(path, dest)
            scenario['files'][disk_name] = dict(sha256=sha(dest))
        # If any source file changed while copying, its post-copy hash (of
        # the original path, re-read now) will no longer match the hash we
        # just recorded from the copy -- catch that instead of returning a
        # scenario that may not match what the operator saw.
        for key, path in retained.items():
            disk_name = 'study-state.json' if key == 'state' else path.name
            if sha(path) != scenario['files'][disk_name]['sha256']:
                raise RuntimeError('Input changed while saving the scenario; rerun the command')
        (staging/'scenario.json').write_text(json.dumps(scenario, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return scenario, output

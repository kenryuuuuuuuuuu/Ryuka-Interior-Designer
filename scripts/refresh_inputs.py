"""Shared input selection/validation for refresh-visual-study.py and
save-study-scenario.py. Extracted so both tools apply the exact same rules for
which saved comparison state is valid and safe to use -- no logic is
duplicated between them.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
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

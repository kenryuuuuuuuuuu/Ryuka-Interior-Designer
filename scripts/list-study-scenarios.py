"""List saved comparison scenarios (see save-study-scenario.py) as a simple table."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def _room_summary(state):
    """W07-G1: a scenario's own saved study-state.json may still be any
    pre-2.0.0 schema (never rewritten by save-study-scenario.py -- the file
    on disk is copied byte-for-byte) as well as 2.0.0's roomStates shape;
    this is a plain listing tool, not a validator, so it reads whichever
    shape is actually there rather than requiring full migration first."""
    if 'roomStates' in state:
        return ','.join(f"{room_id}:{room_state.get('variant','?')}" for room_id,room_state in state['roomStates'].items())
    return f"{state.get('roomId','?')}:{state.get('variant','?')}"


def describe(folder):
    scenario=read(folder/'scenario.json')
    # 1.0.0 recorded a single roomId; 1.1.0 (W07-G1) records scopeId/roomIds
    # instead -- neither field is required here beyond display, so both are
    # accepted and whichever is present is shown.
    if scenario.get('schemaVersion') not in ('1.0.0','1.1.0'): raise ValueError('Unsupported scenario schema')
    for key in ('id','name','createdAt','files'):
        if key not in scenario: raise ValueError('Missing field: '+key)
    files=scenario['files']
    if 'study-state.json' not in files: raise ValueError('Scenario has no study-state.json entry')
    state=read(folder/'study-state.json')
    scope_label=scenario.get('scopeId') or scenario.get('roomId') or '?'
    return dict(id=scenario['id'],name=scenario['name'],createdAt=scenario['createdAt'],
        scope=scope_label,rooms=_room_summary(state),path=folder)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT/'build/scenarios')
    args=parser.parse_args()
    root=args.root.resolve()
    if not root.is_dir():
        print('(no scenarios: '+str(root)+' does not exist)')
        return
    rows=[]; errors=[]
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        try: rows.append(describe(folder))
        except Exception as error: errors.append((folder,error))
    if not rows and not errors:
        print('(no scenarios found under '+str(root)+')')
        return
    name_width=max([len(r['name']) for r in rows]+[4])
    if rows:
        print(f"{'id':36}  {'created':<25}  {'scope':<14}  {'name':<{name_width}}  rooms (roomId:variant)  path")
        for r in rows:
            print(f"{r['id']:36}  {r['createdAt']:<25}  {r['scope']:<14}  {r['name']:<{name_width}}  {r['rooms']}  {r['path']}")
    for folder,error in errors:
        print(f'[invalid] {folder}: {error}')


if __name__=='__main__': main()

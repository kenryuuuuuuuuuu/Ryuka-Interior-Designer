"""List saved comparison scenarios (see save-study-scenario.py) as a simple table."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def describe(folder):
    scenario=read(folder/'scenario.json')
    if scenario.get('schemaVersion')!='1.0.0': raise ValueError('Unsupported scenario schema')
    for key in ('id','name','createdAt','roomId','files'):
        if key not in scenario: raise ValueError('Missing field: '+key)
    files=scenario['files']
    if 'study-state.json' not in files: raise ValueError('Scenario has no study-state.json entry')
    state=read(folder/'study-state.json')
    return dict(id=scenario['id'],name=scenario['name'],createdAt=scenario['createdAt'],
        roomId=scenario['roomId'],variant=state.get('variant','?'),path=folder)


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
        print(f"{'id':36}  {'created':<25}  {'room':<12}  {'finish':<10}  {'name':<{name_width}}  path")
        for r in rows:
            print(f"{r['id']:36}  {r['createdAt']:<25}  {r['roomId']:<12}  {r['variant']:<10}  {r['name']:<{name_width}}  {r['path']}")
    for folder,error in errors:
        print(f'[invalid] {folder}: {error}')


if __name__=='__main__': main()

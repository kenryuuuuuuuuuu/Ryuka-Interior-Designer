"""Save the current comparison scenario (finish, camera, sun) from a generated
UE project as a named, reusable package under build/scenarios/. Does not
launch Blender or Unreal; only copies and validates small state files."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from refresh_inputs import read, sha, retained_inputs

SCHEMA='1.0.0'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True,help='Existing generated UE project directory')
    parser.add_argument('--name',required=True,help='Scenario name, 1-120 characters, not blank/whitespace-only')
    parser.add_argument('--note',default='')
    parser.add_argument('--output',type=Path,required=True,help='New directory within this worktree build/; must not exist')
    args=parser.parse_args()

    name=args.name.strip()
    if not name: parser.error('--name must not be blank')
    if len(args.name)>120: parser.error('--name must be at most 120 characters')
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'build'): parser.error('Output must be within this worktree build/.')
    if output.exists(): parser.error('Output exists; scenarios are append-only, choose a new directory.')
    project=args.project.resolve()

    # Same selection/validation refresh-visual-study.py uses: newest of
    # editor/runtime saves, schema/room/variant checked against current
    # settings, a mid-recovery runtime save (backup present, no current save)
    # refused rather than silently falling back. Raises ValueError with a
    # specific reason on any of those; this script does not catch it, so the
    # message reaches the operator directly and nothing partial is written.
    # retained_inputs() already fully validated the chosen state against the
    # current room/variant settings; just read roomId back out of it here.
    retained=retained_inputs(project)
    state=read(retained['state'])

    manifest_path=project/'SourcePackage/manifest.json'
    manifest=read(manifest_path) if manifest_path.is_file() else {}

    scenario=dict(schemaVersion=SCHEMA,id=str(uuid.uuid4()),name=name,note=args.note,
        createdAt=datetime.now().astimezone().isoformat(),roomId=state['roomId'],
        origin=dict(sourceCommit=manifest.get('sourceCommit'),sourceHashes=manifest.get('sourceHashes',{}),
            stateSource='runtime' if retained['state'].parent.name=='Saved' else 'editor'),
        files={})

    # Stage under a hidden temp name next to the target, then rename into
    # place -- a failure partway through never leaves a half-written
    # directory at the final --output path.
    output.parent.mkdir(parents=True,exist_ok=True)
    staging=output.parent/('.scenario-'+scenario['id'])
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        for key,path in retained.items():
            disk_name='study-state.json' if key=='state' else path.name
            dest=staging/disk_name
            shutil.copy2(path,dest)
            scenario['files'][disk_name]=dict(sha256=sha(dest))
        # If any source file changed while copying, its post-copy hash (of
        # the original path, re-read now) will no longer match the hash we
        # just recorded from the copy -- catch that instead of returning a
        # scenario that may not match what the operator saw.
        for key,path in retained.items():
            disk_name='study-state.json' if key=='state' else path.name
            if sha(path)!=scenario['files'][disk_name]['sha256']:
                raise RuntimeError('Input changed while saving the scenario; rerun the command')
        (staging/'scenario.json').write_text(json.dumps(scenario,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging,ignore_errors=True)
        raise
    print(json.dumps(scenario,ensure_ascii=False,indent=2))
    print(output)


if __name__=='__main__': main()

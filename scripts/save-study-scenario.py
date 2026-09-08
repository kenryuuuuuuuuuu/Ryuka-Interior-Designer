"""Save the current comparison scenario (finish, camera, sun) from a generated
UE project as a named, reusable package under build/scenarios/. Does not
launch Blender or Unreal; only copies and validates small state files.

Thin CLI wrapper: all the actual validation/staging logic lives in
refresh_inputs.save_scenario_package(), which the UE editor's own "案の保存"
menu action (study_controls.py) also calls directly, in-process -- not by
shelling out to this file (see that module for why)."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from refresh_inputs import save_scenario_package


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True,help='Existing generated UE project directory')
    parser.add_argument('--name',required=True,help='Scenario name, 1-120 characters, not blank/whitespace-only')
    parser.add_argument('--note',default='')
    parser.add_argument('--output',type=Path,required=True,help='New directory within this worktree build/; must not exist')
    args=parser.parse_args()
    # Every failure reason save_scenario_package() can raise (bad --name,
    # --output outside build/ or already existing, an invalid/mid-recovery
    # saved state, ...) is a plain ValueError; turned into a clean one-line
    # usage-style error here rather than a full traceback.
    try:
        scenario,output=save_scenario_package(args.project,args.name,args.note,args.output)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(scenario,ensure_ascii=False,indent=2))
    print(output)


if __name__=='__main__': main()

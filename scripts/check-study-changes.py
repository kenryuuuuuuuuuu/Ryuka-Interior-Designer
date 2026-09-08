"""Compare a previously generated project's frozen inputs against the current
source, and check the current source's cross-file references. Does not launch
Blender or Unreal. Exit code 1 if the current source has reference issues
(missing references, duplicate IDs); 0 otherwise (a stale/unusable previous
snapshot is a warning only, not a failure)."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from source_changes import compare, render_html


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',type=Path,required=True,help='Previously generated UE project directory')
    parser.add_argument('--output',type=Path,required=True,help='New directory within this worktree build/; must not exist')
    parser.add_argument('--current-data',type=Path,default=ROOT,
        help='Override the current source root (testing only; refresh-visual-study.py always uses this worktree\'s ROOT)')
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'build'): parser.error('Output must be within this worktree build/.')
    if output.exists(): parser.error('Output exists; choose a new directory.')

    changes=compare(args.previous.resolve(),args.current_data.resolve())
    output.mkdir(parents=True)
    (output/'source-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'index.html').write_text(render_html(changes),encoding='utf-8')
    print(output/'index.html')
    sys.exit(1 if changes['issues'] else 0)


if __name__=='__main__': main()

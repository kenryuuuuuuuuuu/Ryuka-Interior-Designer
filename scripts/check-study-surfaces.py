"""Resolve data/visual/surface-registry.json's persistent wall/floor/ceiling
IDs against the current house.json shape. Does not launch Blender or Unreal.
Exit code 1 if any registered surface is unresolved/ambiguous or the registry
itself is missing/malformed/duplicated; 0 if every registered surface
resolves cleanly."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from surface_registry import resolve_from, render_html


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New directory within this worktree build/; must not exist')
    parser.add_argument('--root',type=Path,default=ROOT,help='Override the current source root (testing only)')
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.is_relative_to(ROOT/'build'): parser.error('Output must be within this worktree build/.')
    if output.exists(): parser.error('Output exists; choose a new directory.')

    result=resolve_from(args.root.resolve())
    output.mkdir(parents=True)
    (output/'surface-resolution.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'index.html').write_text(render_html(result),encoding='utf-8')
    print(output/'index.html')
    sys.exit(1 if result['issues'] else 0)


if __name__=='__main__': main()

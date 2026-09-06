"""Create local daylight cases without embedding site coordinates in project source."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'unreal'))
from solar_position import make_case


def local_path(path):
    resolved=path.resolve()
    if not resolved.is_relative_to(ROOT/'build'):
        raise ValueError('Keep site inputs and solar outputs inside this worktree build/ (gitignored).')
    return resolved


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site',type=Path,required=True)
    parser.add_argument('--times',nargs='+',required=True,help='ISO timestamps including UTC offset, e.g. 2026-12-22T12:00:00+09:00')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    site=json.loads(local_path(args.site).read_text(encoding='utf-8-sig'))
    output=local_path(args.output)
    document=dict(schemaVersion='1.0.0',siteDaylightCalibrated=False,
                  cases=[make_case(site,t) for t in args.times])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as file:
        json.dump(document,file,ensure_ascii=False,indent=2)
        file.write('\n')
    for i,case in enumerate(document['cases']):
        print(f"{i}: {case['localTimestamp']} az={case['azimuthDeg']:.2f} elevation={case['elevationDeg']:.2f} usable={case['usable']}")


if __name__=='__main__': main()

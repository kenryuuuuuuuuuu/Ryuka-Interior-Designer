"""Validate and build a versioned local Blender/GLB transfer prototype.

Run with ordinary Python. Requires Blender and Node; never modifies source data.
The optional interior study compares provisional finishes and manual sun angles.
Neither mode is calibrated to the construction site.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from surface_registry import resolve_from as resolve_surfaces


def run(command, verbose=True):
    result = subprocess.run([str(x) for x in command], cwd=ROOT, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding='utf-8', errors='replace',
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
    if verbose:
        print(result.stdout, end='', flush=True)
    return result.stdout


def inputs():
    paths = sorted((ROOT / 'data').rglob('*.json'))
    paths += sorted((ROOT / 'tests').glob('validate_*.py'))
    paths += [ROOT / 'tests/test_blender_wall_geometry.py', ROOT / 'tests/test_interior_geometry.py']
    paths += [ROOT / p for p in ('generated/house-data.js', 'generated/interior-walls.json',
              'generated/exterior-walls.json', 'generated/visual-envelope.json', 'scripts/build-web-data.mjs',
              'blender/build_house.py', 'blender/wall_geometry.py', 'blender/interior_geometry.py',
              'blender/build_interior.py', 'blender/furniture_assets.py', 'blender/surface_finishes.py', 'blender/guest_decor.py', 'blender/textile_assets.py', 'unreal/finish_settings.py', 'scripts/build-visual-twin.py')]
    return {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(
            p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/visual-twin-baseline'))
    parser.add_argument('--interior', action='store_true', help='Build and render the provisional guest LDK study')
    parser.add_argument('--variant', choices=('natural','warm','reference'), default='natural')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--samples', type=int, default=128)
    parser.add_argument('--elevation', type=float)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Output already exists; choose a new package directory.')
    if not args.blender.is_file():
        parser.error('Blender executable not found.')
    node = shutil.which('node')
    if not node:
        parser.error('Node executable not found.')
    before = inputs()
    checks = [[node, 'scripts/build-web-data.mjs', '--check']]
    checks += [[sys.executable, 'tests/' + name] for name in
               ('validate_house.py', 'validate_furniture.py', 'validate_openings.py',
                'validate_electrical.py', 'test_blender_wall_geometry.py', 'test_interior_geometry.py')]
    for command in checks:
        run(command)
    if args.interior:
        # Only the visual study needs registered surface IDs (W04 will apply
        # per-surface finishes keyed by them); the plain white-model build
        # must not be blocked by this visual-only setup being incomplete.
        surfaces = resolve_surfaces(ROOT)
        if surfaces['issues']:
            reasons = '; '.join(i['reason'] for i in surfaces['issues'])
            parser.error('Surface registry has unresolved entries: ' + reasons
                + ' Run scripts/check-study-surfaces.py for details.')
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage a new package; failures cannot replace the last successful build.
    with tempfile.TemporaryDirectory(prefix='.visual-twin-', dir=output.parent) as temp:
        staging = Path(temp) / 'package'
        if not args.interior:
            staging.mkdir()
        blender_version = run([args.blender, '--version'], verbose=False).splitlines()[0]
        print(blender_version, flush=True)
        if args.interior:
            command = [args.blender, '--background', '--factory-startup', '--python-exit-code', '1',
                       '--python', ROOT / 'blender/build_interior.py', '--', '--output', staging,
                       '--variant', args.variant, '--samples', args.samples, '--width', args.width, '--render']
            if args.elevation is not None:
                command += ['--elevation', args.elevation]
            build_log = run(command, verbose=False)
        else:
            build_log = run([args.blender, '--background', '--factory-startup', '--python-exit-code', '1',
                        '--python', ROOT / 'blender/build_house.py', '--',
                        '--input', ROOT / 'data/house.json', '--output', staging / 'house.blend',
                        '--glb', staging / 'house.glb'], verbose=False)
        (staging / 'build.log').write_text(build_log, encoding='utf-8')
        # Preserve raw source notes/status/provenance even for not-yet-rendered entities.
        for relative in before:
            target = staging / 'inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        if inputs() != before:
            raise RuntimeError('Inputs changed during build; discard package and rebuild.')
        rendered = ['data/house.json', 'data/door-catalog.json', 'data/window-catalog.json',
                    'data/openings.json', 'data/interior-doors.json',
                    'generated/interior-walls.json', 'generated/exterior-walls.json']
        if args.interior:
            rendered += ['data/furniture.json', 'data/furniture-catalog.json',
                         'data/visual/guest-ldk-study.json', 'data/visual/asset-bindings.json', 'data/visual/guest-decor.json', 'generated/visual-envelope.json']
        manifest = dict(schemaVersion='0.1.0', stage='geometry-transfer-prototype',
                        daylightReady=False, unrealImportVerified=False,
                        sourceCommit=run(['git', 'rev-parse', 'HEAD'], verbose=False).strip(),
                        sourceHashes=before, hashNormalization='CRLF to LF',
                        blenderVersion=blender_version, geometryInputs=rendered,
                        coordinates=dict(source='x east, z south, y up; metres; GL origin',
                                         blender='X=x, Y=-z, Z=y; metres',
                                         gltf='Blender standard glTF axis conversion; metres'),
                        limitations=['No ceilings or sloped ceiling closure',
                                     'No stairs, stair slab opening or guard walls',
                                     'No furniture or electrical geometry',
                                     'Door markers are diagnostic solids; arches not modelled',
                                     'No window frames or optical glazing',
                                     'Exterior wall heights still use default ceiling height',
                                     'Missing roof/gable details and site context',
                                     'No sun/site parameters, camera, or calibrated materials',
                                     'Generated wall sequence IDs are not stable finish bindings'],
                        artifacts={name: dict(bytes=(staging / name).stat().st_size,
                                   sha256=hashlib.sha256((staging / name).read_bytes()).hexdigest())
                                   for name in (('interior.blend','interior.glb','interior.png','study.json')
                                                if args.interior else ('house.blend', 'house.glb'))})
        if args.interior:
            manifest['stage'] = 'guest-ldk-visual-study'
            manifest['limitations'] = json.loads((staging/'study.json').read_text(encoding='utf-8'))['limitations']
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        verify_args = (['--study', staging] if args.interior else ['--package', staging])
        verify_script = 'validate_interior_scene.py' if args.interior else 'validate_blender_export.py'
        verification_log = run([args.blender, '--background', '--factory-startup', '--python-exit-code', '1',
                                '--python', ROOT/'tests'/verify_script, '--', *verify_args], verbose=False)
        (staging/'verification.log').write_text(verification_log,encoding='utf-8')
        result_file = staging/'verification.json'
        manifest['artifacts']['verification.json'] = dict(bytes=result_file.stat().st_size,
            sha256=hashlib.sha256(result_file.read_bytes()).hexdigest())
        (staging/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.rename(staging, output)
    print(f'Built {output}. Validation and GLB round-trip passed; daylightReady=false (site calibration pending).')


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stdout or str(error), file=sys.stderr)
        raise SystemExit(error.returncode)

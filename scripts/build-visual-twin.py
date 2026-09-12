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
              'blender/build_interior.py', 'blender/furniture_assets.py', 'blender/surface_finishes.py',
              'blender/surface_bindings.py', 'blender/guest_decor.py', 'blender/textile_assets.py',
              'blender/electrical_assets.py', 'blender/stair_geometry.py',
              'unreal/finish_settings.py', 'unreal/study_state.py', 'unreal/solar_position.py',
              'unreal/surface_finish_overrides.py', 'unreal/lighting.py', 'unreal/multi_room_state.py',
              'unreal/circulation.py',
              'scripts/surface_registry.py', 'scripts/build-visual-twin.py')]
    return {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(
            p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/visual-twin-baseline'))
    parser.add_argument('--interior', action='store_true', help='Build and render the provisional guest LDK study')
    parser.add_argument('--scope', help='--interior only: data/visual/study-scopes.json scopeId. Defaults to '
        '--state\'s own scopeId, or "guest-ldk" (single-room, pre-W07 compatible) if neither is given.')
    parser.add_argument('--variant', choices=('natural','warm','reference'), default='natural')
    parser.add_argument('--state', type=Path, help='--interior only: validated study-state.json/scenario state '
        '(schemaVersion 1.0.0-2.0.0); overrides --variant with the scope\'s per-room variant and carries '
        'per-room surfaceOverrides through to Blender')
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--samples', type=int, default=128)
    parser.add_argument('--elevation', type=float)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error('Output already exists; choose a new package directory.')
    if not args.blender.is_file():
        parser.error('Blender executable not found.')
    if args.state and not args.interior:
        parser.error('--state only applies to --interior.')
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
        try:
            raw_state = json.loads(args.state.read_text(encoding='utf-8')) if args.state else None
        except Exception:
            raw_state = None  # malformed/unreadable; let build_interior.py's real validate_state() report it
        sys.path.insert(0, str(ROOT / 'unreal'))
        import multi_room_state as mrs
        scopes_document = mrs.validate_scopes(json.loads((ROOT / 'data/visual/study-scopes.json').read_text(encoding='utf-8')))
        scope_id = args.scope or (raw_state or {}).get('scopeId') or 'guest-ldk'
        try:
            scope = mrs.resolve_scope(scopes_document, scope_id)
        except ValueError as error:
            parser.error(str(error))
        room_ids = scope['roomIds']
        # W04 review R4: an override naming a surface id that is not even a
        # currently-registered/resolved id must stop HERE, before Blender
        # starts -- not partway through the Blender build (build_interior.py's
        # own check catches this too, but only after bpy has already loaded;
        # that is not "before Blender"). The no-surface case (a registered id
        # with no matching real geometry) is a separate, genuinely
        # model-dependent check that correctly stays in build_interior.py,
        # after Blender builds the geometry and before Unreal import.
        if isinstance(raw_state, dict):
            # W07-G1: a 2.0.0 state's overrides live per-room
            # (roomStates[*].surfaceOverrides); anything older is still the
            # single top-level surfaceOverrides this check has always had.
            if raw_state.get('schemaVersion') == '2.0.0':
                overrides_by_room = {rid: rs.get('surfaceOverrides') for rid, rs in (raw_state.get('roomStates') or {}).items()}
            else:
                overrides_by_room = {raw_state.get('roomId'): raw_state.get('surfaceOverrides')}
            known_ids = {s['id'] for s in surfaces['surfaces']}
            unknown = sorted({sid for overrides in overrides_by_room.values() if isinstance(overrides, dict) for sid in overrides} - known_ids)
            if unknown:
                parser.error('surfaceOverrides references unknown surface id(s): ' + ', '.join(unknown))
        # W06-v1 review R4: build_lighting_bindings() (unknown/unsupported
        # lighting type, missing profile, unresolvable mount) previously only
        # ran INSIDE build_interior.py, after Blender had already built the
        # whole scene -- not "before Blender starts". Resolve the CURRENT
        # source here first, same as the surface-registry check above; a
        # --state naming a fixture id that this resolution doesn't produce is
        # also caught here, before Blender launches.
        sys.path.insert(0, str(ROOT / 'blender'))
        from electrical_assets import build_lighting_bindings
        house_data = json.loads((ROOT / 'data/house.json').read_text(encoding='utf-8'))
        house_data['envelope'] = json.loads((ROOT / 'generated/visual-envelope.json').read_text(encoding='utf-8'))
        electrical_doc = json.loads((ROOT / 'data/electrical.json').read_text(encoding='utf-8'))
        catalog_doc = json.loads((ROOT / 'data/electrical-catalog.json').read_text(encoding='utf-8'))
        lighting_settings_doc = json.loads((ROOT / 'data/visual/lighting-settings.json').read_text(encoding='utf-8'))
        try:
            lighting_bindings_preflight = build_lighting_bindings(
                house_data, electrical_doc, catalog_doc, lighting_settings_doc, room_ids)
        except ValueError as error:
            parser.error('Lighting fixtures could not be resolved: ' + str(error))
        if isinstance(raw_state, dict):
            if raw_state.get('schemaVersion') == '2.0.0':
                fixtures_by_room = {rid: rs.get('fixtures') for rid, rs in (raw_state.get('roomStates') or {}).items()}
            else:
                state_lighting = raw_state.get('lighting')
                fixtures_by_room = {raw_state.get('roomId'): (state_lighting or {}).get('fixtures') if isinstance(state_lighting, dict) else None}
            known_fixture_ids = {f['id'] for f in lighting_bindings_preflight['fixtures']}
            unknown_fixtures = sorted({fid for fixtures in fixtures_by_room.values() if isinstance(fixtures, dict) for fid in fixtures} - known_fixture_ids)
            if unknown_fixtures:
                parser.error('lighting.fixtures references unknown fixture id(s): ' + ', '.join(unknown_fixtures))
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
                       '--scope', scope_id, '--variant', args.variant,
                       '--samples', args.samples, '--width', args.width, '--render']
            if args.elevation is not None:
                command += ['--elevation', args.elevation]
            if args.state:
                command += ['--state', args.state]
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
                         'data/visual/guest-ldk-study.json', 'data/visual/asset-bindings.json', 'data/visual/guest-decor.json', 'generated/visual-envelope.json',
                         'data/electrical.json', 'data/electrical-catalog.json', 'data/visual/lighting-settings.json',
                         'data/visual/study-scopes.json', 'data/visual/room-render-settings.json', 'data/visual/surface-registry.json']
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
                                   for name in (('interior.blend','interior.glb','interior.png','study.json','surface-bindings.json','lighting-bindings.json','role-bindings.json','door-bindings.json')
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

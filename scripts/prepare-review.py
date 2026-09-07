"""Create a local review inventory for a clean, committed worktree. No uploads."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def prepare(root, base, output, artifacts=()):
    root = root.resolve()
    base = git(root, 'rev-parse', '--verify', base + '^{commit}').decode().strip()
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    git(root, 'merge-base', '--is-ancestor', base, head)
    if git(root, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('Commit the task and report first; worktree contains uncommitted/untracked files.')
    output = output.resolve()
    if not output.is_relative_to(root / 'build') or output.exists():
        raise ValueError('Output must be a NEW directory under this worktree/build.')
    evidence = []
    for item in artifacts:
        path = item.resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Evidence must be an existing file inside this worktree.')
        evidence.append({'path': path.relative_to(root).as_posix(),
                         'size': path.stat().st_size, 'sha256': digest(path)})
    # No rename detection: both the deleted and added path are accounted for.
    names = git(root, 'diff', '--no-ext-diff', '--no-renames', '--name-only', '-z', base, head)
    paths = [p.decode('utf-8') for p in names.split(b'\0') if p]
    patch = git(root, 'diff', '--no-ext-diff', '--no-textconv', '--no-renames',
                '--binary', '--full-index', base, head)
    status = git(root, 'diff', '--no-ext-diff', '--no-renames', '--name-status', '-z', base, head)
    history = git(root, 'log', '--format=%H %s', base + '..' + head)
    # Avoid silently making a bundle spanning a concurrent edit/commit.
    if git(root, 'rev-parse', 'HEAD').decode().strip() != head or git(
            root, 'status', '--porcelain=v1', '--untracked-files=all'):
        raise ValueError('Worktree changed during collection; retry when idle.')
    for item in evidence:
        path = root / item['path']
        if path.stat().st_size != item['size'] or digest(path) != item['sha256']:
            raise ValueError('Evidence changed during collection; stop producers and retry.')
    manifest = {'schemaVersion': 1, 'base': base, 'head': head,
                'changedFiles': paths, 'artifacts': evidence,
                'patchSHA256': hashlib.sha256(patch).hexdigest(),
                'scope': 'Git base..head only. Ignored artifacts listed separately; tests not executed.'}
    output.mkdir(parents=True)
    (output / 'changes.patch').write_bytes(patch)
    (output / 'name-status.z').write_bytes(status)
    (output / 'commits.txt').write_bytes(history)
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', required=True, help='Exact starting commit recorded before implementation')
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--artifact', action='append', type=Path, default=[])
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        result = prepare(root, a.base, a.output, a.artifact)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        p.exit(1, f'Review bundle failed: {exc}\n')
    print(json.dumps({'base': result['base'], 'head': result['head'],
                      'changedFiles': len(result['changedFiles']), 'output': str(a.output)}, indent=2))


if __name__ == '__main__':
    main()

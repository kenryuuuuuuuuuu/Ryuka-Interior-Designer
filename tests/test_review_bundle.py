import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('prepare_review', Path(__file__).resolve().parents[1] / 'scripts/prepare-review.py')
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Test')
        (self.root / '.gitignore').write_text('build/\n')
        (self.root / 'old.txt').write_text('original\n')
        self.commit()
        self.base = self.git('rev-parse', 'HEAD').decode().strip()

    def git(self, *args):
        return review.git(self.root, *args)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'test')

    def test_add_delete_binary_unicode_and_evidence(self):
        (self.root / 'old.txt').unlink()
        name = '\u5bb6\u5177 file.bin'
        (self.root / name).write_bytes(b'\x00\xff\x00')
        self.commit()
        evidence = self.root / 'build/evidence.json'
        evidence.parent.mkdir()
        evidence.write_text('{"renderVerified": false}')
        result = review.prepare(self.root, self.base, self.root / 'build/review', [evidence])
        self.assertEqual(set(result['changedFiles']), {'old.txt', name})
        self.assertEqual(result['artifacts'][0]['sha256'], review.digest(evidence))
        patch = (self.root / 'build/review/changes.patch').read_bytes()
        self.assertIn(b'GIT binary patch', patch)
        self.assertIn(b'deleted file mode', patch)
        # Manifest inventory is round-trippable UTF-8, not quoted Git paths.
        self.assertEqual(json.loads((self.root / 'build/review/manifest.json').read_text(encoding='utf-8')), result)

    def test_reject_dirty_and_untracked(self):
        for name in ['old.txt', 'extra.txt']:
            with self.subTest(name=name):
                path = self.root / name
                previous = path.read_bytes() if path.exists() else None
                path.write_text('changed')
                with self.assertRaises(ValueError):
                    review.prepare(self.root, self.base, self.root / 'build/review')
                if previous is None:
                    path.unlink()
                else:
                    path.write_bytes(previous)

    def test_reject_output_escape_and_existing_directory(self):
        for output in [self.root / 'outside', self.root]:
            with self.assertRaises(ValueError):
                review.prepare(self.root, self.base, output)
        output = self.root / 'build/review'
        output.mkdir(parents=True)
        with self.assertRaises(ValueError):
            review.prepare(self.root, self.base, output)

    def test_reject_nonancestor(self):
        self.git('checkout', '--orphan', 'unrelated')
        self.git('commit', '-qm', 'unrelated')
        with self.assertRaises(subprocess.CalledProcessError):
            review.prepare(self.root, self.base, self.root / 'build/review')


if __name__ == '__main__':
    unittest.main()

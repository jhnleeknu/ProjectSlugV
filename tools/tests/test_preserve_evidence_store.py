"""Small reproducible evidence preservation fixtures; never run real-data pack."""
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest import mock

TOOL = Path(__file__).resolve().parents[1] / 'preserve_evidence_store.py'
SPEC = importlib.util.spec_from_file_location('preserve_evidence_store', TOOL)
STORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORE)


class EvidenceStoreTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='evidence-store-fixture-')
        self.base = Path(self.temporary.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        folder = self.source / 'artifacts'
        folder.mkdir()
        (folder / 'a.bin').write_bytes(b'content duplicate\x00' * 41)
        (folder / 'b.bin').write_bytes((folder / 'a.bin').read_bytes())
        (folder / 'different.bin').write_bytes(b'different content')
        (folder / 'empty.bin').write_bytes(b'')
        (folder / 'external').symlink_to('/nonexistent/evidence-fixture-target')
        (folder / 'relative').symlink_to('a.bin')
        os.chmod(folder / 'a.bin', 0o640)
        os.chmod(folder / 'b.bin', 0o600)
        for number, name in enumerate(sorted(folder.iterdir()), 1):
            stamp = 1700000000000000000 + number * 123456789
            os.utime(name, ns=(stamp, stamp), follow_symlinks=False)
        os.chmod(folder, 0o750)
        os.utime(folder, ns=(1700000001234567890, 1700000001234567890))
        self.rows = []
        for path in [folder] + sorted(folder.iterdir()):
            info = path.lstat()
            kind = ('symlink' if stat.S_ISLNK(info.st_mode) else
                    'directory' if stat.S_ISDIR(info.st_mode) else 'file')
            self.rows.append({'path': path.relative_to(self.source).as_posix(),
                              'type': kind, 'size': info.st_size if kind == 'file' else 0,
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()
                              if kind == 'file' else None,
                              'mode': stat.S_IMODE(info.st_mode), 'mtime_ns': info.st_mtime_ns,
                              'link_target': os.readlink(path) if kind == 'symlink' else None})
        self.manifest = self.base / 'manifest.jsonl.gz'
        self.write_manifest(self.manifest, self.rows)
        self.archive = self.base / 'store.tar.gz'
        # Fixtures are tiny; production disk floor remains unchanged.
        self.disk = mock.patch.object(STORE, 'MIN_FREE', 0)
        self.disk.start()

    def tearDown(self):
        self.disk.stop()
        self.temporary.cleanup()

    @staticmethod
    def write_manifest(path, rows):
        with gzip.open(path, 'wt') as stream:
            for row in rows:
                stream.write(json.dumps(row) + '\n')

    def pack(self):
        return STORE.pack(self.source, self.manifest, self.archive)

    def test_roundtrip_independent_files_and_exact_metadata(self):
        before = [(row['path'], (self.source / row['path']).lstat().st_mtime_ns)
                  for row in self.rows]
        result = self.pack()
        self.assertEqual(result['unique_objects'], 3)
        preserved_manifest = Path(str(self.archive) + '.manifest.jsonl.gz')
        self.assertEqual(preserved_manifest.read_bytes(), self.manifest.read_bytes())
        self.assertFalse(Path(str(self.archive) + '.incomplete').exists())
        restored = self.base / 'restored'
        STORE.restore(preserved_manifest, self.archive, restored)
        for row in self.rows:
            path = restored / row['path']
            info = path.lstat()
            self.assertEqual(stat.S_IMODE(info.st_mode), row['mode'])
            self.assertEqual(info.st_mtime_ns, row['mtime_ns'])
            if row['type'] == 'file':
                self.assertEqual(path.read_bytes(), (self.source / row['path']).read_bytes())
            elif row['type'] == 'symlink':
                self.assertEqual(os.readlink(path), row['link_target'])
        self.assertNotEqual((restored / 'artifacts/a.bin').stat().st_ino,
                            (restored / 'artifacts/b.bin').stat().st_ino)
        self.assertNotEqual((restored / 'artifacts/a.bin').stat().st_mtime_ns,
                            (restored / 'artifacts/b.bin').stat().st_mtime_ns)
        self.assertEqual(before, [(row['path'], (self.source / row['path']).lstat().st_mtime_ns)
                                  for row in self.rows])

    def test_corrupt_gzip_trailer_and_truncated_archive_rejected(self):
        self.pack()
        original = self.archive.read_bytes()
        corrupt = bytearray(original)
        corrupt[-8] ^= 1
        self.archive.write_bytes(corrupt)
        with self.assertRaises((ValueError, OSError, tarfile.TarError)):
            STORE.verify(self.manifest, self.archive)
        self.archive.write_bytes(original[:-17])
        with self.assertRaises((ValueError, OSError, EOFError, tarfile.TarError)):
            STORE.verify(self.manifest, self.archive)

    def test_corrupt_manifest_sha_and_unsafe_path_rejected(self):
        self.pack()
        bad = self.base / 'bad.jsonl.gz'
        rows = [dict(row) for row in self.rows]
        next(row for row in rows if row['type'] == 'file')['sha256'] = '0' * 64
        self.write_manifest(bad, rows)
        with self.assertRaises(ValueError):
            STORE.verify(bad, self.archive)
        for unsafe in ('../escape', '/absolute', 'artifacts/../escape', 'artifacts//escape'):
            rows = [dict(row) for row in self.rows]
            rows[0]['path'] = unsafe
            self.write_manifest(bad, rows)
            with self.assertRaises(ValueError):
                STORE.restore(bad, self.archive, self.base / 'should-not-exist')
            self.assertFalse((self.base / 'should-not-exist').exists())

    def test_duplicate_and_conflicting_manifest_paths_rejected(self):
        bad = self.base / 'bad.jsonl.gz'
        self.write_manifest(bad, self.rows + [self.rows[-1]])
        with self.assertRaisesRegex(ValueError, 'Duplicate manifest path'):
            STORE.manifest_index(bad)
        rows = [dict(row) for row in self.rows]
        rows[0].update(type='symlink', link_target='/outside')
        self.write_manifest(bad, rows)
        with self.assertRaisesRegex(ValueError, 'Non-directory manifest ancestor'):
            STORE.manifest_index(bad)
        self.write_manifest(bad, rows[1:] + rows[:1])
        with self.assertRaisesRegex(ValueError, 'Non-directory has manifest children'):
            STORE.manifest_index(bad)

    def test_no_overwrite_output_inside_source_and_source_corruption(self):
        with self.assertRaisesRegex(ValueError, 'outside source'):
            STORE.pack(self.source, self.manifest, self.source / 'store.tar.gz')
        self.pack()
        with self.assertRaises(FileExistsError):
            self.pack()
        with self.assertRaisesRegex(ValueError, 'empty'):
            STORE.restore(self.manifest, self.archive, self.source)
        target = self.source / 'artifacts/a.bin'
        data = target.read_bytes()
        info = target.stat()
        target.write_bytes(b'X' + data[1:])
        os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))
        output = self.base / 'bad-source.tar.gz'
        with self.assertRaisesRegex(RuntimeError, 'SHA256/size differs'):
            STORE.pack(self.source, self.manifest, output)
        self.assertFalse(output.exists())

    def test_source_parent_symlink_not_followed(self):
        external = self.base / 'external'
        (self.source / 'artifacts').rename(external)
        (self.source / 'artifacts').symlink_to(external)
        with self.assertRaisesRegex(RuntimeError, 'metadata differs'):
            self.pack()
        self.assertFalse(self.archive.exists())

    def test_extra_missing_and_duplicate_archive_objects_rejected(self):
        self.pack()
        with tarfile.open(self.archive, 'r:gz') as archive:
            members = [(entry.name, archive.extractfile(entry).read()) for entry in archive]
        for changed in (members[:-1], members + members[:1],
                        members + [('objects/' + '0' * 64, b'extra')]):
            with tarfile.open(self.archive, 'w:gz') as archive:
                for name, data in changed:
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    archive.addfile(entry, io.BytesIO(data))
            with self.assertRaises(ValueError):
                STORE.verify(self.manifest, self.archive)

    def test_archive_change_after_first_verify_rejected(self):
        self.pack()
        real_verify = STORE.verify

        def change_archive(manifest, archive):
            result = real_verify(manifest, archive)
            with tarfile.open(archive, 'w:gz') as stream:
                entry = tarfile.TarInfo('objects/../../escape')
                entry.size = 4
                stream.addfile(entry, io.BytesIO(b'evil'))
            return result

        with mock.patch.object(STORE, 'verify', side_effect=change_archive):
            with self.assertRaisesRegex(RuntimeError, 'object changed'):
                STORE.restore(self.manifest, self.archive, self.base / 'restore-race')
        self.assertFalse((self.base / 'escape').exists())

    def test_nonzero_payload_after_tar_eof_rejected(self):
        self.pack()
        original = gzip.decompress(self.archive.read_bytes())
        extra = io.BytesIO()
        with tarfile.open(fileobj=extra, mode='w') as stream:
            entry = tarfile.TarInfo('unexpected-after-eof')
            entry.size = 4
            stream.addfile(entry, io.BytesIO(b'evil'))
        self.archive.write_bytes(gzip.compress(original + extra.getvalue()))
        with self.assertRaisesRegex(ValueError, 'after tar EOF'):
            STORE.verify(self.manifest, self.archive)


if __name__ == '__main__':
    unittest.main()

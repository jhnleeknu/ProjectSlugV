#!/usr/bin/env python3
"""Preserve evidence as unique content objects plus an independent metadata manifest.

pack writes OUT and OUT.manifest.jsonl.gz only after a complete stream verification.
restore makes independent regular files and creates recorded symlinks last; it
never reads through a recorded symlink. No command deletes or modifies source.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath

CHUNK = 1024 * 1024
MIN_FREE = 5 * 1024 ** 3
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
KINDS = ('file', 'directory', 'symlink')


def disk_check(directory):
    free = shutil.disk_usage(directory).free
    if free < MIN_FREE:
        raise RuntimeError('Free disk below 5 GiB: %d' % free)
    return free


def safe_parts(value):
    if not isinstance(value, str) or not value or '\x00' in value or '\\' in value:
        raise ValueError('Invalid manifest path: %r' % value)
    parts = value.split('/')
    if any(part in ('', '.', '..') for part in parts) or PurePosixPath(value).is_absolute():
        raise ValueError('Unsafe manifest path: ' + value)
    return parts


def integer(row, key, minimum=0):
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError('Invalid %s at %s' % (key, row.get('path')))
    return value


def manifest_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError('Empty manifest row %d' % number)
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError('Manifest row is not an object')
            safe_parts(row.get('path'))
            kind = row.get('type')
            if kind not in KINDS:
                raise ValueError('Invalid manifest type: ' + str(kind))
            size = integer(row, 'size')
            integer(row, 'mtime_ns')
            if integer(row, 'mode') > 0o7777:
                raise ValueError('Invalid mode at ' + row['path'])
            if kind == 'file':
                if not isinstance(row.get('sha256'), str) or not SHA_RE.fullmatch(row['sha256']):
                    raise ValueError('Invalid SHA256 at ' + row['path'])
                if row.get('link_target') is not None:
                    raise ValueError('Regular file has link target')
            else:
                if size != 0 or row.get('sha256') is not None:
                    raise ValueError('Non-file has size or SHA256')
                if kind == 'symlink':
                    target = row.get('link_target')
                    if not isinstance(target, str) or not target or '\x00' in target:
                        raise ValueError('Invalid link target at ' + row['path'])
                elif row.get('link_target') is not None:
                    raise ValueError('Directory has link target')
            yield row


def manifest_index(path):
    objects = {}
    counts = dict((kind, 0) for kind in KINDS)
    total = 0
    # Path validation uses a disk index: never retain all million metadata rows.
    with tempfile.TemporaryDirectory(prefix='evidence-path-index-') as temporary:
        disk_check(temporary)
        database = sqlite3.connect(str(Path(temporary) / 'paths.sqlite'))
        try:
            database.execute('PRAGMA journal_mode=OFF')
            database.execute('PRAGMA synchronous=OFF')
            database.execute('PRAGMA cache_size=-4096')
            database.execute('CREATE TABLE paths (path TEXT PRIMARY KEY, kind TEXT) WITHOUT ROWID')
            for row in manifest_rows(path):
                name = row['path']
                parts = safe_parts(name)
                for length in range(1, len(parts)):
                    parent = '/'.join(parts[:length])
                    found = database.execute('SELECT kind FROM paths WHERE path=?', (parent,)).fetchone()
                    if found is not None and found[0] != 'directory':
                        raise ValueError('Non-directory manifest ancestor: ' + parent)
                if row['type'] != 'directory':
                    descendant = database.execute(
                        'SELECT path FROM paths WHERE path>=? AND path<? LIMIT 1',
                        (name + '/', name + '0')).fetchone()
                    if descendant is not None:
                        raise ValueError('Non-directory has manifest children: ' + name)
                try:
                    database.execute('INSERT INTO paths VALUES (?, ?)', (name, row['type']))
                except sqlite3.IntegrityError as error:
                    raise ValueError('Duplicate manifest path: ' + name) from error
                counts[row['type']] += 1
                if row['type'] == 'file':
                    sha = row['sha256']
                    previous = objects.get(sha)
                    if previous is not None and previous != row['size']:
                        raise ValueError('Same SHA256 has different sizes')
                    objects[sha] = row['size']
                    total += row['size']
        finally:
            database.close()
    return objects, counts, total


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for data in iter(lambda: stream.read(CHUNK), b''):
            digest.update(data)
    return digest.hexdigest()


def physical_directory(path):
    path = Path(path).absolute()
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError('Physical directory required: ' + str(path))
    return path.resolve()


def outside(path, root):
    path = Path(path).absolute()
    resolved = path.parent.resolve() / path.name
    if resolved == root or root in resolved.parents:
        raise ValueError('Output must be outside source: ' + str(path))
    return resolved


def absent(path):
    if os.path.lexists(path):
        raise FileExistsError('Refuse to overwrite: ' + str(path))


def open_parent(root_fd, parts):
    """Return owned parent fd, refusing symlinks in every path component."""
    current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def matches_metadata(info, row):
    kind_ok = (stat.S_ISREG(info.st_mode) if row['type'] == 'file' else
               stat.S_ISDIR(info.st_mode) if row['type'] == 'directory' else
               stat.S_ISLNK(info.st_mode))
    return (kind_ok and stat.S_IMODE(info.st_mode) == row['mode'] and
            info.st_mtime_ns == row['mtime_ns'] and
            (row['type'] != 'file' or info.st_size == row['size']))


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


class HashReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.digest.update(data)
        self.count += len(data)
        return data


def finish_tar_stream(archive):
    # Read the tar stream's own buffer, not just its underlying GzipFile.
    # Tar iteration stops at the first EOF record; only zero padding may follow.
    while True:
        data = archive.fileobj.read(CHUNK)
        if not data:
            break
        if data.strip(b'\x00'):
            raise ValueError('Unexpected nonzero data after tar EOF')


def verify(manifest, archive_path):
    expected, counts, total = manifest_index(manifest)
    remaining = dict(expected)
    verified_bytes = 0
    # GzipFile is explicit so draining to EOF validates the gzip trailer CRC.
    with gzip.open(archive_path, 'rb') as zipped:
        with tarfile.open(fileobj=zipped, mode='r|') as archive:
            for entry in archive:
                archive.members.clear()
                name = entry.name
                if not entry.isfile() or not name.startswith('objects/'):
                    raise ValueError('Unexpected archive member: ' + name)
                sha = name[len('objects/'):]
                if not SHA_RE.fullmatch(sha) or sha not in remaining:
                    raise ValueError('Extra/duplicate object: ' + name)
                size = remaining.pop(sha)
                if entry.size != size:
                    raise ValueError('Object size mismatch: ' + name)
                digest = hashlib.sha256()
                actual = 0
                stream = archive.extractfile(entry)
                for data in iter(lambda: stream.read(CHUNK), b''):
                    digest.update(data)
                    actual += len(data)
                if actual != size or digest.hexdigest() != sha:
                    raise ValueError('Object content mismatch: ' + name)
                verified_bytes += actual
            finish_tar_stream(archive)
        while zipped.read(CHUNK):
            pass
    if remaining:
        raise ValueError('Missing %d objects' % len(remaining))
    return {'status': 'verified', 'unique_objects': len(expected),
            'unique_bytes': verified_bytes, 'manifest_counts': counts,
            'logical_regular_bytes': total, 'gzip_eof_crc_checked': True}


def publish(temporary, final):
    # link/unlink is an atomic no-overwrite publication on the same filesystem.
    os.link(temporary, final, follow_symlinks=False)
    os.unlink(temporary)


def pack(source, manifest, output):
    source = physical_directory(source)
    output = outside(output, source)
    manifest_copy = Path(str(output) + '.manifest.jsonl.gz')
    temporary = Path(str(output) + '.incomplete')
    manifest_tmp = Path(str(manifest_copy) + '.incomplete')
    for path in (output, manifest_copy, temporary, manifest_tmp):
        absent(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    disk_check(output.parent)
    objects, counts, total = manifest_index(manifest)
    manifest_sha = sha_file(manifest)
    written = set()
    seen_counts = dict((kind, 0) for kind in KINDS)
    root_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    started = time.monotonic()
    last = started
    try:
        with open(temporary, 'xb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=1, mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode='w|', format=tarfile.PAX_FORMAT,
                                  dereference=False) as archive:
                    for row in manifest_rows(manifest):
                        disk_check(output.parent)
                        parts = safe_parts(row['path'])
                        parent_fd = open_parent(root_fd, parts)
                        try:
                            before = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                            if not matches_metadata(before, row):
                                raise RuntimeError('Source metadata differs: ' + row['path'])
                            if row['type'] == 'file':
                                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW,
                                             dir_fd=parent_fd)
                                with os.fdopen(fd, 'rb') as stream:
                                    if signature(os.fstat(stream.fileno())) != signature(before):
                                        raise RuntimeError('Source changed before read: ' + row['path'])
                                    reader = HashReader(stream)
                                    sha = row['sha256']
                                    if sha not in written:
                                        entry = tarfile.TarInfo('objects/' + sha)
                                        entry.size = row['size']
                                        entry.mode = 0o444
                                        entry.mtime = 0
                                        archive.addfile(entry, reader)
                                        archive.members.clear()
                                    else:
                                        while reader.read(CHUNK):
                                            pass
                                    after_fd = os.fstat(stream.fileno())
                                if reader.count != row['size'] or reader.digest.hexdigest() != sha:
                                    raise RuntimeError('Source SHA256/size differs: ' + row['path'])
                                if signature(after_fd) != signature(before):
                                    raise RuntimeError('Source changed during read: ' + row['path'])
                                written.add(sha)
                            elif row['type'] == 'symlink':
                                target = os.readlink(parts[-1], dir_fd=parent_fd)
                                if target != row['link_target']:
                                    raise RuntimeError('Source link target differs: ' + row['path'])
                            after = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                            if signature(after) != signature(before):
                                raise RuntimeError('Source path changed: ' + row['path'])
                        finally:
                            os.close(parent_fd)
                        seen_counts[row['type']] += 1
                        if time.monotonic() - last >= 45:
                            print(json.dumps({'phase': 'pack', 'rows': sum(seen_counts.values()),
                                              'unique_objects': len(written),
                                              'compressed_bytes': raw.tell()}), flush=True)
                            last = time.monotonic()
    finally:
        os.close(root_fd)
    if written != set(objects) or seen_counts != counts or sha_file(manifest) != manifest_sha:
        raise RuntimeError('Manifest changed during pack')
    with open(manifest, 'rb') as source_manifest, open(manifest_tmp, 'xb') as copy:
        shutil.copyfileobj(source_manifest, copy, CHUNK)
    if sha_file(manifest_tmp) != manifest_sha:
        raise RuntimeError('Manifest changed during copy')
    result = verify(manifest_tmp, temporary)
    disk_check(output.parent)
    result.update({'archive': str(output), 'manifest': str(manifest_copy),
                   'archive_sha256': sha_file(temporary), 'manifest_sha256': manifest_sha,
                   'source_deleted_or_modified': False,
                   'elapsed_seconds': time.monotonic() - started})
    publish(manifest_tmp, manifest_copy)
    publish(temporary, output)
    return result


def make_parents(root_fd, parts):
    current = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, 0o700, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def restore(manifest, archive_path, output):
    manifest_sha = sha_file(manifest)
    archive_sha = sha_file(archive_path)
    result = verify(manifest, archive_path)
    expected, unused_counts, unused_total = manifest_index(manifest)
    output = Path(output).absolute()
    if os.path.lexists(output):
        physical_directory(output)
        if any(output.iterdir()):
            raise ValueError('Restore output must be empty')
    else:
        output.mkdir(parents=True, mode=0o700)
    output = output.resolve()
    # Keep object staging in the empty destination, then remove before completion.
    object_dir = output / '.evidence-objects.incomplete'
    if any(safe_parts(row['path'])[0] == object_dir.name for row in manifest_rows(manifest)):
        raise ValueError('Manifest conflicts with reserved restore staging path')
    disk_check(output)
    object_dir.mkdir(mode=0o700)
    with gzip.open(archive_path, 'rb') as zipped:
        with tarfile.open(fileobj=zipped, mode='r|') as archive:
            for entry in archive:
                archive.members.clear()
                if not entry.isfile() or not entry.name.startswith('objects/'):
                    raise RuntimeError('Archive changed after verification')
                sha = entry.name[len('objects/'):]
                if not SHA_RE.fullmatch(sha) or sha not in expected:
                    raise RuntimeError('Archive object changed after verification')
                expected_size = expected.pop(sha)
                if entry.size != expected_size:
                    raise RuntimeError('Archive size changed after verification')
                digest = hashlib.sha256()
                actual_size = 0
                with open(object_dir / sha, 'xb') as destination:
                    stream = archive.extractfile(entry)
                    for data in iter(lambda: stream.read(CHUNK), b''):
                        disk_check(output)
                        destination.write(data)
                        digest.update(data)
                        actual_size += len(data)
                if actual_size != expected_size or digest.hexdigest() != sha:
                    raise RuntimeError('Archive changed after verification')
            finish_tar_stream(archive)
        while zipped.read(CHUNK):
            pass
    if expected or sha_file(archive_path) != archive_sha or sha_file(manifest) != manifest_sha:
        raise RuntimeError('Archive or manifest changed during restore')
    root_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for row in manifest_rows(manifest):
            parts = safe_parts(row['path'])
            parent_fd = make_parents(root_fd, parts)
            try:
                if row['type'] == 'directory':
                    try:
                        os.mkdir(parts[-1], 0o700, dir_fd=parent_fd)
                    except FileExistsError:
                        info = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                        if not stat.S_ISDIR(info.st_mode):
                            raise ValueError('Duplicate/conflicting restore path: ' + row['path'])
                elif row['type'] == 'file':
                    disk_check(output)
                    fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent_fd)
                    with os.fdopen(fd, 'wb') as destination, open(object_dir / row['sha256'], 'rb') as source:
                        shutil.copyfileobj(source, destination, CHUNK)
                        os.fchmod(destination.fileno(), row['mode'])
                    os.utime(parts[-1], ns=(row['mtime_ns'], row['mtime_ns']),
                             dir_fd=parent_fd, follow_symlinks=False)
            finally:
                os.close(parent_fd)
        # Symlinks are created only after all actual files, never followed.
        for row in manifest_rows(manifest):
            if row['type'] != 'symlink':
                continue
            parts = safe_parts(row['path'])
            parent_fd = open_parent(root_fd, parts)
            try:
                os.symlink(row['link_target'], parts[-1], dir_fd=parent_fd)
                os.utime(parts[-1], ns=(row['mtime_ns'], row['mtime_ns']),
                         dir_fd=parent_fd, follow_symlinks=False)
                info = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
                if stat.S_IMODE(info.st_mode) != row['mode']:
                    raise RuntimeError('Restored symlink mode unsupported: ' + row['path'])
            finally:
                os.close(parent_fd)
        shutil.rmtree(object_dir)
        # Apply directory timestamps last, after all child creation/removal.
        # Deepest-first ordering without retaining the million file rows.
        max_depth = max((len(safe_parts(row['path'])) for row in manifest_rows(manifest)
                         if row['type'] == 'directory'), default=0)
        for depth in range(max_depth, 0, -1):
            for row in manifest_rows(manifest):
                parts = safe_parts(row['path'])
                if row['type'] != 'directory' or len(parts) != depth:
                    continue
                parent_fd = open_parent(root_fd, parts)
                try:
                    fd = os.open(parts[-1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=parent_fd)
                    try:
                        os.fchmod(fd, row['mode'])
                        os.utime(fd, ns=(row['mtime_ns'], row['mtime_ns']))
                    finally:
                        os.close(fd)
                finally:
                    os.close(parent_fd)
    finally:
        os.close(root_fd)
    if sha_file(manifest) != manifest_sha:
        raise RuntimeError('Manifest changed during restore')
    result.update({'restored_to': str(output), 'regular_files_independent': True,
                   'symlinks_created_last': True})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    pack_parser = commands.add_parser('pack')
    pack_parser.add_argument('--source', required=True)
    pack_parser.add_argument('--manifest', required=True)
    pack_parser.add_argument('--out', required=True)
    verify_parser = commands.add_parser('verify')
    verify_parser.add_argument('--manifest', required=True)
    verify_parser.add_argument('--archive', required=True)
    restore_parser = commands.add_parser('restore')
    restore_parser.add_argument('--manifest', required=True)
    restore_parser.add_argument('--archive', required=True)
    restore_parser.add_argument('--out', required=True)
    args = parser.parse_args()
    if args.command == 'pack':
        result = pack(args.source, args.manifest, args.out)
    elif args.command == 'verify':
        result = verify(args.manifest, args.archive)
    else:
        result = restore(args.manifest, args.archive, args.out)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()

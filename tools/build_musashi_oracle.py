"""Fetch a pinned official Musashi archive and build an explicit-source oracle."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tarfile
import urllib.request

REVISION = '313ebf1bd9f4d0d93341eb5ce21fd8a119e9dbdd'
ARCHIVE_SHA256 = '8bed9e28e7e5377256d41aff80a99c9e917a24e7392d9219e1c45c40ad4000e5'
REPOSITORY = 'https://github.com/kstenerud/Musashi'
ARCHIVE_URL = 'https://codeload.github.com/kstenerud/Musashi/tar.gz/'+REVISION


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    folder = root/'artifacts/dependencies'
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder/('musashi-'+REVISION+'.tar.gz')
    if not archive.exists():
        data = urllib.request.urlopen(ARCHIVE_URL, timeout=60).read()
        if sha(data) != ARCHIVE_SHA256:
            raise ValueError('Pinned official source archive hash mismatch')
        archive.write_bytes(data)
    if sha(archive.read_bytes()) != ARCHIVE_SHA256:
        raise ValueError('Cached official source archive hash mismatch')
    source = folder/('Musashi-'+REVISION)
    with tarfile.open(archive) as package:
        if not source.exists():
            package.extractall(folder, filter='data')
        source_hashes = {}
        for member in package.getmembers():
            if not member.isfile():
                continue
            expected = package.extractfile(member).read()
            path = folder/member.name
            if not path.is_file() or path.read_bytes() != expected:
                raise ValueError('Source archive/extracted file mismatch: '+member.name)
            source_hashes[str(path.relative_to(source))] = sha(expected)
    output = folder/'musashi_oracle_build'
    output.mkdir(parents=True, exist_ok=True)
    compiler = os.environ.get('CC', 'cc')
    version = subprocess.run([compiler, '--version'], check=True, capture_output=True, text=True).stdout
    commands = []
    command_outputs = []

    def run(arguments):
        commands.append(arguments)
        result = subprocess.run(arguments, check=True, capture_output=True, text=True)
        command_outputs.append(dict(stdout=result.stdout, stderr=result.stderr))
        return result.stdout

    generator = output/'m68kmake'
    run([compiler, '-std=c99', '-O2', str(source/'m68kmake.c'), '-o', str(generator)])
    generator_output = run([str(generator), str(output), str(source/'m68k_in.c')])
    library = output/('libmusashi_oracle.dylib' if platform.system() == 'Darwin' else 'libmusashi_oracle.so')
    definitions = ['-DM68K_EMULATE_'+variant+'=0' for variant in ('010', 'EC020', '020', '030', '040')]
    definitions += ['-DM68K_INSTRUCTION_HOOK=1', '-DM68K_EMULATE_ADDRESS_ERROR=1',
                    '-DM68K_EMULATE_PREFETCH=0', '-DM68K_SIMULATE_PD_WRITES=1']
    sources = [source/'m68kcpu.c', output/'m68kops.c', source/'softfloat/softfloat.c',
               root/'tools/native/musashi_oracle.c']
    run([compiler, '-std=c99', '-O2', '-fPIC',
         '-dynamiclib' if platform.system() == 'Darwin' else '-shared', *definitions,
         '-I'+str(source), '-I'+str(output), *[str(p) for p in sources], '-lm', '-o', str(library)])
    notices = re.findall(r'/\*.*?\*/', (source/'m68k.h').read_text(), re.DOTALL)
    license_text = next(notice for notice in notices if 'Permission is hereby granted' in notice)
    metadata = dict(schema_version=1, repository=REPOSITORY, revision=REVISION,
        archive_url=ARCHIVE_URL, archive_sha256=ARCHIVE_SHA256,
        source_file_sha256=source_hashes, license='MIT-style Musashi notice preserved verbatim; bundled SoftFloat notice also preserved',
        musashi_license_notice=license_text, softfloat_notice=(source/'softfloat/README.txt').read_text(),
        compiler_version=version, commands=commands, command_outputs=command_outputs,
        generator_stdout=generator_output, compile_definitions=definitions,
        generated_file_sha256={name:sha((output/name).read_bytes()) for name in ('m68kops.c', 'm68kops.h')},
        bridge_sha256=sha((root/'tools/native/musashi_oracle.c').read_bytes()),
        wrapper_sha256=sha((root/'tools/musashi_oracle.py').read_bytes()),
        build_script_sha256=sha((root/'tools/build_musashi_oracle.py').read_bytes()),
        library_path=str(library), library_sha256=sha(library.read_bytes()),
        cpu_model='M68000', memory_bytes=0x200000, default_sentinel_cpu_address=0xff000,
        limits='Single CPU context per process. Exact instruction budget via hook and one-cycle slices. Read-only instruction/write observers; callback failure rejects execution result. Unmapped memory is a harness fault, not modeled MMIO. Prefetch disabled; not cycle/timing equivalence. Fixture reset clears D0..D7/A0..A6, preserving hardware vector-reset PC/A7/SR. No ROM patches or game logic inference.')
    (output/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata


def main():
    metadata = build()
    print(json.dumps({key:metadata[key] for key in ('revision', 'archive_sha256', 'library_path', 'library_sha256')}))


if __name__ == '__main__':
    main()

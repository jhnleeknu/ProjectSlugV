"""Read-only dependency snapshots for original-ROM acceptance tools.

Call snapshot twice with the same root, explicit entry tools and data paths.
Exact dictionary equality checks hashes, dependency identity and directory members.
Local tool imports are followed through Python AST; unrelated tools are excluded.
"""
import ast
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys


def _hash(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            block = stream.read(1048576)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _absolute(root, path):
    path = Path(path)
    return path.absolute() if path.is_absolute() else (root / path).absolute()


def _key(root, path):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _tools(root, entries):
    pending = [_absolute(root, path) for path in entries]
    pending.append(Path(__file__).resolve())
    result = set()
    while pending:
        path = pending.pop()
        if path in result:
            continue
        if not path.is_file():
            raise FileNotFoundError('required tool: ' + str(path))
        result.add(path)
        if path.suffix != '.py':
            continue
        syntax = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(syntax):
            modules = []
            bases = [path.parent, root / 'tools']
            if isinstance(node, ast.Import):
                modules = [name.name for name in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = path.parent
                    for unused in range(node.level - 1):
                        base = base.parent
                    bases = [base]
                if node.module:
                    modules = [node.module]
                    modules += [node.module + '.' + name.name for name in node.names]
                else:
                    modules = [name.name for name in node.names]
            for module in modules:
                if module == '*':
                    continue
                relative = Path(*module.split('.'))
                for base in bases:
                    for candidate in (base / relative.with_suffix('.py'), base / relative / '__init__.py'):
                        if candidate.is_file() and candidate not in result:
                            pending.append(candidate)
    return result


def snapshot(root, tool_paths, data_paths):
    """Hash explicit data, recursive local imports and active execution dependencies.

    Data paths may be files or directory trees. Missing explicit paths fail closed.
    Keep the explicit argument lists fixed for the before/after calls. Files and
    tree membership are returned separately, so additions/removals are detected.
    """
    root = Path(root).resolve()
    files = _tools(root, tool_paths)
    trees = {}
    for value in data_paths:
        path = _absolute(root, value)
        if path.is_dir():
            members = sorted(p for p in path.rglob('*') if p.is_file())
            trees[_key(root, path)] = [_key(root, p) for p in members]
            files.update(members)
        elif path.is_file():
            files.add(path)
        else:
            raise FileNotFoundError('required data: ' + str(path))
    manifest = root / 'extracted/program/manifest.json'
    if not manifest.is_file():
        raise FileNotFoundError('required program manifest: ' + str(manifest))
    files.add(manifest)
    python = Path(sys.executable).resolve()
    compiler_name = shutil.which('clang++')
    if compiler_name is None:
        raise FileNotFoundError('required compiler: clang++')
    compiler = Path(compiler_name).resolve()
    files.update((python, compiler))
    packages = {}
    # These packages implement the active native oracle/decoder; capture their
    # Python wrappers and native shared libraries without copying or vendoring.
    import unicorn
    import capstone
    for module in (unicorn, capstone):
        package = Path(module.__file__).resolve().parent
        members = sorted(p for p in package.rglob('*') if p.is_file() and
                         (p.suffix in ('.py', '.dylib', '.dll', '.pyd') or '.so' in p.name))
        files.update(members)
        packages[module.__name__] = dict(version=module.__version__, root=str(package),
                                       files=[_key(root, p) for p in members])
    return dict(files={_key(root, path): _hash(path) for path in sorted(files)},
                trees=trees, packages=packages,
                python=dict(path=str(python), version=sys.version),
                compiler=dict(path=str(compiler), version=subprocess.check_output([str(compiler), '--version'], text=True)))

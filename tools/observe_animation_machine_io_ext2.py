"""Third IO native observation (IO-ext2): other stage groups / areas, a second player and play past the last life, recorded with the exact routing bitmap.

The pinned observer tools/observe_animation_machine_io.py and the extended-input wrapper tools/observe_animation_machine_io_ext.py are imported unchanged (the observer
file SHA256 is pinned by tools/verify_animation_machine_io.py through observation.json).  Native machinery, frame protocol, declarations, guards, records, state packs and
the exact bitmap (ext native_setup_exact) are theirs.  This wrapper changes three things from outside:
  1. input scripts and configurations come from docs/analysis/data/io-input-scripts-ext2.json (same format, version 1).  Entries that share a name with
     docs/analysis/data/io-input-scripts.json or docs/analysis/data/io-input-scripts-ext.json must be identical (checked before the run).
  2. a configuration may name its own seed cases (configs.NAME.cases, a list of natural stage seed cases); without it the configuration runs every --cases seed.
     Host writes stay fixed-frame declarations; a per-seed declaration is a per-seed configuration.
  3. the input tables are expanded to max(2048, longest configuration) frames (the observer expands 2048 frames and repeats the last one after that).
This is an observation, not natural game execution: no BIOS execution, no natural IRQ timing and no natural scheduler is claimed.  Every stage selection, setting,
credit and PLAYER_START effect is a declared host write.
observation.json gains pins.extension (this tool, the imported ext tool, the three scripts files, the shared entries, the cases) and compared_sha256 is recomputed.
Usage:
  observe_animation_machine_io_ext2.py --out DIR [--config X1,...] [--cases 94] [--frames N] [--workers 4] [--extra-routed lo-hi,...]
  observe_animation_machine_io_ext2.py --compare DIR_A DIR_B
"""
import argparse
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import observe_animation_machine_io as O  # noqa: E402  (imported unchanged)
import observe_animation_machine_io_ext as X  # noqa: E402  (imported unchanged)

SCRIPTS = ROOT / 'docs/analysis/data/io-input-scripts-ext2.json'


def check_scripts():
    """Entries shared by name with the base or the ext scripts file must be identical -> (ext2 dict, list of shared names)."""
    ext2 = json.loads(SCRIPTS.read_text())
    shared = []
    for ref in (X.BASE_SCRIPTS, X.EXT_SCRIPTS):
        other = json.loads(ref.read_text())
        assert ext2['format'] == other['format'] and ext2['version'] == other['version']
        for sect in ('scripts', 'host_write_sets', 'configs'):
            for name, val in ext2[sect].items():
                if name in other[sect]:
                    if O.canon(val) != O.canon(other[sect][name]):
                        raise SystemExit('%s %s differs from %s' % (sect, name, ref.relative_to(ROOT)))
                    shared.append('%s:%s/%s' % (ref.name, sect, name))
    for name, c in ext2['configs'].items():
        if c['family'] != 'stage' or c.get('fixture'):
            raise SystemExit('configuration %s: this wrapper runs non-fixture stage configurations only' % name)
        if 'cases' in c and not (isinstance(c['cases'], list) and c['cases'] and all(isinstance(k, int) for k in c['cases'])):
            raise SystemExit('configuration %s: cases must be a non-empty list of seed cases' % name)
    return ext2, shared


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='Third IO native observation (imports tools/observe_animation_machine_io.py and _ext.py unchanged)')
    ap.add_argument('--config', default=None, help='comma list of configurations of %s (default: all)' % SCRIPTS.relative_to(ROOT))
    ap.add_argument('--cases', default='94', help='seed cases of the configurations without their own cases (default 94)')
    ap.add_argument('--frames', type=int, default=None, help='cap on the frames of every configuration (default: the configuration frames)')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--out', default=None, help='output directory (must be new or empty; never the shared artifacts/ tree)')
    ap.add_argument('--seed-dir', default=None, help='stage_entry_body seed directory (historic pin); env MS5_SEED_DIR; default artifacts/stage_entry_body')
    ap.add_argument('--extra-routed', default='', help='comma list of hex ranges lo-hi added to the bitmap (virtual routing for unit predictions)')
    ap.add_argument('--compare', nargs=2, metavar=('DIR_A', 'DIR_B'), help='compare two output directories (observer --compare)')
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.compare:
        return O.compare_dirs(*args.compare)
    if not args.out:
        raise SystemExit('--out is required')
    t_start = time.time()
    ext2, shared = check_scripts()
    O.SCRIPTS_FILE = SCRIPTS
    extra = [tuple(int(v, 16) for v in r.split('-')) for r in args.extra_routed.split(',') if r]
    seed_dir = Path(args.seed_dir or os.environ.get('MS5_SEED_DIR') or O.SEED_DIR_DEFAULT)
    if not seed_dir.is_absolute():
        seed_dir = ROOT / seed_dir
    out_dir = Path(args.out).absolute()
    if ROOT / 'artifacts' in out_dir.parents or out_dir == ROOT / 'artifacts':
        raise SystemExit('refusing to write into the shared artifacts/ tree')
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit('output directory %s exists and is not empty (this tool never deletes; choose a new one)' % out_dir)
    scripts = O.load_scripts()
    cfgs = args.config.split(',') if args.config else list(scripts['configs'])
    for n in cfgs:
        if n not in scripts['configs']:
            raise SystemExit('unknown configuration %s' % n)
    default_cases = [int(v) for v in args.cases.split(',')]
    tasks = []
    for cfg in cfgs:
        c = scripts['configs'][cfg]
        fr = c['frames'] if args.frames is None else min(c['frames'], args.frames)
        for case in c.get('cases', default_cases):
            tasks.append(dict(config=cfg, case=case, modes=['continuous'], frames=fr, keep_all=True, out=str(out_dir)))
    out_dir.mkdir(parents=True, exist_ok=True)
    rom0 = O.rom_guard()
    X.native_setup_exact(seed_dir, extra)
    S = O.CTX['S']
    for t in tasks:
        if t['case'] not in S.SEEDS or S.SEEDS[t['case']]['kind'] != 'natural':
            raise SystemExit('case %d is not a natural stage seed' % t['case'])
    O.EXPAND_FRAMES = max([O.EXPAND_FRAMES] + [t['frames'] for t in tasks])   # recorded as pins.input_scripts.expanded_frames
    O.CTX['scripts'] = scripts
    O.CTX['tables'] = dict((name, O.expand_script(sd, O.EXPAND_FRAMES)) for name, sd in scripts['scripts'].items())
    O.CTX['IoRun'] = O.make_io_class()
    O.CTX['boot'] = {}
    print('io-ext2: exact routing bitmap %s routed even PCs %d extra %s, %d runs' % (O.CTX['routing']['sha256'][:16], O.CTX['routing']['routed_even_pcs'],
          args.extra_routed or '-', len(tasks)), file=sys.stderr, flush=True)
    tasks.sort(key=lambda t: (-t['frames'], t['config'], t['case']))
    ctx = multiprocessing.get_context('fork')

    class Args(object):
        pass
    oargs = Args()
    oargs.frames = max(t['frames'] for t in tasks)
    oargs.boot_frames = 0
    oargs.workers = args.workers
    oargs.selftest = False
    results = O.run_phase(ctx, oargs, tasks, 'io-ext2', t_start)
    O.write_outputs(oargs, out_dir, [r['entry'] for r in results], None, scripts, rom0, time.time() - t_start, [])
    obs_path = out_dir / 'observation.json'
    obs = json.loads(obs_path.read_text())

    def pin(p):
        return dict(path=str(p.relative_to(ROOT)), sha256=O.file_sha(p))
    obs['pins']['extension'] = dict(tool=pin(Path(__file__).resolve()), ext_tool=pin(Path(X.__file__).resolve()), scripts=pin(SCRIPTS), base_scripts=pin(X.BASE_SCRIPTS),
                                    ext_scripts=pin(X.EXT_SCRIPTS), shared_identical=shared, cases=sorted(set(t['case'] for t in tasks)),
                                    runs=sorted([t['config'], t['case']] for t in tasks), configs=cfgs,
                                    orchestration='every (configuration, case) one continuous run with all frame-start states; configs.*.cases restricts the seeds')
    obs['compared_sha256'] = O.recompute_compared_sha(obs)
    obs_path.write_text(json.dumps(obs, indent=1, sort_keys=True))
    plat_path = out_dir / 'platform.json'
    plat = json.loads(plat_path.read_text())
    plat['compared_sha256'] = obs['compared_sha256']
    plat_path.write_text(json.dumps(plat, indent=1, sort_keys=True))
    print('io-ext2 observation.json sha256 %s compared_sha256 %s' % (O.file_sha(obs_path), obs['compared_sha256']), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())

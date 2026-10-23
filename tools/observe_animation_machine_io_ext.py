"""Extended-input IO native observation (IO-ext): more player input configurations, recorded with an exact routing bitmap.

The pinned observer tools/observe_animation_machine_io.py is imported unchanged (its file SHA256 is pinned by tools/verify_animation_machine_io.py through
observation.json).  This wrapper changes three things from outside, without editing the observer file:
  1. input scripts and configurations come from docs/analysis/data/io-input-scripts-ext.json (same format, version 1).  Entries that the extension file shares by
     name with docs/analysis/data/io-input-scripts.json must be identical (checked before the run; P0 / P1 are re-observed as controls).
  2. the TB coverage bitmap is the exact set of PCs routed by the checked-out dispatch chain (verify_animation_machine_unit_fixtures.pc_routed over every even PC
     below 100000), optionally plus --extra-routed ranges (virtual routing for unit predictions).  The observer's own bitmap (observation-time routing 8ce8eb93 plus
     the intra-function closure of single-PC atoms [I]) is not used.  The bitmap only decides which TB instruction is recorded; native execution does not depend on it.
  3. orchestration: every requested (configuration, seed case) is one continuous run with all frame-start states (the IO verifier needs them); no class
     representatives, no fresh-CPU split.  Stage family only.
Everything else (native machinery, frame protocol, declared IRQ / card / BIOS returns, guards, records, state packs, observation.json / platform.json) is the observer's.
This is an observation, not natural game execution: no BIOS execution, no natural IRQ timing and no natural scheduler is claimed.

observation.json gains pins.extension (this tool's SHA256, the extension scripts file, the base scripts file, the bitmap) and compared_sha256 is recomputed over it.
Usage:
  observe_animation_machine_io_ext.py --out DIR [--config P0,P1,...] [--cases 94,68] [--frames 900] [--workers 3] [--extra-routed lo-hi,...]
  observe_animation_machine_io_ext.py --compare DIR_A DIR_B
"""
import argparse
import hashlib
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

EXT_SCRIPTS = ROOT / 'docs/analysis/data/io-input-scripts-ext.json'
BASE_SCRIPTS = ROOT / 'docs/analysis/data/io-input-scripts.json'
ROUTING_FILE = ROOT / 'engine/src/animation_machine.cpp'


def check_scripts():
    """Extension entries shared by name with the base scripts file must be identical -> (ext dict, list of shared names)."""
    ext = json.loads(EXT_SCRIPTS.read_text())
    base = json.loads(BASE_SCRIPTS.read_text())
    assert ext['format'] == base['format'] and ext['version'] == base['version']
    shared = []
    for sect in ('scripts', 'host_write_sets', 'configs'):
        for name, val in ext[sect].items():
            if name in base[sect]:
                if O.canon(val) != O.canon(base[sect][name]):
                    raise SystemExit('extension %s %s differs from the base scripts file' % (sect, name))
                shared.append('%s/%s' % (sect, name))
    for name, c in ext['configs'].items():
        if c['family'] != 'stage' or c.get('fixture'):
            raise SystemExit('configuration %s: this wrapper runs non-fixture stage configurations only' % name)
    return ext, shared


def exact_bitmap(extra):
    import verify_animation_machine_unit_fixtures as U
    bm = bytearray(0x100000)
    for pc in range(0, 0x100000, 2):
        if U.pc_routed(pc):
            bm[pc] = 1
    for lo, hi in extra:
        for pc in range((lo + 1) & ~1, min(hi, 0x100000), 2):
            bm[pc] = 1
    return bm


def native_setup_exact(seed_dir, extra):
    """observer native_setup without the observation-time routing pin: same tool / ROM / seed pins, exact bitmap of the checked-out routing."""
    for name, expect in O.TOOL_PINS.items():
        got = O.file_sha(TOOLS / name)
        if got != expect:
            raise SystemExit('imported tool %s changed: %s != pinned %s' % (name, got, expect))
    rg = O.rom_guard()
    if rg['sha256'] != O.ROM_SHA:
        raise SystemExit('ROM SHA256 mismatch %s' % rg['sha256'])
    import verify_animation_machine_frame_driver as D
    import verify_animation_machine_frame_controller as VC
    import verify_animation_machine_frame_irq as VI
    import measure_code_coverage as MC

    class Opt(object):
        pass
    opt = Opt()
    opt.seed_dir = str(seed_dir)
    D.apply_seed_option(opt)
    rebase, routing_info, pins = D.setup_native()
    if rebase['seed_sha256'] != O.HISTORIC_SEED_SHA:
        raise SystemExit('unexpected seed observation %s (the observer pins the historic stage_entry_body %s)' % (rebase['seed_sha256'], O.HISTORIC_SEED_SHA))
    O.CTX.update(D=D, VC=VC, VI=VI, MC=MC, FH=D.FH, S=D.S, R=D.R, rebase=rebase, rom=rg, routing_info=routing_info)
    bm = exact_bitmap(extra)
    disc = MC.Discovery(bytes(D.R.G['program'][:0x100000]))
    O.CTX.update(atoms=None, routed2=bm, disc=disc, unr_cache={})
    O.CTX['routing'] = dict(file=str(ROUTING_FILE.relative_to(ROOT)), sha256=O.file_sha(ROUTING_FILE), routed_even_pcs=sum(bm),
                            extra_routed=['%x-%x' % r for r in extra],
                            method='exact: verify_animation_machine_unit_fixtures.pc_routed over every even PC < 100000 (+ extra_routed); no intra-function closure')
    return O.CTX


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='Extended-input IO native observation (imports tools/observe_animation_machine_io.py unchanged)')
    ap.add_argument('--config', default=None, help='comma list of configurations of %s (default: all)' % EXT_SCRIPTS.relative_to(ROOT))
    ap.add_argument('--cases', default='94,68', help='comma list of stage seed cases (default 94,68: the two P1 player classes)')
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
    ext, shared = check_scripts()
    O.SCRIPTS_FILE = EXT_SCRIPTS
    extra = [tuple(int(x, 16) for x in r.split('-')) for r in args.extra_routed.split(',') if r]
    seed_dir = Path(args.seed_dir or os.environ.get('MS5_SEED_DIR') or O.SEED_DIR_DEFAULT)
    if not seed_dir.is_absolute():
        seed_dir = ROOT / seed_dir
    out_dir = Path(args.out).absolute()
    if ROOT / 'artifacts' in out_dir.parents or out_dir == ROOT / 'artifacts':
        raise SystemExit('refusing to write into the shared artifacts/ tree')
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit('output directory %s exists and is not empty (this tool never deletes; choose a new one)' % out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rom0 = O.rom_guard()
    native_setup_exact(seed_dir, extra)
    scripts = O.load_scripts()
    O.CTX['scripts'] = scripts
    O.CTX['tables'] = dict((name, O.expand_script(sd)) for name, sd in scripts['scripts'].items())
    O.CTX['IoRun'] = O.make_io_class()
    O.CTX['boot'] = {}
    S = O.CTX['S']
    cfgs = args.config.split(',') if args.config else list(scripts['configs'])
    for n in cfgs:
        if n not in scripts['configs']:
            raise SystemExit('unknown configuration %s' % n)
    cases = [int(x) for x in args.cases.split(',')]
    for c in cases:
        if c not in S.SEEDS or S.SEEDS[c]['kind'] != 'natural':
            raise SystemExit('case %d is not a natural stage seed' % c)
    print('io-ext: exact routing bitmap %s routed even PCs %d extra %s' % (O.CTX['routing']['sha256'][:16], O.CTX['routing']['routed_even_pcs'], args.extra_routed or '-'),
          file=sys.stderr, flush=True)
    tasks = []
    for cfg in cfgs:
        fr = scripts['configs'][cfg]['frames'] if args.frames is None else min(scripts['configs'][cfg]['frames'], args.frames)
        for case in cases:
            tasks.append(dict(config=cfg, case=case, modes=['continuous'], frames=fr, keep_all=True, out=str(out_dir)))
    tasks.sort(key=lambda t: (-t['frames'], t['config'], t['case']))
    ctx = multiprocessing.get_context('fork')

    class Args(object):
        pass
    oargs = Args()
    oargs.frames = max(t['frames'] for t in tasks)
    oargs.boot_frames = 0
    oargs.workers = args.workers
    oargs.selftest = False
    results = O.run_phase(ctx, oargs, tasks, 'io-ext', t_start)
    entries = [r['entry'] for r in results]
    O.write_outputs(oargs, out_dir, entries, None, scripts, rom0, time.time() - t_start, [])
    # extension pins, then compared_sha256 over the whole observation again
    obs_path = out_dir / 'observation.json'
    obs = json.loads(obs_path.read_text())
    obs['pins']['extension'] = dict(tool=dict(path=str(Path(__file__).resolve().relative_to(ROOT)), sha256=O.file_sha(Path(__file__).resolve())),
                                    scripts=dict(path=str(EXT_SCRIPTS.relative_to(ROOT)), sha256=O.file_sha(EXT_SCRIPTS)),
                                    base_scripts=dict(path=str(BASE_SCRIPTS.relative_to(ROOT)), sha256=O.file_sha(BASE_SCRIPTS), shared_identical=shared),
                                    cases=cases, configs=cfgs, orchestration='every (configuration, case) one continuous run with all frame-start states')
    obs['compared_sha256'] = O.recompute_compared_sha(obs)
    obs_path.write_text(json.dumps(obs, indent=1, sort_keys=True))
    plat_path = out_dir / 'platform.json'
    plat = json.loads(plat_path.read_text())
    plat['compared_sha256'] = obs['compared_sha256']
    plat_path.write_text(json.dumps(plat, indent=1, sort_keys=True))
    print('io-ext observation.json sha256 %s compared_sha256 %s' % (O.file_sha(obs_path), obs['compared_sha256']), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())

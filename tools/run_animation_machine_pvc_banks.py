#!/usr/bin/env python3
"""Runs tools/observe_animation_machine_pvc_banks.py (unchanged, its SHA-256 is pinned by other tools) with --input-tree / --reference-dir
instead of the machine-specific historic paths, and records the locations in <out>/input_locations.json."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import observe_animation_machine_pvc_banks as O

DEFAULT_INPUT_TREE=O.INPUT_TREE
DEFAULT_REFERENCE_DIR=O.ROOT/'artifacts/reference'
TREE_FILES=('engine/src/animation_machine.cpp','engine/src/program_bus.cpp','engine/src/animation_machine_objects_u06.cpp')
REF_FILES=('prot_pvc.cpp','neogeo.cpp')


def sha(b):return hashlib.sha256(b).hexdigest()


def input_pins():
    pins={}
    for path in (O.REF_PVC,O.REF_NEOGEO):pins['artifacts/reference/'+path.name]=sha(path.read_bytes())
    for path in (O.INPUT_ROUTING,O.INPUT_BUS,O.INPUT_TREE/TREE_FILES[2]):pins['metalslug-input/'+str(path.relative_to(O.INPUT_TREE))]=sha(path.read_bytes())
    return pins


def tool_pins():
    """Same dict (keys and order) as O.tool_pins, but the reference dir may live outside ROOT."""
    pins={}
    for name in ('observe_animation_machine_scheduler.py',)+O.S.IMPORTED_TOOLS:pins['tools/'+name]=sha((O.ROOT/'tools'/name).read_bytes())
    for path in (O.S.F2_CONTRACT,O.S.F3_CONTRACT,O.U06_CONTRACT,O.S.SEED_OBS):pins[str(path.relative_to(O.ROOT))]=sha(path.read_bytes())
    pins.update(input_pins())
    return pins


def configure_inputs(input_tree,reference_dir):
    tree=Path(input_tree).expanduser();ref=Path(reference_dir).expanduser()
    missing=[str(p) for p in [tree/f for f in TREE_FILES]+[ref/f for f in REF_FILES] if not p.is_file()]
    if missing:raise SystemExit('missing required input files (--input-tree / --reference-dir):\n  '+'\n  '.join(missing))
    O.INPUT_TREE=tree;O.INPUT_ROUTING=tree/TREE_FILES[0];O.INPUT_BUS=tree/TREE_FILES[1]
    O.REF_PVC=ref/REF_FILES[0];O.REF_NEOGEO=ref/REF_FILES[1];O.tool_pins=tool_pins


def build_parser():
    ap=argparse.ArgumentParser(description='Run the PVC bank observer with explicit input locations; other options (--workers) pass through to it.')
    ap.add_argument('--input-tree',default=str(DEFAULT_INPUT_TREE));ap.add_argument('--reference-dir',default=str(DEFAULT_REFERENCE_DIR));ap.add_argument('--out',default=str(O.OUT))
    return ap


def main(argv=None):
    args,rest=build_parser().parse_known_args(argv)
    configure_inputs(args.input_tree,args.reference_dir)
    summary=O.main(['--out',args.out]+rest)
    out_dir=Path(args.out).resolve()
    side=dict(schema_version=1,tool='tools/run_animation_machine_pvc_banks.py',tool_sha256=sha(Path(__file__).read_bytes()),observer='tools/observe_animation_machine_pvc_banks.py',
        observer_sha256=sha(Path(O.__file__).read_bytes()),input_tree=str(Path(args.input_tree).expanduser()),reference_dir=str(Path(args.reference_dir).expanduser()),
        observation_sha256=sha((out_dir/'observation.json').read_bytes()))
    (out_dir/'input_locations.json').write_text(json.dumps(side,indent=1,sort_keys=True)+'\n')
    return summary


if __name__=='__main__':main()

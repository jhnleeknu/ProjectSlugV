"""Explicit bounded coordinate instruction candidates, not semantic completion."""
import argparse
import hashlib
import json
from pathlib import Path

from disassemble_program import load_verified_program, disassemble_range
from pack_scene_scripts import SOURCE_SHA256
from inventory_object_removal import controls

WINDOWS=((0x1a7a8,0x1a910),(0x43dda,0x43e04),(0x43e22,0x43e34),
         (0x43e38,0x43ea4),(0x43ea8,0x43eb8),(0x16fac,0x16ff8),(0x1724c,0x17292))


def window(program,start,end):
    rows=disassemble_range(program,start,end-start,start)
    assert sum(row['size']for row in rows)==end-start
    assert all(row['rom_offset']+row['size']<=end for row in rows)
    return dict(start_cpu_address=start,start_rom_offset=start,end_exclusive=end,
        raw_sha256=hashlib.sha256(program[start:end]).hexdigest(),instructions=rows,
        rts_candidates=[row['cpu_address']for row in rows if row['mnemonic']=='rts'],
        undecoded_rows=[row for row in rows if row['classification']!='candidate_instruction'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='artifacts/scene_coordinates');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=SOURCE_SHA256:raise ValueError('Unsupported canonical source')
    windows=[window(program,start,end)for start,end in WINDOWS]
    clear_probe=window(program,0x17292,0x17500)
    clear_complete=window(program,0x17292,0x1829a)
    assert program[0x17298:0x18298]==bytes.fromhex('22c0')*2048
    assert program[0x18298:0x1829a]==bytes.fromhex('4e75')
    prefix=window(program,0x1a7a8,0x1a8ca)
    prefix_calls=[item for item in controls(prefix['instructions'])if item['mnemonic'].split('.')[0]in('jsr','bsr')]
    tail=window(program,0x1a8ca,0x1a910)
    tail_calls=[item for item in controls(tail['instructions'])if item['mnemonic'].split('.')[0]in('jsr','bsr')]
    report=dict(source=source,program_code_modified=False,mapping='Explicit first1MiB fixed-ROM CPU addresses equal ROM offsets.',
        windows=windows,clear_17292_bounded_probe=clear_probe,
        clear_17292_confirmed_span=clear_complete,clear_raw_22c0_repeat_count=2048,
        clear_actual_rts_cpu_address=0x18298,prefix_direct_calls=prefix_calls,
        deferred_tail_direct_calls=tail_calls,
        clear_probe_scope='Initial bounded17500 probe has noRTS; main confirmed18298 RTS. Exact22c0*2048 raw pattern and terminal4e75 asserted in extended span.',
        limitations='Full bounded candidate instructions only, not execution/semantic completion. No firstRTS ownership inference; branches/callees unresolved. '
            'Coordinate implementation scope is1a7a8..1a8ca before1afda/four19e64, not entire1a7a8 function.')
    output=Path(args.output);output=output if output.is_absolute()else root/output;output.mkdir(parents=True,exist_ok=True)
    path=output/'disassembly.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(windows=len(windows),rows=sum(len(w['instructions'])for w in windows),
        clear_probe_rows=len(clear_probe['instructions']),clear_probe_rts=clear_probe['rts_candidates'],
        confirmed_clear_rows=len(clear_complete['instructions']),confirmed_rts=0x18298,
        prefix_direct_calls=len(prefix_calls),deferred_tail_calls=len(tail_calls),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest())))


if __name__=='__main__':main()

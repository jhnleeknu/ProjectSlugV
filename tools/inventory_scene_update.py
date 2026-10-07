"""Reproducible explicit scene-update instruction windows, not semantic completion."""
import hashlib
import json
from pathlib import Path
from disassemble_program import load_verified_program, disassemble_range

SOURCE_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS=((0x1afda,0x1b128),(0xca9e,0xcb64),(0x35a2,0x35f0),(0x1a7a8,0x1a910),(0x1a5a4,0x1a73c))


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);before=hashlib.sha256(program).hexdigest()
    if source['sha256']!=SOURCE_SHA256 or before!=SOURCE_SHA256:raise ValueError('Unsupported canonical source')
    windows=[]
    for start,end in WINDOWS:
        rows=disassemble_range(program,start,end-start,start)
        if sum(r['size']for r in rows)!=end-start or any(r['rom_offset']+r['size']>end for r in rows):raise ValueError('Incomplete bounded coverage')
        windows.append(dict(start_cpu_address=start,start_rom_offset=start,end_cpu_address_exclusive=end,end_rom_offset_exclusive=end,raw_sha256=hashlib.sha256(program[start:end]).hexdigest(),instructions=rows,rts_candidate_addresses=[r['cpu_address']for r in rows if r['mnemonic']=='rts'],undecoded_rows=[r for r in rows if r['classification']!='candidate_instruction']))
    if hashlib.sha256(program).hexdigest()!=before:raise ValueError('Source mutated')
    report=dict(source=source,program_code_modified=False,mapping='Explicit fixed first1MiB CPU addresses equal canonical ROM offsets.',windows=windows,scope='Full supplied bounded windows with padded Capstone decoding and truncated/invalid dc.w preservation. No firstRTS endpoint inference, code/data ownership, callee semantics or execution completion claim.',recommended_regression_commands=['.venv/bin/python tools/verify_scene_initialization.py','.venv/bin/python tools/verify_scene_coordinates.py'],regressions_executed=False)
    output=root/'artifacts/scene_update';output.mkdir(parents=True,exist_ok=True);path=output/'disassembly.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(windows=len(windows),rows=sum(len(w['instructions'])for w in windows),undecoded=sum(len(w['undecoded_rows'])for w in windows),last_rows=[dict(start=w['start_cpu_address'],last=w['instructions'][-1])for w in windows],report_sha256=hashlib.sha256(path.read_bytes()).hexdigest())))

if __name__=='__main__':main()

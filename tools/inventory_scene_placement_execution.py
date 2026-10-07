"""Explicit placement-execution candidate windows, no semantic inference."""
import hashlib
import json
from pathlib import Path
from disassemble_program import load_verified_program,disassemble_range

SOURCE_SHA256='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
WINDOWS=((0x1a414,0x1a442),(0x1a470,0x1a526),(0x43e08,0x43e22))


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);before=hashlib.sha256(program).hexdigest()
    if before!=SOURCE_SHA256 or source['sha256']!=SOURCE_SHA256:raise ValueError('Unsupported canonical source')
    windows=[]
    for start,end in WINDOWS:
        rows=disassemble_range(program,start,end-start,start)
        assert sum(r['size']for r in rows)==end-start
        assert all(r['rom_offset']+r['size']<=end for r in rows)
        windows.append(dict(start_cpu_address=start,start_rom_offset=start,end_cpu_address_exclusive=end,end_rom_offset_exclusive=end,raw_sha256=hashlib.sha256(program[start:end]).hexdigest(),instructions=rows,undecoded_rows=[r for r in rows if r['classification']!='candidate_instruction']))
    assert hashlib.sha256(program).hexdigest()==before
    report=dict(source=source,program_code_modified=False,mapping='Fixed first1MiB CPU addresses equal ROM offsets.',windows=windows,scope='Only three main-confirmed explicit windows using padded decoder. Incomplete/invalid dc.w retained. No routine-completion, callee effects, semantic inference or execution equivalence claim. Optional28ae..28c0 window is not included.')
    folder=root/'artifacts/scene_placement_execution';folder.mkdir(parents=True,exist_ok=True);path=folder/'disassembly.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(windows=len(windows),rows=sum(len(w['instructions'])for w in windows),undecoded=sum(len(w['undecoded_rows'])for w in windows),per_window=[dict(start=w['start_cpu_address'],rows=len(w['instructions']),raw_sha256=w['raw_sha256'],last=w['instructions'][-1])for w in windows],sha256=hashlib.sha256(path.read_bytes()).hexdigest())))

if __name__=='__main__':main()

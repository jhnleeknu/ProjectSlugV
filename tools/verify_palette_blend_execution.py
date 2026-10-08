"""Frozen native480 full8cda RAM/register observations versus actual CLI."""
import collections
import json
import os
from pathlib import Path
import subprocess
import tempfile
from observe_palette_blend_full import (BASE,STACK,RETURN,ENTRY,END,KEYS,BRANCHES,
    SOURCE_SHA256,sha,build_cases,fixture,load_verified_program,oracle_provenance)


def invoke(exe,regs,inp,out):
    return subprocess.run([str(exe)]+[str(regs[k]) for k in KEYS]+list(map(str,(inp,out))),
        capture_output=True,text=True,timeout=2)


def audit(root,program,source):
    folder=root/'artifacts/palette_blend_full';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert native['source']==source and native['oracle']==oracle_provenance(root)
    assert native['cases']==len(native['results'])==len(build_cases())==480 and native['RAM_write_count']==600
    assert native['native_register_contract_assertions_passed'] and native['full_RAM_captured'] and native['exact_CPU_write_replay_passed'] and native['SR_set_before_A7']
    assert not native['program_code_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    assert native['entry']==ENTRY and native['return_instruction']==0x8d32
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,name
    instruction_pcs=set()
    for row in native['instructions']:
        at=row['rom_offset'];assert row['cpu_address']==at and bytes.fromhex(row['raw'])==program[at:at+row['size']]
        assert row['classification']=='candidate_instruction';instruction_pcs.add(at)
    assert min(instruction_pcs)==ENTRY and max(instruction_pcs)==END-2
    artifacts={str(path.relative_to(root)):sha(raw)};branches=collections.defaultdict(set);writes=0;counts=collections.Counter()
    for index,(case,row) in enumerate(zip(build_cases(),native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs=fixture(case);assert row['incoming']==dict(zip(KEYS,regs))
        for key,digest in (('input_ram_file','input_ram_sha256'),('native_ram_file','native_ram_sha256')):
            p=folder/row[key];assert sha(p.read_bytes())==row[digest];artifacts[str(p.relative_to(root))]=row[digest]
        assert (folder/row['input_ram_file']).read_bytes()==ram
        assert row['status']['status']=='sentinel' and row['status']['pc']==row['final_pc']==RETURN and not row['status']['fault_address']
        assert row['final_a7']==STACK+4
        pcs=row['pcs'];assert pcs[0]==ENTRY and all(pc in instruction_pcs for pc in pcs)
        assert program[pcs[-1]:pcs[-1]+2]==b'\x4e\x75' and len(pcs)==row['status']['instructions']
        for pc,next_pc in zip(pcs,pcs[1:]):
            if pc in BRANCHES:branches[pc].add(next_pc)
        replay=bytearray(ram);slot=0x104d92+case['slot']*16
        for event in row['RAM_writes']:
            pc,address,size,value=(event[k] for k in ('pc','address','size','value'))
            assert pc in pcs and 0<=value<1<<(size*8)
            assert (pc,address,size) in ((0x8d06,slot+12,2),(0x8d0a,slot+14,1),(0x8d0e,slot+15,1),(0x8d20,slot+14,1),(0x8d2c,slot+15,1))
            replay[address-BASE:address-BASE+size]=value.to_bytes(size,'big')
        write_positions=[pcs.index(event['pc']) for event in row['RAM_writes']]
        assert write_positions==sorted(write_positions)
        assert bytes(replay)==(folder/row['native_ram_file']).read_bytes()
        assert row['status']['cpu_writes']==len(row['RAM_writes']);writes+=len(row['RAM_writes'])
        result=row['result'];incoming=row['incoming'];assert set(result)==set(KEYS)
        assert result['d0']==(incoming['d0']&0xffff0000)|((incoming['d0']&255)<<4)
        assert result['a1']==0x104d92 and result['a2']==slot and result['a5']==case['a5']
        clamped=bool(case['reference']) and case['incoming_weight']>=32
        assert result['d2']==(32 if clamped else incoming['d2'])
        for key in KEYS:
            if key not in ('d0','d2','a1','a2'):assert result[key]==incoming[key]
        if not case['reference']:assert not row['RAM_writes'] and bytes(replay)==ram
        counts['active' if case['reference'] else 'reference-zero-bypass']+=1
        counts['D2-full-MOVEQ' if clamped else 'D2-preserved']+=1
        counts['initial-dirty' if case['initial_flag']&128 else 'initial-clean']+=1
    assert writes==native['RAM_write_count'] and {hex(pc):sorted(branches[pc]) for pc in BRANCHES}==native['branches']
    assert all(len(branches[pc])==2 for pc in BRANCHES)
    assert set(c['incoming_weight'] for c in build_cases())=={0,31,32,33,255}
    assert set((c['base_id_same'],bool(c['initial_flag']&128)) for c in build_cases())=={(False,False),(False,True),(True,False),(True,True)}
    return native,raw,artifacts,dict(counts)


def negatives(exe,folder,row,ram):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out=work/'input.bin',work/'output.bin';sentinel=b'preserved-blend-output';regs=row['incoming']
        def reject(label,state=regs,payload=ram,source=None,destination=None,command=None):
            inp.write_bytes(payload);out.write_bytes(sentinel)
            src=inp if source is None else source;dest=out if destination is None else destination
            watched={p:p.read_bytes() for p in (inp,out,src,dest) if p.exists() and p.is_file()}
            p=subprocess.run(command,capture_output=True,text=True,timeout=2) if command else invoke(exe,state,src,dest)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,input_outputs_preserved=True,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        for key in KEYS:
            for bad in ('-1','4294967296','0x100000000','0x','1x',''):
                reject('register-parser-'+key,state=dict(regs,**{key:bad}))
        reject('missing-arguments',command=[str(exe)])
        reject('extra-argument',command=[str(exe)]+[str(regs[k]) for k in KEYS]+[str(inp),str(out),'extra'])
        reject('missing-input',source=work/'absent-input');reject('input-directory',source=work)
        reject('output-directory',destination=work);reject('missing-output-parent',destination=work/'absent'/'output.bin')
        reject('input-output-identical',destination=inp)
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-output-'+kind,destination=alias)
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-output',destination=fifo)
        fresh=work/'fresh-output'
        reject('invalid-RAM-does-not-leave-new-output',payload=b'',destination=fresh);assert not fresh.exists()
        reject('invalid-register-does-not-leave-new-output',state=dict(regs,d0='-1'),destination=fresh);assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            alias=work/'INPUT.BIN';assert os.path.samefile(inp,alias)
            reject('case-insensitive-input-output-alias',destination=alias);case_alias['input_preserved']=True
    return rows,case_alias


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/palette_blend_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True);exe=root/'build/execute_palette_blend'
    names=('tools/verify_palette_blend_execution.py','build/execute_palette_blend','engine/tools/execute_palette_blend.cpp',
        'engine/src/palette_blend_execution.cpp','engine/src/palette_control.cpp',
        'engine/include/ms5/palette_blend_execution.h','engine/include/ms5/palette_control.h',
        'engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,artifacts,coverage=audit(root,program,source)
    inp,out=folder/'input.bin',folder/'cpp.bin';native_folder=root/'artifacts/palette_blend_full';rows=[]
    for row in native['results']:
        ram=(native_folder/row['input_ram_file']).read_bytes();expected=(native_folder/row['native_ram_file']).read_bytes()
        inp.write_bytes(ram);out.write_bytes(b'previous-output')
        p=invoke(exe,row['incoming'],inp,out);assert not p.returncode,(row['case_index'],p.stderr)
        parsed=json.loads(p.stdout)
        assert parsed==row['result'] and inp.read_bytes()==ram and out.read_bytes()==expected,row['case_index']
        rows.append(dict(case_index=row['case_index'],fixture=row['fixture'],result=parsed,ram_sha256=sha(expected)))
    fresh=folder/'fresh-output.bin';fresh.unlink(missing_ok=True)
    row=native['results'][-1];ram=(native_folder/row['input_ram_file']).read_bytes();inp.write_bytes(ram)
    p=invoke(exe,row['incoming'],inp,fresh)
    assert not p.returncode and json.loads(p.stdout)==row['result'] and inp.read_bytes()==ram and fresh.read_bytes()==(native_folder/row['native_ram_file']).read_bytes()
    rejected,case_alias=negatives(exe,folder,row,ram)
    for name,digest in dict(inputs,**native['inputs'],**artifacts).items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance(root)==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],native_artifacts=artifacts,
        native_observation_sha256=sha(raw),cases=len(rows),RAM_write_count=native['RAM_write_count'],coverage=coverage,branches=native['branches'],
        negative_cases=rejected,case_alias_regression=case_alias,fresh_output_creation_native_equal=True,
        full_RAM_15_registers_equal=True,source_and_inputs_unchanged=True,source_program_modified=False,in_call_SR_read=False,
        results=rows,scope='Immutable original8cda through actual RTS in pinnedMusashi versus actualCLI;480 native cases and600 CPU writes replayed. ArbitraryA5 preserved, conditional fullD2 MOVEQ32, D0WORD mask/shift and A1/A2 observed. No resources/ports, CCR/cycles, physical RAM mirror, scheduler or rendered pixel equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),negative_cases=len(rejected),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()

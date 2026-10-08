"""Actual corrected C++ API/CLI versus immutable original4843c Unicorn evidence.

The batch expected RAM uses observed BYTE writes, never a BCD implementation.
Unicorn source0 SBCD support is independently checked against pinned third-party
hardware-tested reference; no local hardware experiment is claimed.
"""
import collections
import json
import os
from pathlib import Path
import subprocess
import tempfile
from observe_stage_counter import (BASE,STACK,RETURN,ENTRY,END,KEYS,BRANCHES,RECORD,
    SOURCE_SHA256,sha,fixture,sweep_case,build_cases,RAM_PROFILES,load_verified_program,provenance)


def invoke(exe,regs,inp,out):
    return subprocess.run([str(exe)]+[str(regs[k]) for k in KEYS]+list(map(str,(inp,out))),
        capture_output=True,text=True,timeout=2)


def audit(root,program,source):
    folder=root/'artifacts/stage_counter/unicorn';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert native['source']==source and native['oracle']==provenance(root,'unicorn')
    assert native['oracle_choice']=='unicorn' and native['acceptance_oracle']
    assert native['word_cases']==65536 and native['detailed_cases']==109 and native['full_WORD_domain_completed'] and not native['diagnostic_only']
    assert native['full_RAM_15_registers_observed'] and native['compact_RAM_write_replay_passed'] and native['SR_before_A7']
    assert not native['program_code_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,name
    instruction_pcs=set()
    for row in native['instructions']:
        at=row['rom_offset'];assert row['cpu_address']==at and bytes.fromhex(row['raw'])==program[at:at+row['size']]
        assert row['classification']=='candidate_instruction';instruction_pcs.add(at)
    assert min(instruction_pcs)==ENTRY and max(instruction_pcs)==END-2 and program[END-2:END]==b'\x4e\x75'
    compact=native['compact_records'];assert compact['schema_version']==1 and compact['record_bytes']==99 and compact['count']==65536
    assert compact['byte_order']=='big' and compact['struct_format']==RECORD.format
    assert compact['fields']==['input_WORD','output_WORD']+list(KEYS)+['output_RAM_SHA256_bytes32','trace_id_u16','CPU_write_count_u8']
    records_path=folder/compact['file'];records=records_path.read_bytes()
    assert len(records)==65536*99 and sha(records)==compact['sha256']
    artifacts={str(path.relative_to(root)):sha(raw),str(records_path.relative_to(root)):sha(records)}
    branches=collections.defaultdict(collections.Counter);write_total=0;clamps=0;selected=[]
    catalog=native['trace_catalog'];assert [r['id'] for r in catalog]==list(range(len(catalog)))
    def trace(pcs):
        assert pcs[0]==ENTRY and pcs[-1]==END-2 and all(pc in instruction_pcs for pc in pcs)
        for pc,nxt in zip(pcs,pcs[1:]):
            if pc in BRANCHES:branches[pc][nxt]+=1
    for word in range(65536):
        values=RECORD.unpack_from(records,word*99);assert values[0]==word
        ram,regs,_=fixture(sweep_case(word));replay=bytearray(ram);shape=catalog[values[-2]];trace(shape['pcs'])
        assert values[-1]==len(shape['writes'])==2
        assert shape['writes']==[dict(pc=0x48472,address=0x10d67e,size=1),dict(pc=0x48476,address=0x10d67f,size=1)]
        replay[0xd67e:0xd680]=values[1].to_bytes(2,'big');assert sha(replay)==values[-3].hex()
        result=dict(zip(KEYS,values[2:17]));assert result['d2']==0
        for k in KEYS:
            if k not in ('d0','d1','d2'):assert result[k]==regs[k]
        write_total+=2;clamps+=int(0x4846e in shape['pcs'])
        if word&255 in (0,2):selected.append((dict(family='full-high-BYTE-cross-low0-or2',word=word),ram,regs,bytes(replay),result))
    assert write_total==native['sweep_RAM_write_count']==131072 and clamps==native['sweep_clamp_branch_count']
    assert len(native['results'])==len(build_cases())==109
    for index,(case,row) in enumerate(zip(build_cases(),native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs,host=fixture(case);assert row['incoming']==regs and row['host_writes']==host
        files=row['files'];assert len(files)==2
        for name,digest in files.items():
            p=folder/name;assert sha(p.read_bytes())==digest;artifacts[str(p.relative_to(root))]=digest
        assert (folder/('case-%03d-input.bin'%index)).read_bytes()==ram
        expected=(folder/('case-%03d-native.bin'%index)).read_bytes();trace(row['pcs'])
        assert row['status']['status']=='sentinel' and row['status']['pc']==row['final_pc']==RETURN and row['final_a7']==STACK+4
        assert not row['status']['fault_address'] and row['status']['instructions']==len(row['pcs'])
        assert row['status']['cpu_writes']==len(row['RAM_writes'])
        assert [s['pc'] for s in row['steps']]==row['pcs'] and row['steps'][0]['registers']==regs
        replay=bytearray(ram)
        for event in row['RAM_writes']:
            assert (event['pc'],event['address'],event['size']) in ((0x48472,regs['a5']+0x567e,1),(0x48476,regs['a5']+0x567f,1))
            assert 0<=event['value']<=255;replay[event['address']-BASE]=event['value']
        assert bytes(replay)==expected and set(row['result'])==set(KEYS)
        if row['RAM_writes']:assert [r['pc'] for r in row['RAM_writes']]==[0x48472,0x48476]
        selected.append((dict(family='native-detailed',index=index,fixture=case),ram,regs,expected,row['result']))
    assert {hex(pc):{hex(n):c for n,c in sorted(branches[pc].items())} for pc in BRANCHES}==native['branches']
    assert all(len(branches[pc])==2 for pc in BRANCHES)
    reference_path=root/'artifacts/stage_counter_bcd/verification.json';reference=json.loads(reference_path.read_bytes())
    assert reference['source']==source and reference['cases']==512 and reference['unicorn_mismatches']==0 and reference['musashi_mismatches']==301
    assert reference['unicorn_provenance']==native['oracle']
    assert reference['reference_revision']=='39a01be528b0744302bf1dc9b3463fc22a3fc45f'
    ref_inputs={str(reference_path.relative_to(root)):sha(reference_path.read_bytes())}
    for name,data in reference['reference_files'].items():
        path=root/'artifacts/dependencies/flamewing-bcd'/name;assert sha(path.read_bytes())==data['sha256'];ref_inputs[str(path.relative_to(root))]=data['sha256']
    path=root/'artifacts/dependencies/flamewing-bcd/data/bcd-table.bin'
    assert len(path.read_bytes())==reference['table_size'] and sha(path.read_bytes())==reference['table_sha256'];ref_inputs[str(path.relative_to(root))]=reference['table_sha256']
    assert reference['tool_sha256']==sha((root/'tools/check_stage_counter_bcd.py').read_bytes())
    diagnostic_folder=root/'artifacts/stage_counter/musashi'
    preserved_path=diagnostic_folder/'preservation.json';preserved=json.loads(preserved_path.read_bytes())
    old_path=diagnostic_folder/'observation.json';old_raw=old_path.read_bytes();old=json.loads(old_raw)
    assert sha(old_raw)==preserved['original_report_sha256']
    artifacts[str(preserved_path.relative_to(root))]=sha(preserved_path.read_bytes());artifacts[str(old_path.relative_to(root))]=sha(old_raw)
    for name,item in preserved['snapshots'].items():
        path=diagnostic_folder/item['snapshot'];assert sha(path.read_bytes())==item['sha256']==item['original_sha256']==old['inputs'][name]
        artifacts[str(path.relative_to(root))]=item['sha256']
    old_records_path=diagnostic_folder/old['compact_records']['file'];old_records=old_records_path.read_bytes()
    assert sha(old_records)==old['compact_records']['sha256'] and len(old_records)==len(records)
    artifacts[str(old_records_path.relative_to(root))]=sha(old_records)
    for row in old['results']:
        for name,digest in row['files'].items():
            path=diagnostic_folder/name;assert sha(path.read_bytes())==digest;artifacts[str(path.relative_to(root))]=digest
    mismatch_count=sum(RECORD.unpack_from(records,i*99)[1:17]!=RECORD.unpack_from(old_records,i*99)[1:17] for i in range(65536))
    native['preserved_Musashi_diagnostic']=dict(report_sha256=sha(old_raw),records_sha256=sha(old_records),
        full_WORD_output_or_register_mismatches=mismatch_count,acceptance_oracle=False)
    assert len(selected)==621
    return native,raw,records_path,artifacts,ref_inputs,selected


def negatives(exe,folder,row,ram):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out=work/'input.bin',work/'output.bin';sentinel=b'preserved-counter-output';regs=row['incoming']
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
        for label,a5,patches in (
            ('flag-below-RAM',0xfa97c,()),('flag-above-RAM',0x10a97d,()),
            ('A5-max-no-host-wrap',0xffffffff,()),('A5-zero',0,()),
            ('first-status-late',0x10824a,((0x10824a+0x5683,16),)),
            ('second-status-late',0x108249,((0x108249+0x5683,16),(0x10ffff,1))),
            ('low-counter-late',0xfa97d,((0x100000,16),(0x102733,1),(0x102734,0))),
            ('high-counter-late',0xfa981,((0x100004,16),(0x102737,1),(0x102738,0)))):
            payload=bytearray(ram)
            for address,value in patches:
                assert BASE<=address<BASE+65536;payload[address-BASE]=value
            reject(label,state=dict(regs,a5=a5),payload=bytes(payload))
        fresh=work/'fresh-output'
        reject('invalid-RAM-does-not-leave-new-output',payload=b'',destination=fresh);assert not fresh.exists()
        reject('invalid-register-does-not-leave-new-output',state=dict(regs,d0='-1'),destination=fresh);assert not fresh.exists()
        reject('invalid-span-does-not-leave-new-output',state=dict(regs,a5=0xffffffff),destination=fresh);assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded)
        case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            alias=work/'INPUT.BIN';assert os.path.samefile(inp,alias)
            reject('case-insensitive-input-output-alias',destination=alias);case_alias['input_preserved']=True
    return rows,case_alias



def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/stage_counter/execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True);exe=root/'build/execute_stage_counter'
    names=('tools/verify_stage_counter.py','build/execute_stage_counter','engine/tools/execute_stage_counter.cpp',
        'engine/src/stage_counter.cpp','engine/include/ms5/stage_counter.h','engine/tests/stage_counter_sweep.cpp',
        'engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,records_path,artifacts,reference_inputs,selected=audit(root,program,source)
    profiles=[]
    for index in range(3):
        p=folder/('profile-%d.bin'%index);p.write_bytes(RAM_PROFILES[index]);profiles.append(p)
    batch=folder/'sweep_test'
    command=['c++','-O2','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(root/'engine/include'),
        str(root/'engine/src/stage_counter.cpp'),str(root/'engine/tests/stage_counter_sweep.cpp'),'-o',str(batch)]
    compiled=subprocess.run(command,capture_output=True,text=True,timeout=30);assert not compiled.returncode,compiled.stderr
    assert not compiled.stdout and not compiled.stderr
    batch_run=subprocess.run([str(batch),str(records_path)]+list(map(str,profiles)),capture_output=True,text=True,timeout=30)
    assert not batch_run.returncode,(batch_run.stdout,batch_run.stderr)
    batch_result=json.loads(batch_run.stdout);assert batch_result==dict(cases=65536,full_RAM_15_registers_equal=True)
    for p in profiles+[batch]:artifacts[str(p.relative_to(root))]=sha(p.read_bytes())
    inp,out=folder/'input.bin',folder/'cpp.bin';rows=[]
    for label,ram,regs,expected,result in selected:
        inp.write_bytes(ram);out.write_bytes(b'previous-output')
        process=invoke(exe,regs,inp,out);assert not process.returncode,(label,process.stderr)
        parsed=json.loads(process.stdout)
        assert set(parsed)==set(KEYS) and all(type(v) is int for v in parsed.values())
        assert parsed==result and inp.read_bytes()==ram and out.read_bytes()==expected,label
        rows.append(dict(case=label,result=parsed,ram_sha256=sha(expected)))
    fresh=folder/'fresh-output.bin';fresh.unlink(missing_ok=True)
    label,ram,regs,expected,result=selected[-1];inp.write_bytes(ram)
    process=invoke(exe,regs,inp,fresh)
    assert not process.returncode and json.loads(process.stdout)==result and inp.read_bytes()==ram and fresh.read_bytes()==expected
    rejected,case_alias=negatives(exe,folder,dict(incoming=regs),ram)
    for name,digest in {**inputs,**native['inputs'],**artifacts,**reference_inputs}.items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and provenance(root,'unicorn')==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],
        native_artifacts=artifacts,reference_inputs=reference_inputs,native_observation_sha256=sha(raw),
        API_exhaustive_cases=65536,CLI_cases=len(rows),native_detailed_cases=109,branches=native['branches'],
        preserved_Musashi_diagnostic=native['preserved_Musashi_diagnostic'],
        negative_cases=rejected,case_alias_regression=case_alias,fresh_output_creation_native_equal=True,
        batch=dict(command=command,binary_sha256=sha(batch.read_bytes()),result=batch_result),
        full_RAM_15_registers_equal=True,source_and_inputs_unchanged=True,source_program_modified=False,in_call_SR_read=False,
        results=rows,scope='Immutable original4843c through RTS in pinnedUnicorn. Exhaustive65,536 rawWORD native fullRAM/15regs versus actualC++API;621 actualCLI cases include every highBYTE with low0/2 plus109 gate/status/oddA5/boundary fixtures. Expected RAM uses observed native writes, no duplicated BCD formula. Pinned third-party hardware-tested source0 SBCD reference512 agrees withUnicorn and differs fromMusashi301; no local physicalmeasurement claim. HistoricalMusashi report retained separately as diagnostic. No CCR/N/V/cycles, physicalRAMmirror, scheduling or gameplay equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(API_cases=65536,CLI_cases=len(rows),negative_cases=len(rejected),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()

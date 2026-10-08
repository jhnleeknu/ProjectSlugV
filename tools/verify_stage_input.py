"""FullRAM/13-register CLI comparison and stage-input CLI failure preservation."""
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

from disassemble_program import load_verified_program
from observe_stage_input import (BASE, KEYS, SOURCE_SHA256, build_cases, fixture,
    oracle_provenance, provenance, sha)


def invoke(exe,entry,regs,inp,out,resources=()):
    return subprocess.run([str(exe),str(entry)]+list(map(str,regs))+
        [str(inp),str(out)]+list(map(str,resources)),capture_output=True,text=True)


def container(payload,cpu=0x49ab0,**changes):
    fields=dict(version=1,kind=1,cpu=cpu,rom=cpu,size=len(payload),
        crc=zlib.crc32(payload),reserved=0)
    fields.update(changes)
    return struct.pack('<4s7I',b'MS5D',*(fields[k] for k in
        ('version','kind','cpu','rom','size','crc','reserved')))+payload


def negative_checks(root):
    exe = root/'build/step_stage_input'
    case = build_cases()[0]
    ram,regs = fixture(case)
    raw = bytes.fromhex('10204080')
    rows = []
    with tempfile.TemporaryDirectory(dir=root/'artifacts/stage_input') as directory:
        work = Path(directory)
        inp,out,res,other = [work/n for n in ('in.bin','out.bin','one.ms5d','two.ms5d')]
        def reject(label,entry=0x49ab4,values=None,resources=(),input_bytes=None):
            body = bytes(ram) if input_bytes is None else input_bytes
            inp.write_bytes(body);out.write_bytes(b'existing-output-must-survive')
            preserved = out.read_bytes()
            result = invoke(exe,entry,regs if values is None else values,inp,out,resources)
            assert result.returncode != 0 and not result.stdout, (label,result.stdout,result.stderr)
            assert out.read_bytes() == preserved and inp.read_bytes() == body,label
            rows.append(dict(failure=label,input_output_preserved=True,error=result.stderr.strip(),native_executed=False))
        res.write_bytes(container(raw))
        for value in (0,0x49ab5,-1,'0x','4294967296',' 0x49ab4'):
            reject('invalid-entry-'+str(value),entry=value,resources=[res])
        for index,value in ((0,-1),(1,'0x'),(2,'4294967296'),(8,' 1'),(12,'1x')):
            bad=regs.copy();bad[index]=value
            reject('invalid-register-'+str(index),values=bad,resources=[res])
        for size in (0,65535,65537):
            reject('RAM-size-'+str(size),input_bytes=bytes(size),resources=[res])
        reject('missing-default-fixed-window')
        reject('missing-resource-file',resources=[work/'missing.ms5d'])
        for packed,label in ((b'bad','header-truncated'),(container(raw)[:-1],'payload-truncated'),
            (container(raw)+b'x','trailing-payload'),(container(raw,version=2),'version'),
            (container(raw,kind=2),'banked-kind'),(container(raw,reserved=1),'reserved'),
            (container(raw,rom=0x49ab2),'CPU-ROM-mismatch'),
            (container(raw,cpu=0x100000),'nonfixed-mapping'),
            (container(raw,crc=0),'CRC')):
            res.write_bytes(packed);reject('resource-'+label,resources=[res])
        res.write_bytes(container(raw));other.write_bytes(container(raw))
        reject('overlap-complete-fixed-windows',resources=[res,other])
        other.write_bytes(container(raw[2:],cpu=0x49ab2))
        reject('overlap-partial-fixed-windows',resources=[res,other])
        res.write_bytes(container(raw[:3]))
        reject('partial-fixed-mask-late-byte',resources=[res])
        res.write_bytes(container(raw))
        for address,label in ((0x10fffd,'RAM-end-late-mask-byte'),(0x110000,'missing-mask-address'),
                              (0xffffffff,'mask-address-overflow')):
            bad=regs.copy();bad[12]=address
            reject(label,values=bad,resources=[res])
        for entry,address,label in ((0x49afe,0x106001,'odd-previous-WORD'),
            (0x49afe,0xffffffff,'previous-address-addition-overflow'),
            (0x49bb4,0x106001,'odd-consume-WORD'),
            (0x49bb4,0x49aac,'consume-read-fixed-then-reject-write'),
            (0x49bb4,0x10fffc,'consume-outside-RAM')):
            bad=regs.copy();bad[9]=address
            reject(label,entry=entry,values=bad,resources=[res])
        for label in ('same-path','hardlink','symlink'):
            inp.write_bytes(ram)
            dest=inp if label=='same-path' else work/label
            if label=='hardlink':os.link(inp,dest)
            if label=='symlink':dest.symlink_to(inp)
            result=invoke(exe,0x49ab4,regs,inp,dest,[res])
            assert result.returncode and inp.read_bytes()==ram and dest.read_bytes()==ram,label
            rows.append(dict(failure='input-output-'+label,input_output_preserved=True,native_executed=False))
        reject('resource-input-path-alias',resources=[inp])
        reject('resource-output-path-alias',resources=[out])
        out.write_bytes(container(raw));inp.write_bytes(ram)
        alias=work/'resource-output-hardlink.ms5d';os.link(out,alias)
        before=out.read_bytes()
        result=invoke(exe,0x49ab4,regs,inp,out,[alias])
        assert result.returncode and out.read_bytes()==before and inp.read_bytes()==ram
        rows.append(dict(failure='resource-output-hardlink',input_output_preserved=True,native_executed=False))
    return rows


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'artifacts/stage_input'
    program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    inputs,oracle=provenance(root),oracle_provenance(root.resolve())
    path=folder/'observation.json';native_bytes=path.read_bytes();native=json.loads(native_bytes)
    cases=build_cases()
    assert native['source']==source and native['inputs']==inputs and native['oracle']==oracle
    assert native['cases']==native['completed_cases']==len(native['results'])==len(cases)
    assert native['failure'] is None and not native['program_code_modified']
    negatives=negative_checks(root)
    exe=root/'build/step_stage_input';resource=root/'extracted/runtime/stage_input/default_masks.ms5d'
    rows=[];previous={};resumes=0
    with tempfile.TemporaryDirectory(dir=folder) as directory:
        work=Path(directory);inp,out=work/'in.bin',work/'out.bin'
        for index,(case,expected) in enumerate(zip(cases,native['results'])):
            assert expected['case_index']==index and expected['fixture']==case and expected['returned']
            prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
            ram,regs=fixture(case) if prior is None else (bytearray(prior[0]),list(prior[1]))
            resumes+=prior is not None
            assert sha(ram)==expected['input_ram_sha256'] and dict(zip(KEYS,regs))==expected['incoming']
            inp.write_bytes(ram)
            result=invoke(exe,hex(case['entry']),regs,inp,out,[resource])
            assert result.returncode==0,(index,case,result.stderr)
            actual=json.loads(result.stdout)
            original=(folder/expected['ram_file']).read_bytes()
            assert sha(original)==expected['ram_sha256']
            assert out.read_bytes()==original and actual==expected['result'],(index,case,actual,expected['result'])
            assert inp.read_bytes()==ram
            if 'sequence'in case:
                previous[case['sequence']]=(out.read_bytes(),[actual[k] for k in KEYS])
            rows.append(dict(case_index=index,entry=case['entry'],family=case['family'],
                full_RAM_13_registers_equal=True,ram_sha256=sha(original)))
    assert provenance(root)==inputs and oracle_provenance(root.resolve())==oracle
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    assert sha(path.read_bytes())==sha(native_bytes)
    report=dict(source=source,oracle=oracle,inputs=inputs,native_observation_sha256=sha(native_bytes),
        cases=len(cases),negative_cases=len(negatives),negative_results=negatives,
        counts_by_entry=dict(sorted(collections.Counter(c['entry'] for c in cases).items())),
        full_RAM_13_registers_equal=True,actual_output_chain_resumes=resumes,
        resumed_host_writes=0,CCR_exposed=False,results=rows,
        scope='Original Musashi uninterrupted helper outputs compared with actual stage-input CLI files and13 registers. '
              'Controlled liveRAM fixture masks, unchanged originalROM, no flags patched or callee substituted. '
              'Two actual CLI-output chains carry fullRAM/13regs without subsequent host writes. '
              'Malformed/partial/overlap/alias/address failures preserve existing output and input bytes; no native invalid-memory behavior equivalence claimed. '
              'Native49bb4 write-order evidence is retained in observation; CLI comparison checks final state only. No entire49b0c or callback/cycle/reachability claim.')
    destination=folder/'verification.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),negative_cases=len(negatives),actual_output_chain_resumes=resumes,
        full_RAM_13_registers_equal=True,sha256=sha(destination.read_bytes()))))


if __name__=='__main__':
    main()

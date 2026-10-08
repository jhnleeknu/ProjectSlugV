"""Verify reached3c WORD callbacks and actual14/03 RTS against immutable native runs.

No builds or native fixture generation. Native stages are replayed before CLI comparison;
continuations use only the previous actual C++ output plus recorded host writes.
"""
import argparse
import collections
import importlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

import observe_animation_rts_callback as rts
import verify_animation_execution as ordinary
import verify_animation_sound_execution as sound
import pack_animation_word_callback as word_packer
from disassemble_program import load_verified_program

RTS_SHA = 'b6064ba9908ac25b3d137cadf2dc3914e8df539edee104671b05c5760d8488dd'
WORD_SHA = '22e757ea1e727cfed50eaf3ad593b0cf6d2d9115c0beadf3a864220531c3495d'
WORD_TOOL_SHA = '5f2809db28ce29b91e49ba65be25e331d2152c5edea99ea424cd7fbefb2397ee'
KEYS = tuple(rts.KEYS)
KNOWN = (0x3679e,0x2b3e8,0x2b3fa,0x47672)


def digest(path):
    return rts.sha(Path(path).read_bytes())


def record(root,path,hashes):
    hashes[str(path.relative_to(root))] = digest(path)


def audit_source(root,folder,native,program,source,hashes):
    assert native['source']==source
    assert native['entry_pc']==0x49fc6
    assert native['original_program_modified'] is False and native['in_call_SR_read'] is False
    assert native['Cpp_comparison_performed'] is False and native['failure'] is None
    for name,value in native['inputs'].items():
        assert digest(root/name)==value,name
        hashes[name]=value
    static=json.loads((folder/'source.json').read_text())
    assert static['source']==source
    for row in static.get('data_ranges',[]):
        assert row['cpu_address']==row['rom_offset']
        assert rts.sha(program[row['rom_offset']:row['rom_offset']+row['size']])==row['sha256']
    branches=set()
    for start,end in static['ranges']:
        cursor=start
        for row in static['instructions']:
            if start<=row['cpu_address']<end:
                assert row['cpu_address']==row['rom_offset']==cursor
                assert bytes.fromhex(row['raw'])==program[cursor:cursor+row['size']]
                cursor+=row['size']
                if row['mnemonic'].startswith('b') and not row['mnemonic'].startswith(('bra','bsr','btst','bclr')):
                    branches.add(row['cpu_address'])
        assert cursor==end,(hex(cursor),hex(end))
    record(root,folder/'source.json',hashes)
    return branches


def audit_files(root,folder,phase,info,before,output,ports,trace,hashes):
    assert all(phase[key]==value for key,value in info.items()),phase['phase']
    assert before==(folder/phase['input_ram_file']).read_bytes()
    assert output==(folder/phase['ram_file']).read_bytes()
    assert ports==(folder/phase['ports_file']).read_bytes()
    assert trace==json.loads((folder/phase['trace_file']).read_text())
    assert phase['port_count']==len(ports)//9 and len(ports)%9==0
    assert set(phase['files'])=={phase[k] for k in ('input_ram_file','ram_file','ports_file','trace_file')}
    for name,value in phase['files'].items():
        assert digest(folder/name)==value,name
        record(root,folder/name,hashes)


def audit_rts(root,program,source):
    folder=root/'artifacts/animation_rts_callback_native'
    path=folder/'observation.json';assert digest(path)==RTS_SHA
    native=json.loads(path.read_text());hashes={};record(root,path,hashes)
    branches=audit_source(root,folder,native,program,source,hashes)
    assert native['oracle']==rts.oracle_provenance()
    cases=rts.cases(program);assert len(cases)==native['cases']==len(native['results'])
    observer=rts.Observer(program,branches);count=0;ports_count=0
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case and len(row['phases'])==1
        ram,regs,details=rts.fixture(case,index,program)
        assert details==row['details']
        observer.prepare(ram,regs)
        info,before,output,ports,trace=observer.run()
        assert rts.check(case,details,info,trace)==row['phases'][0]['evidence']
        audit_files(root,folder,row['phases'][0],info,before,output,ports,trace,hashes)
        count+=1;ports_count+=len(ports)//9
    assert count==native['phases'] and ports_count==native['total_native_ports']
    referenced={n for row in native['results'] for phase in row['phases'] for n in phase['files']}
    assert {p.name for p in folder.glob('case_*')}==referenced
    return native,folder,hashes


def audit_word(root,program,source):
    assert digest(root/'tools/observe_animation_word_callback.py')==WORD_TOOL_SHA
    original=importlib.import_module('observe_animation_word_callback')
    folder=root/'artifacts/animation_word_callback_native';path=folder/'observation.json'
    assert WORD_SHA is not None and digest(path)==WORD_SHA,'WORD observer must be frozen first'
    native=json.loads(path.read_text());hashes={};record(root,path,hashes)
    branches=audit_source(root,folder,native,program,source,hashes)
    assert native['oracle']==original.oracle_provenance()
    cases=original.cases();assert len(cases)==len(native['results'])==native['cases']
    observer=original.Observer(program,branches);counts=collections.Counter()
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs,details=original.fixture(case,index,program);assert details==row['details']
        observer.prepare(ram,regs,case['external'])
        for position,phase in enumerate(row['phases']):
            if position:observer.mutate(phase['host_changes']);counts['resumes']+=1
            else:assert not phase['host_changes']
            info,before,output,ports,trace=observer.run()
            original.check_phase(case,details,info,trace,not position)
            assert original.callee_records(trace,details,before)==phase['callbacks']
            audit_files(root,folder,phase,info,before,output,ports,trace,hashes)
            counts['phases']+=1;counts['ports']+=len(ports)//9;counts['external_reads']+=info['external_reads']
    controls=original.unsupported_cases();assert len(controls)==len(native['unsupported_stops'])
    for j,(case,row) in enumerate(zip(controls,native['unsupported_stops'])):
        index=10000+j;assert row['case_index']==index and row['fixture']==case
        ram,regs,details=original.fixture(case,index,program);assert details==row['details']
        observer.prepare(ram,regs,0)
        info,before,output,ports,trace=observer.run(allow_unsupported=True)
        original.check_phase(case,details,info,trace,True)
        assert row['stop']==info['stopped_unsupported'] and row['stop_state']==info['stop_state']
        assert row['incoming']==info['incoming'] and row['result']==info['result']
        payloads=('_input.bin','_native.bin','_ports.bin','_trace.json')
        prefix='case_%04d_unsupported_stop'%index
        assert before==(folder/(prefix+payloads[0])).read_bytes()
        assert output==(folder/(prefix+payloads[1])).read_bytes()
        assert ports==(folder/(prefix+payloads[2])).read_bytes()
        assert trace==json.loads((folder/(prefix+payloads[3])).read_text())
        for name,value in row['files'].items():assert digest(folder/name)==value;record(root,folder/name,hashes)
    assert counts['phases']==native['phases'] and counts['ports']==native['total_native_ports']
    assert counts['external_reads']==native['total_external_reads']
    for name,value in native['artifacts'].items():assert digest(folder/name)==value;record(root,folder/name,hashes)
    for index,control in enumerate(native['guard_controls']):
        case=original.cases()[0];ram,regs,details=original.fixture(case,20000+index,program)
        ram=bytearray(ram);original.put(ram,details['terminal'],2,control['terminal_word'])
        observer.prepare(bytes(ram),regs,0)
        try:
            observer.run()
        except AssertionError:
            assert observer.error==control['stopped']
        else:
            raise AssertionError('Native unsupported guard did not stop')
    assert len(native['artifacts'])==native['artifact_files']
    assert rts.sha(json.dumps(sorted(native['artifacts'].items())).encode())==native['artifact_manifest_sha256']
    assert {p.name for p in folder.glob('case_*')}==set(native['artifacts'])
    return native,folder,hashes


def expected(phase,trace,ports,incoming_bank=0x200000):
    result=sound.expected(phase,trace,ports,incoming_bank)
    assert result['external_reads']==phase['external_reads']
    return result


def changes(ram,writes,external):
    data=bytearray(ram)
    for row in writes:
        if row['address']==0xd00046:
            assert row['size']==1;external=row['value']
        else:
            at=row['address']-0x100000
            assert 0<=at and at+row['size']<=65536
            data[at:at+row['size']]=row['value'].to_bytes(row['size'],'big')
    return bytes(data),external


def compare(root,folder,native,native_folder,resources,exe,general_exe,label):
    rows=[];hashes={};counts=collections.Counter()
    for row in native['results']:
        state=sound.initial(row['phases'][0]['incoming']);native_bank=0x200000
        ram=(native_folder/row['phases'][0]['input_ram_file']).read_bytes()
        external=row['fixture'].get('external',0)
        for position,phase in enumerate(row['phases']):
            if position:
                ram,external=changes(ram,phase['host_changes'],external)
                counts['previous_actual_CPP_output_resumes']+=1
            else:assert not phase['host_changes']
            assert ram==(native_folder/phase['input_ram_file']).read_bytes()
            trace=json.loads((native_folder/phase['trace_file']).read_text());want=expected(phase,trace,(native_folder/phase['ports_file']).read_bytes(),native_bank)
            native_bank=want['current_bank_base']
            prefix='%s_%04d_%s'%(label,row['case_index'],phase['phase'])
            inp,out,ports,st=(folder/(prefix+s) for s in ('_input.bin','_cpp.bin','_ports.bin','_state.json'))
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            # Pending holds must not revisit either selector or any callback operand.
            held=position and phase['waiting'] and not phase['port_count'] and want['external_reads']==0
            rr=[] if held else resources
            p=sound.invoke(exe,state,external,inp,out,ports,rr)
            assert p.returncode==0,(label,row['case_index'],phase['phase'],p.stderr)
            actual=sound.parse(p.stdout);assert actual==want,(label,row['case_index'],phase['phase'],actual,want)
            assert out.read_bytes()==(native_folder/phase['ram_file']).read_bytes()
            assert ports.read_bytes()==(native_folder/phase['ports_file']).read_bytes() and inp.read_bytes()==ram
            st.write_text(p.stdout)
            for path in (inp,out,ports,st):record(root,path,hashes)
            if held:counts['resource_free_pending_invocations']+=1
            counts['sound_CLI_phases']+=1;counts['ports']+=len(ports.read_bytes())//9
            counts['external_reads']+=actual['external_reads']
            # Ordinary CLI supports reached non-sound targets, with its exact23-key schema.
            details=row.get('details',{})
            targets=[c['target'] for c in details['commands']] if 'commands' in details else [details['callback']]
            if 0x47672 not in targets and not position:
                oldstate={k:state[k] for k in ordinary.FIELDS}
                oldout=folder/(prefix+'_ordinary.bin');oldports=folder/(prefix+'_ordinary_ports.bin')
                op=ordinary.invoke(general_exe,oldstate,inp,oldout,oldports,resources)
                assert op.returncode==0,(label,row['case_index'],op.stderr)
                old=ordinary.parse(op.stdout);oldwant={k:want[k] for k in ordinary.OUTPUT}
                assert old==oldwant and oldout.read_bytes()==out.read_bytes() and oldports.read_bytes()==ports.read_bytes()
                oldst=folder/(prefix+'_ordinary_state.json');oldst.write_text(op.stdout)
                for path in (oldout,oldports,oldst):record(root,path,hashes)
                counts['ordinary_CLI_phases']+=1
            rows.append(dict(case_index=row['case_index'],phase=phase['phase'],result=actual,
                previous_actual_CPP_output_carried=bool(position),resources_omitted=bool(held),
                port_count=len(ports.read_bytes())//9,external_status_passed=external))
            state={k:actual[k] for k in sound.FIELDS if k!='external'};ram=out.read_bytes()
    return dict(counts),rows,hashes


def raw_window(cpu,payload):
    return struct.pack('<4s7I',b'MS5D',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload


def raw_script(cpu,payload):
    return struct.pack('<4s7I',b'MS5A',1,1,cpu,cpu,len(payload),zlib.crc32(payload),0)+payload


def padding_supplement(root,folder,exe,resources,native,native_folder):
    """CLI-only synthetic fixed-script twin, distinct from original-ROM comparisons."""
    row=next(r for r in native['results'] if r['fixture']['opcode']==0x3c)
    phase=row['phases'][0];ram=bytearray((native_folder/phase['input_ram_file']).read_bytes())
    state=sound.initial(phase['incoming']);script=bytes(ram[0x6000:0x600c]);cpu=0x60000
    at=state['a6']+0x26-0x100000;ram[at:at+4]=cpu.to_bytes(4,'big')
    paths=[]
    for name,address,data in (('padding_full.ms5a',cpu,script),('padding_head.ms5a',cpu,script[:1]),
            ('padding_tail.ms5a',cpu+2,script[2:])):
        path=folder/name;path.write_bytes(raw_script(address,data));paths.append(path)
    inp=folder/'padding_input.bin';inp.write_bytes(ram);results=[];hashes={}
    for label,rr in (('full',[paths[0]]+resources),('absent-padding',paths[1:]+resources)):
        out=folder/('padding_'+label+'_cpp.bin');ports=folder/('padding_'+label+'_ports.bin')
        p=sound.invoke(exe,state,0,inp,out,ports,rr);assert not p.returncode,(label,p.stderr)
        actual=sound.parse(p.stdout);assert actual['phase']==0 and actual['external_reads']==0
        st=folder/('padding_'+label+'_state.json');st.write_text(p.stdout)
        results.append((actual,out.read_bytes(),ports.read_bytes()))
        for path in (out,ports,st):record(root,path,hashes)
    assert results[0]==results[1] and inp.read_bytes()==ram
    for path in paths+[inp]:record(root,path,hashes)
    return dict(cases=2,results_equal=True,scope='CLI-only synthetic MS5A twin: absent padding byte is never fetched; no original fixed-script/reachability claim'),hashes


def negatives(root,folder,program,exe,general_exe,resources,rts_native,rts_folder):
    rows=[]
    first=next(r for r in rts_native['results'] if r['fixture']['opcode']==0x3c)
    phase=first['phases'][0];ram=(rts_folder/phase['input_ram_file']).read_bytes();state=sound.initial(phase['incoming'])
    details=first['details'];dataerror='fixed animation data read'
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/n for n in ('input','output','ports'));sentinel=b'preserve me'
        def reject(label,rr=resources,st=state,payload=ram,error=None,src=None,dst=None,old=False):
            inp.write_bytes(payload);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            src=inp if src is None else src;dst=(out,ports) if dst is None else dst
            watched={p:p.read_bytes() for p in [inp,out,ports,src]+list(dst)+list(rr) if p.exists() and p.is_file()}
            if old:p=ordinary.invoke(general_exe,{k:st[k] for k in ordinary.FIELDS},src,*dst,rr)
            else:p=sound.invoke(exe,st,0,src,*dst,rr)
            assert p.returncode!=0 and not p.stdout,(label,p.stderr,p.stdout)
            if error:assert error in p.stderr,(label,error,p.stderr)
            assert all(p.read_bytes()==b for p,b in watched.items()),label
            rows.append(dict(label=label,error=p.stderr.strip(),files_preserved=True,
                input_sha256=rts.sha(payload),state=st,
                resource_hashes=[dict(size=q.stat().st_size,sha256=digest(q)) for q in rr if q.is_file()]))
        def window(name,at,size):
            p=work/name;p.write_bytes(raw_window(at,program[at:at+size]));return p
        first_at=details['callback_table_address'];second_at=details['second_table_address']
        fw=window('first',first_at,4);sw=window('second',second_at,2)
        reject('missing-first',rr=[sw],error=dataerror);reject('missing-second',rr=[fw],error=dataerror)
        reject('partial-first',rr=[window('partial-first',first_at,3),sw],error=dataerror)
        reject('partial-second',rr=[fw,window('partial-second',second_at,1)],error=dataerror)
        reject('overlap-first',rr=[fw,window('overlap-first',first_at+2,2),sw],error=dataerror)
        reject('overlap-second',rr=[fw,sw,window('overlap-second',second_at,2)],error=dataerror)
        # Every missing-prefix slot has its ORIGINAL raw target; no synthetic target substitution.
        for address in range(0x42500,0x4276c,4):
            target=int.from_bytes(program[address:address+4],'big');assert target not in KNOWN
            payload=bytearray(ram);selector=((address-0x4a500)&65535)//4
            payload[0x6002:0x6004]=selector.to_bytes(2,'big')
            reject('unsupported-prefix-%05x'%address,payload=bytes(payload),error='unsupported animation callback')
        for selector in (0x2000,0x6000,0xa000,0xe000):
            payload=bytearray(ram);payload[0x6002:0x6004]=selector.to_bytes(2,'big')
            reject('prefix-absent-alias-%04x'%selector,payload=bytes(payload),rr=resources[:2]+resources[3:],error=dataerror)
            reject('prefix-consumed-unsupported-alias-%04x'%selector,payload=bytes(payload),error='unsupported animation callback')
        for selector in (0,1,2,4,0x3fff,0x7fff,0xffff):
            at=0x4a500+struct.unpack('>h',struct.pack('>H',(selector*4)&65535))[0]
            if int.from_bytes(program[at:at+4],'big') in KNOWN:continue
            payload=bytearray(ram);payload[0x6002:0x6004]=selector.to_bytes(2,'big')
            reject('unsupported-selector-%04x'%selector,payload=bytes(payload),error='unsupported animation callback')
        for field in sound.FIELDS:
            if field=='external':continue
            if field in ('waiting','callback_waiting'):bad=dict(state,**{field:True})
            elif field in ('phase','saved_a0','saved_a1','saved_bank','saved_list_end','callback_saved_a0','callback_sound_phase','callback_saved_low'):
                bad=dict(state,**{field:5 if field=='phase' else 1})
            else:continue
            reject('inactive-metadata-'+field,st=bad)
        for kind in ('copy','hardlink','symlink'):
            alias=work/('alias-'+kind)
            if kind=='copy':shutil.copyfile(resources[0],alias)
            elif kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('protected-'+kind,rr=[alias]+resources[1:] if kind=='copy' else resources,
                dst=(alias,ports))
        reject('same-output',dst=(out,out));reject('input-output',dst=(inp,ports))
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',src=fifo);reject('FIFO-output',dst=(fifo,ports));reject('FIFO-ports',dst=(out,fifo));reject('FIFO-resource',rr=[fifo])
        fresh=work/'fresh';reject('new-placeholder-cleanup',dst=(fresh,fifo));assert not fresh.exists()
    return rows


def word_negatives(root,folder,program,exe,general_exe,resources,native,native_folder):
    rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/n for n in ('input','output','ports'));sentinel=b'preserved late outputs'
        def reject(label,ram,state,rr,external=0,old=False,error=None):
            inp.write_bytes(ram);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in [inp,out,ports]+list(rr)}
            if old:p=ordinary.invoke(general_exe,{k:state[k] for k in ordinary.FIELDS},inp,out,ports,rr)
            else:p=sound.invoke(exe,state,external,inp,out,ports,rr)
            assert p.returncode and not p.stdout,(label,p.stderr,p.stdout)
            if error:assert error in p.stderr,(label,error,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,error=p.stderr.strip(),files_preserved=True,
                input_sha256=rts.sha(ram),state=state,external_status=external,
                resource_hashes=[dict(size=q.stat().st_size,sha256=digest(q)) for q in rr],
                limitation='CLI file preservation; internal state/ports/readcount transaction covered by API units'))
        def narrow(name,at,size):
            path=work/name;path.write_bytes(raw_window(at,program[at:at+size]));return path
        original=importlib.import_module('observe_animation_word_callback')
        for row in native['unsupported_stops']:
            ram,regs,details=original.fixture(row['fixture'],row['case_index'],program)
            assert details==row['details']
            for old in (False,True):
                reject('native-unsupported-target-%d-%s'%(row['case_index'],'ordinary' if old else 'sound'),
                    ram,sound.initial(regs),resources,old=old,error='unsupported animation callback')
        # Actual native fixed/RAM operand paths, with both mandatory lookups intact.
        for row in native['results']:
            if len(row['details']['commands'])!=1:continue
            cmd=row['details']['commands'][0]
            if cmd['target'] not in (0x2b3e8,0x2b3fa):continue
            if not row['fixture']['family'].startswith('operand-index-fixed-6431a'):continue
            phase=row['phases'][0];ram=(native_folder/phase['input_ram_file']).read_bytes();state=sound.initial(phase['incoming'])
            fw=narrow('first',cmd['slot'],4);sw=narrow('second',cmd['field'],2)
            reject('missing-callee-operand-%d'%row['case_index'],ram,state,[fw,sw],error='fixed animation data read')
            trace=json.loads((native_folder/phase['trace_file']).read_text())
            rd=next(r for r in trace['reads'] if r['pc'] in (0x2b3f2,0x2b404))
            reject('partial-callee-operand-%d'%row['case_index'],ram,state,
                [fw,sw,narrow('operand-partial',rd['address'],3)],error='fixed animation data read')
        for row in native['results']:
            if not any(c['target']==0x47672 for c in row['details']['commands']):continue
            phase=row['phases'][0];ram=(native_folder/phase['input_ram_file']).read_bytes();state=sound.initial(phase['incoming'])
            reject('ordinary-rejects-sound-target-%d'%row['case_index'],ram,state,resources,old=True,error='requires external-input overload')
            if len(row['details']['commands'])==1:
                cmd=row['details']['commands'][0];fw=narrow('sound-first',cmd['slot'],4)
                reject('sound-mandatory-second-%d'%row['case_index'],ram,state,[fw],error='fixed animation data read')
        for row in native['results']:
            if not row['fixture']['wait']:continue
            held=next(p for p in row['phases'] if p['phase']=='hold');ready=row['phases'][-1]
            captured=folder/('word_%04d_%s_state.json'%(row['case_index'],held['phase']))
            pending=sound.parse(captured.read_text())
            pending={k:pending[k] for k in sound.FIELDS if k!='external'}
            held_ram=(folder/('word_%04d_%s_cpp.bin'%(row['case_index'],held['phase']))).read_bytes()
            reject('ordinary-rejects-phase2-%d'%row['case_index'],held_ram,pending,[],old=True)
            reject('phase2-canonical-A5-%d'%row['case_index'],held_ram,dict(pending,a5=0x108002),[],error='canonical A5')
            for field,value in (('waiting',True),('callback_waiting',False),('callback_sound_phase',0),('saved_list_end',1)):
                reject('phase2-invalid-%s-%d'%(field,row['case_index']),held_ram,dict(pending,**{field:value}),[])
            # Negative continuations also start from previous actual C++ output.
            previous=row['phases'][-2]
            last_pending=sound.parse((folder/('word_%04d_%s_state.json'%(row['case_index'],previous['phase']))).read_text())
            last_pending={k:last_pending[k] for k in sound.FIELDS if k!='external'}
            cpp_ram=(folder/('word_%04d_%s_cpp.bin'%(row['case_index'],previous['phase']))).read_bytes()
            ready_ram,external=changes(cpp_ram,ready['host_changes'],row['fixture']['external'])
            assert ready_ram==(native_folder/ready['input_ram_file']).read_bytes()
            final_trace=json.loads((native_folder/ready['trace_file']).read_text())
            assert any(w['pc']==0x3af0 for w in final_trace['ordered_writes'])
            assert any(w['pc']==0x4a278 for w in final_trace['ordered_writes'])
            reject('phase2-late-missing-callee-lookup-%d'%row['case_index'],ready_ram,last_pending,[],external,error='fixed')
            raw=next(r for r in final_trace['reads'] if r['pc']==0x476aa)
            one=narrow('late-lookup-one',raw['address'],2);two=narrow('late-lookup-two',raw['address'],2)
            reject('phase2-late-overlapping-callee-lookup-%d'%row['case_index'],ready_ram,last_pending,[one,two],external,error='fixed')
            for field in ('saved_a0','saved_a1'):
                for suffix,value in (('odd',0x106001),('outside',0x110000)):
                    reject('phase2-late-%s-%s-%d'%(field,suffix,row['case_index']),ready_ram,
                        dict(last_pending,**{field:value}),resources,external)
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rts-only',action='store_true',help='partial RTS comparison; never reports full WORD verification')
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if not args.rts_only:importlib.import_module('observe_animation_word_callback')
    folder=root/'artifacts/animation_word_callback_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/('rts_partial_verification.json' if args.rts_only else 'verification.json');report.unlink(missing_ok=True)
    program,source=load_verified_program(root);rom=root/source['path'];rom_before=(digest(rom),rom.stat().st_mtime_ns)
    packed,manifest=word_packer.build(root)
    for name,data in packed.items():
        assert (root/'extracted/runtime/animation_word_callback'/name).read_bytes()==data,name
    resources=[root/'extracted/runtime/animation_control/control_04276c.ms5d',
        root/'extracted/runtime/animation_control/operands_06431a.ms5d',
        root/'extracted/runtime/animation_word_callback/prefix_042500.ms5d']
    if not args.rts_only:
        resources += [root/'extracted/runtime/animation_word_callback'/n for n in ('operands_000000.ms5d','operands_0ffc00.ms5d')]
    for path in resources:
        magic,version,kind,cpu,offset,size,crc,reserved=struct.unpack_from('<4s7I',path.read_bytes())
        data=path.read_bytes()[32:]
        assert (magic,version,kind,reserved)==(b'MS5D',1,1,0) and cpu==offset and size==len(data)
        assert zlib.crc32(data)==crc and data==program[cpu:cpu+size]
    spans=sorted((struct.unpack_from('<4s7I',p.read_bytes())[3],
        struct.unpack_from('<4s7I',p.read_bytes())[3]+len(p.read_bytes())-32) for p in resources)
    assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:])),spans
    exe=root/'build/step_animation_sound_execution';general_exe=root/'build/step_animation_execution'
    names=['tools/verify_animation_word_callback.py','tools/verify_animation_execution.py','tools/verify_animation_sound_execution.py',
        'tools/pack_animation_word_callback.py','tools/pack_animation_control.py','tools/pack_object_sound_lookup.py',
        'extracted/runtime/animation_word_callback/manifest.json','extracted/runtime/animation_control/manifest.json',
        'extracted/runtime/object_sound_lookup/manifest.json','extracted/runtime/object_sound_lookup/lookup.ms5d',
        'docs/analysis/animation-word-callback-contract.md','Makefile']
    names += ['engine/src/'+n+'.cpp' for n in ('animation_execution','object_sound_lookup','sound_word_execution','sound_byte_execution','sprite_submit_execution','fixed_data_resource','animation_resource')]
    names += ['engine/include/ms5/'+n+'.h' for n in ('animation_execution','object_sound_lookup','sound_word_execution','sound_byte_execution','sprite_submit_execution','sprite_producer','scene_map_transfer','video_port','animation_resource','fixed_data_resource')]
    names += ['engine/tools/step_animation_execution.cpp','engine/tools/step_animation_sound_execution.cpp']
    # Include transitive local helper modules, even when imported only for
    # shared register constants/JSON helpers or oracle provenance.
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if root/'tools' in path.parents and path.suffix=='.py':names.append(str(path.relative_to(root)))
    names.extend(('tools/address_map.py','docs/analysis/animation-bank-state-contract.md'))
    names=sorted(set(names))
    inputs={n:digest(root/n) for n in names}
    for path in resources+[exe,general_exe,rom]:record(root,path,inputs)
    for path in (exe,general_exe):
        assert path.stat().st_mtime_ns>=max((root/n).stat().st_mtime_ns for n in names if n.startswith('engine/')),'stale CLI'
    native,native_folder,artifacts=audit_rts(root,program,source)
    counts,rows,hashes=compare(root,folder,native,native_folder,resources,exe,general_exe,'rts');artifacts.update(hashes)
    supplement,hashes=padding_supplement(root,folder,exe,resources,native,native_folder);artifacts.update(hashes)
    rejected=negatives(root,folder,program,exe,general_exe,resources,native,native_folder)
    if not args.rts_only:
        assert WORD_SHA is not None,'WORD observer not frozen; use --rts-only for explicitly partial verification'
        word,word_folder,hashes=audit_word(root,program,source);artifacts.update(hashes)
        word_counts,word_rows,hashes=compare(root,folder,word,word_folder,resources,exe,general_exe,'word');artifacts.update(hashes)
        rejected.extend(word_negatives(root,folder,program,exe,general_exe,resources,word,word_folder))
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert (digest(rom),rom.stat().st_mtime_ns)==rom_before
    assert rts.oracle_provenance()==native['oracle']
    result=dict(bank_expectation=ordinary.BANK_EXPECTATION,complete=False,scope='RTS only; WORD non-RTS comparison pending',source=source,oracle=native['oracle'],inputs=inputs,
        native_and_CPP_artifacts=artifacts,native_observation_sha256=RTS_SHA,cases=native['cases'],
        counts=counts,results=rows,negative_cases=rejected,padding_supplement=supplement,ROM_unchanged=True,
        successful_resource_windows=[dict(cpu_start=a,end_exclusive=b) for a,b in spans],
        resources_passed_to_successful_runs=[str(p.relative_to(root)) for p in resources],
        limits='Static raw target equality is not reachability. CLI rejection proves file preservation, not internal API rollback. No fullCCR/timing/physicalCPU/natural-game claim.')
    if not args.rts_only:
        result.update(complete=True,scope='Actual3c WORD targets2b3e8/2b3fa/47672/3679e and14/03 RTS; all saved native stages reexecuted before full RAM/15R/state/carry/ports/readcount CLI comparison',
            word_native_observation_sha256=WORD_SHA,word_cases=word['cases'],word_counts=word_counts,word_results=word_rows,
            original_successful_phases_reexecuted=native['phases']+word['phases'],
            original_unsupported_prefix_stops_reexecuted=len(word['unsupported_stops']),
            original_excluded_odd_targets=word['excluded'],
            total_successful_sound_CLI_phases=counts['sound_CLI_phases']+word_counts['sound_CLI_phases'],
            total_successful_ordinary_CLI_phases=counts['ordinary_CLI_phases']+word_counts['ordinary_CLI_phases'])
        result['limits']+=' Fixed vector operands compare the canonical cartridge-ROM view, including addresses below80; BIOS/cart vector selection and natural boot are not modeled.'
        reached=collections.defaultdict(set)
        for row in word['results']:
            for phase in row['phases']:
                trace=json.loads((word_folder/phase['trace_file']).read_text())
                for read in trace['reads']:
                    if read['pc'] in (0x2b3f2,0x2b404) and read['kind']=='fixed':
                        reached[read['pc']].add((read['address'],read['size']))
        result['actual_fixed_callee_operand_read_spans']={hex(pc):[dict(address=a,size=n) for a,n in sorted(spans)] for pc,spans in sorted(reached.items())}
    report.write_text(json.dumps(result,indent=2)+'\n')
    summary=dict(complete=result['complete'],RTS_cases=result['cases'],RTS_counts=counts,negative_cases=len(rejected),sha256=digest(report))
    if not args.rts_only:summary.update(WORD_cases=word['cases'],WORD_counts=word_counts)
    print(json.dumps(summary))


if __name__=='__main__':main()

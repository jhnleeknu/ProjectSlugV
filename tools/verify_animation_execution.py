"""Actual full-state animation CLI versus immutable original traces and live RAM scripts."""
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import struct
from address_map import pvc_bank_update
import tempfile
from observe_activation_animation_scripts import (Observer,cases,fixture,load_verified_program,
    oracle_provenance,KEYS,BASE,SOURCE_SHA256)

NATIVE_SHA='18d25c677ab35698a7662142ce730422c67abcb2df58e7eea8592e141d5e39e6'
FIELDS=tuple(KEYS)+('phase','saved_a0','saved_a1','saved_bank','waiting','saved_list_end','current_bank_base')
OUTPUT=set(FIELDS)|{'carry'}
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(path):return sha(path.read_bytes())
BANK_EXPECTATION = 'current_bank_base derived from pinned PVC pair formula and original ordered ports over independently tracked incoming bank; never RAM shadow or C++ result'
def bank_from_ports(incoming_bank, ports):
    assert type(incoming_bank) is int and 0<=incoming_bank<=0xffffffff
    assert len(ports)%18==0, 'animation PVC writes must be complete ordered pairs'
    bank=incoming_bank;ff8=0
    for at in range(0,len(ports),18):
        size,address,value=struct.unpack_from('>BII',ports,at)
        second=struct.unpack_from('>BII',ports,at+9)
        assert size==2 and address==0x2ffff2 and value<=65535
        assert second==(2,0x2ffff0,0)
        # The first write already invokes get_bank_base and masks stored ff9.
        # Its transient bank is not the completed pair's selected bank.
        unused,ff8,ff9=pvc_bank_update(ff8,value)
        bank,ff8,ff9=pvc_bank_update(0,ff9)
    return bank

def bank_before_phase(phases, target, folder, incoming_bank=0x200000):
    bank=incoming_bank
    for phase in phases:
        if phase is target:return bank
        bank=bank_from_ports(bank,(folder/phase['ports_file']).read_bytes())
    raise AssertionError('phase does not belong to original chain')

def initial(regs,current_bank_base=0x200000):return dict(regs,phase=0,saved_a0=0,saved_a1=0,saved_bank=0,waiting=False,saved_list_end=0,current_bank_base=current_bank_base)
def expected(info,ports,incoming_bank=0x200000):
    pending=info['pending']
    return dict(info['result'],phase=int(info['waiting']),waiting=info['waiting'],carry=info['carry'],
        saved_a0=pending.get('saved_a0',0),saved_a1=pending.get('saved_a1',0),saved_bank=pending.get('saved_bank',0),saved_list_end=0,current_bank_base=bank_from_ports(incoming_bank,ports))
def apply_changes(ram,changes):
    data=bytearray(ram)
    for change in changes:
        at=change['address']-BASE;size=change['size'];assert 0<=at and at+size<=65536
        data[at:at+size]=change['value'].to_bytes(size,'big')
    return bytes(data)
def invoke(exe,state,inp,out,ports,resources):
    args=[str(int(state[k])) if type(state[k]) is bool else str(state[k]) for k in FIELDS]
    return subprocess.run([str(exe)]+args+list(map(str,(inp,out,ports)))+list(map(str,resources)),capture_output=True,text=True,timeout=5)
def parse(text):
    def unique(pairs):
        result={}
        for k,v in pairs:assert k not in result;result[k]=v
        return result
    r=json.loads(text,object_pairs_hook=unique)
    assert type(r) is dict and set(r)==OUTPUT and type(r['waiting']) is bool
    assert all(type(v) is int and 0<=v<=0xffffffff for k,v in r.items() if k not in ('waiting','carry'))
    assert r['phase'] in (0,1,3) and r['saved_bank']<=65535 and r['waiting']==(r['phase'] in (1,3))
    assert r['saved_list_end']==0 if r['phase']!=3 else True
    if r['phase']==0:assert all(r[k]==0 for k in ('saved_a0','saved_a1','saved_bank'))
    assert r['carry'] is None if r['waiting'] else type(r['carry']) is bool
    return r

def audit(root,program,source):
    folder=root/'artifacts/activation_animation_scripts';path=folder/'observation.json'
    native=json.loads(path.read_text());assert digest(path)==NATIVE_SHA
    assert native['source']==source and native['oracle']==oracle_provenance()
    assert not native['original_program_modified'] and not native['in_call_SR_read'] and native['failure'] is None
    hashes={str(path.relative_to(root)):digest(path)}
    for name,value in native['inputs'].items():assert digest(root/name)==value;hashes[name]=value
    static=json.loads((folder/'source.json').read_text());branches=set()
    for start,end in static['ranges']:
        cursor=start
        for row in static['instructions']:
            if start<=row['cpu_address']<end:
                assert row['cpu_address']==row['rom_offset']==cursor
                assert bytes.fromhex(row['raw'])==program[cursor:cursor+row['size']];cursor+=row['size']
                if row['mnemonic'].startswith('b') and not row['mnemonic'].startswith(('bra','bsr','btst','bclr')):branches.add(row['cpu_address'])
        assert cursor==end
    for script in static['scripts']:
        raw=program[script['rom_offset']:script['rom_offset']+script['size']]
        assert raw.hex()==script['raw'] and sha(raw)==script['sha256']
    observer=Observer(program,branches);phase_count=0;ports_total=0
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        assert row['case_index']==index and row['fixture']==case
        ram,regs=fixture(case,index);observer.prepare(ram,regs)
        for position,phase in enumerate(row['phases']):
            if position:observer.mutate(phase['host_changes'])
            else:assert not phase['host_changes']
            info,before,output,ports=observer.run();trace=info.pop('trace')
            assert all(phase[k]==value for k,value in info.items()),(index,phase['phase'])
            assert before==(folder/phase['input_ram_file']).read_bytes() and output==(folder/phase['ram_file']).read_bytes()
            assert ports==(folder/phase['ports_file']).read_bytes() and trace==json.loads((folder/phase['trace_file']).read_text())
            for name,value in phase['files'].items():
                p=folder/name;assert digest(p)==value;hashes[str(p.relative_to(root))]=value
            phase_count+=1;ports_total+=len(ports)//9
    assert len(native['results'])==len(cases())==native['cases']==90
    assert phase_count==native['phases']==98 and ports_total==native['total_native_ports']==3280
    return native,hashes,branches

def live_ram_supplements(root,folder,program,branches,exe):
    rows=[];hashes={};observer=Observer(program,branches)
    samples=[]
    for timer in (0,0x8000):samples.append(('duration-zero-'+hex(timer),bytes.fromhex('0000'),timer,0,0))
    for control in (0,1,2,3,0x10,0x40,0x50,0xa0,0xf0):
        samples.append(('live-draw-control-'+hex(control),bytes([4,control,0xfe,0x81])+bytes.fromhex('0006c80028'),0,0,0))
    samples.extend([
        ('palette-counter-selected',bytes.fromhex('0400fe810006c80028'),0,0,0),
        ('sentinel-skip',bytes.fromhex('04ff807f007ff80028'),0,0,0),
        ('flash-skip',bytes.fromhex('04ff807f0006c80028'),0,8,1),
        ('entry-clear-live-script',bytes.fromhex('280128'),0,0,0)])
    inp,out,ports=(folder/name for name in ('extra-input.bin','extra-cpp.bin','extra-ports.bin'))
    for index,(label,script,timer,flash,flash_phase) in enumerate(samples):
        case=dict(cases()[0],timer=timer,flash_flag=flash,flash_phase=flash_phase,counter=2 if label=='palette-counter-selected' else 0)
        ram,regs=fixture(case,index);ram=bytearray(ram);base=0x10d742 if label=='entry-clear-live-script' else 0x106000
        ram[base-BASE:base-BASE+len(script)]=script;ram[0x2026:0x202a]=base.to_bytes(4,'big');ram=bytes(ram)
        observer.prepare(ram,regs);info,before,native_ram,native_ports=observer.run();assert not info['waiting'] and before==ram
        inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
        p=invoke(exe,initial(regs),inp,out,ports,[]);assert not p.returncode,(label,p.stderr)
        actual=parse(p.stdout);assert actual==expected(info,native_ports) and out.read_bytes()==native_ram and ports.read_bytes()==native_ports and inp.read_bytes()==ram,label
        if label=='entry-clear-live-script':
            assert info['trace']['opcodes'][0]==dict(address=base,value=0)
            assert any(e['address']==base and e['pc']==0x49fee for e in info['trace']['ordered_writes'])
        files={}
        for name,data in (('input',ram),('native',native_ram),('cpp',out.read_bytes()),('ports',native_ports),('trace',(json.dumps(info,indent=2)+'\n').encode())):
            path=folder/('extra-%02d-%s.bin'%(index,name));path.write_bytes(data);rel=str(path.relative_to(root));hashes[rel]=digest(path);files[name]=rel
        rows.append(dict(label=label,result=actual,files=files,script_address=base,script_hex=script.hex(),resource_files=[]))
    return rows,hashes

def negatives(root,folder,exe,resources,native):
    ram,regs=fixture(cases()[0],0);state=initial(regs);rows=[]
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/x for x in ('input','output','ports'));sentinel=b'preserved-output'
        def reject(label,st=state,payload=ram,rr=None,src=None,outputs=None,command=None):
            inp.write_bytes(payload);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            source=inp if src is None else src;dest=(out,ports) if outputs is None else outputs;rr=resources if rr is None else rr
            watched={p:p.read_bytes() for p in [inp,out,ports,source]+list(dest)+list(rr) if p.exists() and p.is_file()}
            p=invoke(exe,st,source,*dest,rr) if command is None else subprocess.run(command,capture_output=True,text=True,timeout=5)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,files_preserved=True,error=p.stderr.strip()))
        for key in FIELDS:
            for bad in ('-1','4294967296','0x','1x',''):reject('parser-'+key+'-'+repr(bad),st=dict(state,**{key:bad}))
        for key,bad in (('phase',4),('saved_bank',65536),('waiting',2)):reject('range-'+key,st=dict(state,**{key:bad}))
        reject('old-overload-rejects-sound-phase2',st=dict(state,phase=2))
        for patch in ({'phase':1},{'waiting':True},{'saved_a0':1},{'saved_a1':1},{'saved_bank':1},{'saved_list_end':1}):reject('inconsistent-state-'+str(patch),st=dict(state,**patch))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),payload=bytes(size))
        for a6 in (0,0xffffffff,0x102001,0x10ffda):reject('object-span-'+hex(a6),st=dict(state,a6=a6))
        for a5 in (0,0xffffffff,0x108001):reject('bank-span-'+hex(a5),st=dict(state,a5=a5))
        reject('missing-script',rr=[])
        for opcode in (0x0c,0x10,0x14,0x18,0x40,0x44,0xff):
            data=bytearray(ram);data[0x2026:0x202a]=(0x106000).to_bytes(4,'big');data[0x6000]=opcode
            reject(('opcode-without-data-' if opcode in (0x0c,0x10,0x14,0x18) else 'unsupported-opcode-')+hex(opcode),payload=bytes(data),rr=[])
        # A jump loop must fail the command budget transactionally.
        data=bytearray(ram);data[0x2026:0x202a]=(0x106000).to_bytes(4,'big');data[0x6000:0x6006]=bytes.fromhex('080000106000')
        reject('live-jump-command-budget',payload=bytes(data),rr=[])
        data=bytearray(ram);data[0x9152:0x9156]=bytes(4);reject('late-callback',payload=bytes(data))
        pending=next(row for row in native['results'] if row['fixture']['pending'])['phases'][0]
        pending_ram=(root/'artifacts/activation_animation_scripts'/pending['ram_file']).read_bytes();pending_state=expected(pending,(root/'artifacts/activation_animation_scripts'/pending['ports_file']).read_bytes());pending_state.pop('carry')
        reject('pending-noncanonical-A5',st=dict(pending_state,a5=0x108002),payload=pending_ram,rr=[])
        ready=bytearray(pending_ram);ready[0x8d34:0x8d36]=(pending_state['d4']&65535).to_bytes(2,'big')
        reject('late-resume-missing-next-script',st=pending_state,payload=bytes(ready),rr=[])
        for at in (0,4,8,12,16,20,24,28,32):
            data=bytearray(resources[0].read_bytes());data[at]^=1;bad=work/('bad-resource-'+str(at));bad.write_bytes(data)
            reject('bad-resource-'+str(at),rr=[bad])
        reject('missing-args',command=[str(exe)]);reject('missing-input',src=work/'missing')
        reject('input-directory',src=work);reject('output-directory',outputs=(work,ports));reject('ports-directory',outputs=(out,work))
        reject('same-input-output',outputs=(inp,ports));reject('same-input-ports',outputs=(out,inp));reject('same-outputs',outputs=(out,out))
        reject('output-script-alias',outputs=(resources[0],ports));reject('ports-script-alias',outputs=(out,resources[0]))
        for kind in ('hardlink','symlink'):
            alias=work/kind
            if kind=='hardlink':os.link(inp,alias)
            else:alias.symlink_to(inp)
            reject('input-alias-'+kind,outputs=(alias,ports))
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',src=fifo);reject('FIFO-output',outputs=(fifo,ports));reject('FIFO-ports',outputs=(out,fifo));reject('FIFO-script',rr=[fifo])
        fresh=work/'fresh';reject('second-reservation-cleans-new-first',outputs=(fresh,fifo));assert not fresh.exists()
        folded=work/'INPUT'
        if folded.exists() and os.path.samefile(inp,folded):reject('case-alias-input',outputs=(folded,ports))
    return rows

def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/animation_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,artifacts,branches=audit(root,program,source)
    from pack_activation_animation import build
    packed,manifest=build(root);runtime=root/'extracted/runtime/activation_animation'
    for name,data in packed.items():assert (runtime/name).read_bytes()==data
    resources=[runtime/'animation_048980.ms5a',runtime/'animation_0489c2.ms5a'];exe=root/'build/step_animation_execution'
    names=['tools/verify_animation_execution.py','tools/pack_activation_animation.py','tools/inspect_activation_animation_scripts.py',
        'engine/src/animation_execution.cpp','engine/include/ms5/animation_execution.h','engine/tools/step_animation_execution.cpp',
        'engine/src/object_sound_lookup.cpp','engine/include/ms5/object_sound_lookup.h','engine/src/sound_word_execution.cpp','engine/include/ms5/sound_word_execution.h','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_byte_execution.h','engine/src/sprite_submit_execution.cpp','engine/include/ms5/sprite_submit_execution.h','engine/include/ms5/sprite_producer.h',
        'engine/include/ms5/scene_map_transfer.h','engine/include/ms5/video_port.h','engine/include/ms5/fixed_data_resource.h',
        'engine/src/animation_resource.cpp','engine/src/fixed_data_resource.cpp','engine/include/ms5/animation_resource.h','Makefile','build/step_animation_execution',
        'docs/analysis/animation-execution-initial-contract.md','docs/analysis/animation-draw-full-contract.md']
    names.extend(str((runtime/name).relative_to(root)) for name in packed)
    names.extend(('tools/address_map.py','docs/analysis/animation-bank-state-contract.md'))
    inputs={name:digest(root/name) for name in names};inp,out,ports=(folder/x for x in ('input.bin','cpp.bin','cpp.ports.bin'));rows=[];resumes=0
    for index,(case,row) in enumerate(zip(cases(),native['results'])):
        ram,regs=fixture(case,index);state=initial(regs);native_bank=0x200000
        for position,phase in enumerate(row['phases']):
            if position:ram=apply_changes(ram,phase['host_changes']);resumes+=1
            assert ram==(root/'artifacts/activation_animation_scripts'/phase['input_ram_file']).read_bytes()
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            rr=[] if case['script']==0 or phase['phase']=='hold' else resources
            p=invoke(exe,state,inp,out,ports,rr);assert not p.returncode,(index,phase['phase'],p.stderr)
            actual=parse(p.stdout);output=out.read_bytes();written=ports.read_bytes()
            want=expected(phase,(root/'artifacts/activation_animation_scripts'/phase['ports_file']).read_bytes(),native_bank)
            assert actual==want,(index,phase['phase'],actual,want)
            native_bank=want['current_bank_base']
            assert output==(root/'artifacts/activation_animation_scripts'/phase['ram_file']).read_bytes()
            assert written==(root/'artifacts/activation_animation_scripts'/phase['ports_file']).read_bytes() and inp.read_bytes()==ram
            files={}
            for name,data in (('ram',output),('ports',written)):
                path=folder/('cpp_%03d_%s_%s.bin'%(index,phase['phase'],name));path.write_bytes(data);rel=str(path.relative_to(root));artifacts[rel]=digest(path);files[name]=rel
            rows.append(dict(case_index=index,phase=phase['phase'],result=actual,files=files,host_changes=phase['host_changes'],previous_actual_CPP_output_carried=bool(position),port_count=len(written)//9))
            state=dict(actual);state.pop('carry');ram=output
    assert len(rows)==98 and resumes==8
    extra,extra_hashes=live_ram_supplements(root,folder,program,branches,exe);artifacts.update(extra_hashes)
    rejected=negatives(root,folder,exe,resources,native)
    for name,value in {**inputs,**artifacts}.items():assert digest(root/name)==value,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle']
    result=dict(bank_expectation=BANK_EXPECTATION,source=source,oracle=native['oracle'],inputs=inputs,native_and_CPP_artifacts=artifacts,
        cases=90,phases=98,previous_actual_CPP_output_resumes=resumes,primary_ordered_ports=sum(r['port_count'] for r in rows),
        results=rows,live_RAM_supplements=extra,negative_cases=rejected,full_RAM_15_registers_pending_carry_ports_equal=True,
        scope='RealMS5A scripts48980/489c2 with98originalreexecutedphases and8resumes usingonlypreviousactualCPPoutputs pluslistedhostwrites. '
        'Additional liveRAMdata scripts execute originalROM code unchanged and coverduration0/sentinel/controlpalette/liveentryclear. '
        'Checkederrors not nativeTRAPcompletion. This regression covers00/04/08/28; new0c/14 paths are verified separately. '
        'No physicalPVC/bankeddata/arbitrarycallback/naturalIRQ/scheduler/wholegame equivalence claim.')
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=90,phases=98,resumes=resumes,live_RAM_cases=len(extra),negative_cases=len(rejected),sha256=digest(report))))

if __name__=='__main__':main()

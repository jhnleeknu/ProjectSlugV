"""Full HUD original128 and same-CPU sound waits versus actual CLI."""
import argparse
import collections
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from observe_stage_hud_counter import (BASE,STACK,STACK_START,RETURN,KEYS,REGS,ENTRY,
    SOURCE_SHA256,sha,build_cases,fixture,load_verified_program,oracle_provenance)
from verify_object_reset import make_cpu

WAIT=0x3aea
META=('phase','saved_d0','sound_phase','sound_saved_low','waiting')


def inactive():return dict(phase=0,saved_d0=0,sound_phase=0,sound_saved_low=0,waiting=False)
def put(ram,at,value,size=2):ram[at:at+size]=value.to_bytes(size,'big')


def audit(root,program,source):
    folder=root/'artifacts/stage_hud_counter';path=folder/'observation.json';raw=path.read_bytes();native=json.loads(raw)
    assert sha(raw)=='b87af2a6a5a5e2506072e241b8c003aa9ff889cd6acd430880a23c06d17d95d5'
    assert native['source']==source and native['oracle']==oracle_provenance()
    assert native['cases']==native['completed_cases']==len(native['results'])==128
    assert native['total_native_ports']==1112 and native['external_read_count']==0
    assert native['full_RAM_15_registers_ordered_ports_observed'] and not native['original_program_modified'] and not native['in_call_SR_read'] and not native['Cpp_comparison_performed']
    for name,digest in native['inputs'].items():assert sha((root/name).read_bytes())==digest,name
    static=json.loads((folder/'source.json').read_bytes());assert static['source']==source
    for row in static['instructions']:
        at=row['rom_offset'];assert bytes.fromhex(row['raw'])==program[at:at+row['size']]
    lookup=static['raw_lookup'];assert lookup['raw']==program[0x4e272:0x4e292].hex() and lookup['size']==32
    artifacts={str(path.relative_to(root)):sha(raw)};cases=build_cases();addresses=set()
    for index,(case,row) in enumerate(zip(cases,native['results'])):
        ram=fixture(case);assert row['case_index']==index and row['fixture']==case
        assert row['final_pc']==RETURN and row['final_a7']==STACK+4 and not row['external_reads']
        for key,digest in (('input_ram_file','input_ram_sha256'),('ram_file','ram_sha256'),('ports_file','ports_sha256'),('trace_file','trace_sha256')):
            p=folder/row[key];assert sha(p.read_bytes())==row[digest];artifacts[str(p.relative_to(root))]=row[digest]
        assert (folder/row['input_ram_file']).read_bytes()==ram
        trace=json.loads((folder/row['trace_file']).read_bytes());pcs=trace['pcs'];assert pcs[0]==ENTRY and pcs[-1]==RETURN and len(pcs)-1==row['instructions']
        replay=bytearray(ram);ports=[];writes=[];stack=[]
        for e in trace['writes']:
            a,n,v=e['address'],e['size'],e['value'];assert n in (1,2,4) and 0<=v<1<<(8*n) and e['pc'] in pcs
            if e['kind']=='ram':
                assert BASE<=a and a+n<=BASE+65536;replay[a-BASE:a-BASE+n]=v.to_bytes(n,'big');writes.append(e)
            elif e['kind']=='ports':assert a==0x3c0000;ports.append(struct.pack('>BII',n,a,v))
            else:assert e['kind']=='stack' and STACK_START<=a and a+n<=STACK;stack.append(e)
        assert bytes(replay)==(folder/row['ram_file']).read_bytes() and b''.join(ports)==(folder/row['ports_file']).read_bytes()
        assert len(ports)==row['port_count'] and writes==row['RAM_writes'] and len(stack)==row['stack_write_count']
        assert min([e['address'] for e in stack]+[STACK])==row['lowest_stack_write']
        assert trace['raw_lookup_reads']==row['raw_lookup_reads'] and trace['external_reads']==row['external_reads']
        for e in row['raw_lookup_reads']:
            a=e['address'];assert e['size']==2 and 0x4e272<=a<=0x4e290 and e['value']==int.from_bytes(program[a:a+2],'big');addresses.add(a)
        if not case['flag']:assert row['result']==case['incoming'] and bytes(replay)==ram and not ports
    assert sorted(addresses)==native['raw_lookup_read_addresses']==list(range(0x4e272,0x4e292,2))
    return native,raw,artifacts


class Native:
    def __init__(self,program):
        self.program=program;self.cpu=make_cpu(program);self.cpu.mem_map(0x300000,0x100000);self.cpu.mem_map(0xd00000,4096)
        self.baseline=self.cpu.context_save();self.events=[];self.pcs=[];self.lookup=[];self.external=[];self.visits=0;self.error=None
        def code(c,pc,size,user):
            self.pcs.append(pc)
            if pc==RETURN:c.emu_stop();return
            if pc==WAIT:
                head=int.from_bytes(c.mem_read(c.reg_read(m.UC_M68K_REG_A5)-0x328c,2),'big')
                if head==(c.reg_read(m.UC_M68K_REG_D1)&65535):
                    self.visits+=1
                    if self.visits==2:c.emu_stop()
                else:self.visits=0
            opcode=int.from_bytes(c.mem_read(pc,2),'big')
            if opcode==0x4afc or 0x4e40<=opcode<=0x4e4f:self.error=dict(kind='trap',pc=pc);c.emu_stop()
        def write(c,access,address,size,value,user):
            kind='ports' if address==0x3c0000 else 'ram' if BASE<=address and address+size<=BASE+65536 else 'stack' if STACK_START<=address and address+size<=STACK else None
            e=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=value&((1<<(8*size))-1),kind=kind);self.events.append(e)
            if kind is None:self.error=dict(kind='unexpected-write',event=e);c.emu_stop()
        def read(c,access,address,size,value,user):
            e=dict(pc=c.reg_read(m.UC_M68K_REG_PC),address=address,size=size,value=int.from_bytes(c.mem_read(address,size),'big'))
            if 0x4e272<=address and address+size<=0x4e292:self.lookup.append(e)
            if address==0xd00046:self.external.append(e)
            elif not(address+size<=BASE or BASE<=address and address+size<=BASE+65536 or STACK_START<=address and address+size<=STACK+4):self.error=dict(kind='unexpected-read',event=e);c.emu_stop()
        def invalid(c,access,address,size,value,user):self.error=dict(kind='invalid',address=address,size=size);return False
        def intr(c,number,user):self.error=dict(kind='exception',number=number,pc=c.reg_read(m.UC_M68K_REG_PC));c.emu_stop()
        for hook,callback in ((UC_HOOK_CODE,code),(UC_HOOK_MEM_WRITE,write),(UC_HOOK_MEM_READ,read),(UC_HOOK_MEM_INVALID,invalid),(UC_HOOK_INTR,intr)):self.cpu.hook_add(hook,callback)

    def run(self,ram,regs,meta,external=0):
        c=self.cpu
        if not meta['phase']:
            c.context_restore(self.baseline);c.mem_write(STACK_START,b'\x5a'*4100);c.mem_write(STACK,RETURN.to_bytes(4,'big'))
            self.stack_low=STACK
            c.reg_write(m.UC_M68K_REG_SR,0x2000);c.reg_write(m.UC_M68K_REG_A7,STACK)
            for key,reg in zip(KEYS,REGS):c.reg_write(reg,regs[key])
        else:
            assert c.reg_read(m.UC_M68K_REG_PC)==WAIT and all(c.reg_read(r)&0xffffffff==regs[k] for k,r in zip(KEYS,REGS))
        c.mem_write(BASE,bytes(ram));c.mem_write(0xd00046,bytes([external]))
        self.events.clear();self.pcs.clear();self.lookup.clear();self.external.clear();self.visits=0;self.error=None
        c.emu_start(WAIT if meta['phase'] else ENTRY,0xffffff,count=100000)
        pc=c.reg_read(m.UC_M68K_REG_PC);sp=c.reg_read(m.UC_M68K_REG_A7)
        assert self.error is None and pc in (WAIT,RETURN),(self.error,hex(pc))
        output=bytes(c.mem_read(BASE,65536));result={k:c.reg_read(r)&0xffffffff for k,r in zip(KEYS,REGS)};captured=inactive();stack_evidence={}
        if pc==WAIT:
            assert self.visits==2
            ret=int.from_bytes(c.mem_read(sp,4),'big');sound_phase={0x3c00:1,0x4e2ce:2}[ret]
            assert sp==(STACK-12 if sound_phase==1 else STACK-6)
            assert int.from_bytes(c.mem_read(STACK-6,4),'big')==0x4e2ce
            saved=int.from_bytes(c.mem_read(STACK-2,2),'big')
            low=c.mem_read(sp+4,1)[0] if sound_phase==1 else result['d0']&255
            captured=dict(phase=1,saved_d0=saved,sound_phase=sound_phase,sound_saved_low=low,waiting=True)
            stack_evidence=dict(a7=sp,top_return=ret,outer_return=0x4e2ce,outer_saved_word=saved,
                raw=c.mem_read(STACK-16,20).hex(),two_wait_visits=self.visits)
        else:assert sp==STACK+4
        assert bytes(c.mem_read(STACK,4))==RETURN.to_bytes(4,'big') and bytes(c.mem_read(0,BASE))==self.program[:BASE]
        self.stack_low=min([self.stack_low]+[e['address'] for e in self.events if e['kind']=='stack'])
        assert bytes(c.mem_read(STACK_START,self.stack_low-STACK_START))==b'\x5a'*(self.stack_low-STACK_START)
        replay=bytearray(ram);packed=[]
        for e in self.events:
            if e['kind']=='ram':replay[e['address']-BASE:e['address']-BASE+e['size']]=e['value'].to_bytes(e['size'],'big')
            if e['kind']=='ports':packed.append(struct.pack('>BII',e['size'],e['address'],e['value']))
        assert bytes(replay)==output
        result.update(captured,external_reads=len(self.external))
        return output,result,b''.join(packed),dict(pcs=self.pcs.copy(),writes=self.events.copy(),lookup_reads=self.lookup.copy(),external_reads=self.external.copy(),stack=stack_evidence,lowest_stack_write=self.stack_low,final_pc=pc,final_a7=sp)


def invoke(exe,regs,meta,external,inp,out,ports,resources):
    values=[regs[k] for k in KEYS]+[meta[k] for k in META]+[external]
    return subprocess.run([str(exe)]+[str(int(v)) if isinstance(v,bool) else str(v) for v in values]+
        list(map(str,(inp,out,ports)))+list(map(str,resources)),capture_output=True,text=True,timeout=3)


def run_additional(root,program,exe=None,resource=None):
    folder=root/'artifacts/stage_hud_counter_execution';folder.mkdir(parents=True,exist_ok=True)
    observer=Native(program);rows=[];inp,out,ports=(folder/name for name in ('extra-input.bin','extra-cpp.bin','extra-cpp.ports.bin'))
    def compare(label,ram,regs,meta,external=0,changes=()):
        output,result,packed,trace=observer.run(ram,regs,meta,external)
        index=len(rows);prefix='extra-%02d'%index
        payloads={prefix+'-input.bin':bytes(ram),prefix+'-native.bin':output,prefix+'-native.ports.bin':packed,prefix+'-trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
        for name,data in payloads.items():(folder/name).write_bytes(data)
        if exe:
            inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
            p=invoke(exe,regs,meta,external,inp,out,ports,[resource]);assert not p.returncode,(label,p.stderr)
            actual=json.loads(p.stdout);assert actual==result and inp.read_bytes()==bytes(ram) and out.read_bytes()==output and ports.read_bytes()==packed,(label,actual,result)
            output=out.read_bytes();result=actual
        rows.append(dict(label=label,incoming=dict(regs,**meta,external_status=external),host_changes=list(changes),result=result,port_count=len(packed)//9,
            files={name:sha(data) for name,data in payloads.items()},trace=trace))
        return bytearray(output),{k:result[k] for k in KEYS},{k:result[k] for k in META}
    base_case=next(c for c in build_cases() if c['word']==0x09ff and c['counter']==0 and c['reference']==1)
    def initial():
        case=json.loads(json.dumps(base_case));ram=bytearray(fixture(case));regs=case['incoming']
        for at,v in ((0x4d8a,0),(0x4d8c,6),(0x4d74,1),(0x4d76,0),(0x4d82,0x0455),(0x4d84,0x0566),(0x4d86,0x0677),(0x4d88,0x0788)):put(ram,at,v)
        return ram,regs
    for target in (1,2):
        ram,regs=initial();put(ram,0x4d74,target)
        ram,regs,meta=compare('sound-wait-%d-start'%target,ram,regs,inactive());assert meta['sound_phase']==target
        changes=[dict(address=BASE+0xdd1f,size=1,value=0),dict(address=BASE+0xdd20,size=1,value=0x80)]
        for w in changes:put(ram,w['address']-BASE,w['value'],w['size'])
        ram,regs,meta=compare('sound-wait-%d-hold-poison-HUD'%target,ram,regs,meta,255,changes);assert meta['sound_phase']==target
        assert rows[-1]['trace']['pcs'][0]==WAIT and ENTRY not in rows[-1]['trace']['pcs'] and not rows[-1]['trace']['external_reads']
        put(ram,0x4d74,0xffff)
        ram,regs,meta=compare('sound-wait-%d-release'%target,ram,regs,meta,255,[dict(address=BASE+0x4d74,size=2,value=65535)])
        assert meta==inactive() and ram[0xdd1f]==0 and ram[0xdd20]==31
        assert ENTRY not in rows[-1]['trace']['pcs'] and not rows[-1]['trace']['external_reads']
    ram,regs=initial();ram,regs,meta=compare('sequential-high-start',ram,regs,inactive());assert meta['sound_phase']==1
    put(ram,0x4d74,2);ram,regs,meta=compare('sequential-high-to-low',ram,regs,meta,0,[dict(address=BASE+0x4d74,size=2,value=2)]);assert meta['sound_phase']==2
    put(ram,0x4d74,0xffff);ram,regs,meta=compare('sequential-low-release',ram,regs,meta,0,[dict(address=BASE+0x4d74,size=2,value=65535)]);assert meta==inactive()
    for external in (0,1,255):
        ram=bytearray(fixture(json.loads(json.dumps(base_case))));regs=base_case['incoming']
        changes=[]
        for at,value in ((0x12,1),(0xfd82,1),(0xfe80,0),(0xfd8d,1)):
            put(ram,at,value,1);changes.append(dict(address=BASE+at,size=1,value=value))
        ram,regs,meta=compare('conditional-external-'+str(external),ram,regs,inactive(),external,changes)
        assert meta==inactive() and len(rows[-1]['trace']['external_reads'])==1
    # Every legal upper BYTE (00..99) reaches its actual two raw digit lookups;
    # non-BCD low nibbles a..f remain original code bytes read as WORD data.
    for upper in range(0x9a):
        case=json.loads(json.dumps(base_case));case['counter']=1
        low=(0,1,7,8,31,32,127,128,255)[upper%9]
        case['word']=(upper<<8)|low
        case['incoming']['d0']=(case['incoming']['d0']&0xffff0000)|case['word']
        ram=bytearray(fixture(case))
        ram,regs,meta=compare('all-legal-upper-byte-%02x'%upper,ram,case['incoming'],inactive())
        assert meta==inactive() and len(rows[-1]['trace']['lookup_reads'])==2
    for a5 in (0xff140,0xff141):
        case=json.loads(json.dumps(base_case));case['word']=0x0a00
        case['incoming']['d0']=(case['incoming']['d0']&0xffff0000)|0x0a00
        case['incoming']['a5']=a5;ram=bytearray(fixture(case))
        counter=a5+0x5d20;assert counter in (0x104e60,0x104e61)
        ram,regs,meta=compare('live-A5-palette-field-alias-'+hex(a5),ram,case['incoming'],inactive())
        assert meta==inactive() and regs['a5']==a5
        alias_writes=[e for e in rows[-1]['trace']['writes'] if e['kind']=='ram' and e['address']==counter]
        assert alias_writes[0]['pc']==0x4e2b2 and alias_writes[0]['value']==0
        if a5==0xff140:assert len(alias_writes)==1 and ram[0x4e61]==0x25
        else:assert [e['pc'] for e in alias_writes]==[0x4e2b2,0x8d2c] and ram[0x4e61]==0x80
    return rows


def negatives(exe,folder,resource,native,extra):
    rows=[]
    case=next(row['fixture'] for row in native['results'] if row['fixture']['word']==0x0a00 and row['fixture']['profile']==1)
    base=fixture(case);regs=case['incoming']
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        work=Path(temporary);inp,out,ports=(work/name for name in ('in.bin','out.bin','ports.bin'));sentinel=b'preserved-HUD-output'
        def reject(label,ram=base,state=regs,meta=None,external=0,resources=None,source=None,outputs=None,command=None):
            sources=[resource] if resources is None else resources;destinations=(out,ports) if outputs is None else outputs
            inp.write_bytes(ram);out.write_bytes(sentinel);ports.write_bytes(sentinel)
            watched={p:p.read_bytes() for p in (inp,out,ports)+tuple(sources)+tuple(destinations) if p.exists() and p.is_file()}
            p=subprocess.run(command,capture_output=True,text=True,timeout=3) if command else invoke(exe,state,inactive() if meta is None else meta,external,inp if source is None else source,*destinations,sources)
            assert p.returncode and not p.stdout,(label,p.stdout,p.stderr)
            assert all(p.read_bytes()==data for p,data in watched.items()),label
            rows.append(dict(label=label,input_resources_outputs_preserved=True,error=p.stderr.strip()))
        for size in (0,65535,65537):reject('RAM-size-'+str(size),ram=bytes(size))
        for key in KEYS:
            for bad in ('-1','4294967296','0x100000000','0x','1x',''):
                reject('register-parser-'+key,state=dict(regs,**{key:bad}))
        for key,maximum in zip(META,(1,65535,2,255,1)):
            for bad in ('-1',str(maximum+1),'0x','1x',''):
                reject('metadata-parser-'+key,meta=dict(inactive(),**{key:bad}))
        for bad in ('-1','256','0x','1x',''):reject('external-parser',external=bad)
        for update in (dict(saved_d0=1),dict(sound_phase=1),dict(sound_phase=2),dict(sound_saved_low=1),dict(waiting=True),
                dict(phase=1),dict(phase=1,sound_phase=1),dict(phase=1,sound_phase=2),dict(phase=1,waiting=True)):
            reject('inconsistent-continuation',meta=dict(inactive(),**update))
        for a5 in (0,0xffffffff,0x10a2e1):reject('fresh-A5-span',state=dict(regs,a5=a5))
        soundcase=next(r['fixture'] for r in native['results'] if r['fixture']['word']==0x09ff and r['fixture']['counter']==0 and r['fixture']['reference']==1)
        soundram=bytearray(fixture(soundcase));soundregs=soundcase['incoming']
        shifted=bytearray(soundram);shifted[0xdd20]=1;shifted[0xdd21]=0
        reject('noncanonical-A5-actual-sound-unsupported',ram=bytes(shifted),state=dict(soundregs,a5=0x108001))
        for at,value in ((0x4d8a,1),(0x4d8a,0x8000),(0x4d8c,1),(0x4d8c,8)):
            modified=bytearray(soundram);put(modified,at,value)
            reject('fresh-invalid-sound-index',ram=bytes(modified),state=soundregs)
        pending=extra[0];pendingram=(folder/next(name for name in pending['files'] if name.endswith('-native.bin'))).read_bytes()
        pendingregs={k:pending['result'][k] for k in KEYS};pendingmeta={k:pending['result'][k] for k in META}
        reject('pending-noncanonical-A5',ram=pendingram,state=dict(pendingregs,a5=0x108001),meta=pendingmeta)
        modified=bytearray(pendingram);put(modified,0x4d74,65535)
        reject('pending-byte-destination-outside-RAM',ram=bytes(modified),state=dict(pendingregs,a0=0x110000),meta=pendingmeta)
        reject('missing-lookup',resources=[])
        duplicate=work/'duplicate.ms5d';duplicate.write_bytes(resource.read_bytes());reject('duplicate-distinct-lookup',resources=[resource,duplicate])
        original=resource.read_bytes()
        for offset in (0,4,8,12,16,20,24,28,32):
            bad=bytearray(original);bad[offset]^=1;p=work/('bad-%d.ms5d'%offset);p.write_bytes(bad);reject('lookup-corruption-'+str(offset),resources=[p])
        def window(name,start,payload):
            path=work/name;path.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,start,start,len(payload),zlib.crc32(payload),0)+payload);return path
        for start in (0x4e272,0x4e273):
            partial=window('partial-%x'%start,start,b'\xc8');reject('partial-overlap-'+hex(start),resources=[resource,partial])
        first=window('first-digit-only',0x4e272,original[32:34])
        reject('late-second-lookup-after-first-draw',resources=[first])
        reject('missing-input',source=work/'absent-input');reject('input-directory',source=work)
        reject('missing-resource',resources=[work/'absent-resource']);reject('resource-directory',resources=[work])
        reject('RAM-output-directory',outputs=(work,ports));reject('port-output-directory',outputs=(out,work))
        reject('RAM-output-missing-parent',outputs=(work/'absent'/'out',ports));reject('port-output-missing-parent',outputs=(out,work/'absent'/'ports'))
        reject('input-RAM-output-alias',outputs=(inp,ports));reject('input-port-output-alias',outputs=(out,inp));reject('two-output-alias',outputs=(out,out))
        reject('resource-RAM-output-alias',outputs=(resource,ports));reject('resource-port-output-alias',outputs=(out,resource))
        for kind in ('hardlink','symlink'):
            for target,label in ((inp,'input'),(resource,'resource'),(out,'output')):
                alias=work/(label+'-'+kind)
                if kind=='hardlink':os.link(target,alias)
                else:alias.symlink_to(target)
                if label=='output':reject('output-pair-'+kind,outputs=(out,alias))
                else:
                    reject(label+'-RAM-output-'+kind,outputs=(alias,ports));reject(label+'-port-output-'+kind,outputs=(out,alias))
        reject('missing-arguments',command=[str(exe)])
        fifo=work/'fifo';os.mkfifo(fifo)
        reject('FIFO-input',source=fifo);reject('FIFO-resource',resources=[fifo]);reject('FIFO-RAM-output',outputs=(fifo,ports));reject('FIFO-port-output',outputs=(out,fifo))
        fresh=work/'fresh';reject('late-reservation-cleans-new-output',outputs=(fresh,fifo));assert not fresh.exists()
        probe=work/'CaseProbe';probe.write_bytes(b'probe');folded=work/'caseprobe'
        insensitive=folded.exists() and os.path.samefile(probe,folded);case_alias=dict(case_insensitive_filesystem=insensitive,applicable=insensitive)
        if insensitive:
            first,second=work/'NewOutput',work/'newoutput'
            reject('case-alias-new',outputs=(first,second));assert not first.exists() and not second.exists()
            first.write_bytes(b'');reject('case-alias-existing-empty',outputs=(first,second));assert first.read_bytes()==b''
            case_alias.update(new_placeholders_removed=True,existing_empty_preserved=True)
    return rows,case_alias


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    native,raw,artifacts=audit(root,program,source)
    if args.prepare:
        extra=run_additional(root,program)
        print(json.dumps(dict(native_cases=len(native['results']),native_sha256=sha(raw),additional=len(extra),pending=[r['trace']['stack'] for r in extra if r['trace']['stack']])))
        return
    folder=root/'artifacts/stage_hud_counter_execution';folder.mkdir(parents=True,exist_ok=True)
    report=folder/'verification.json';report.unlink(missing_ok=True)
    exe=root/'build/step_stage_hud_counter';resource=root/'extracted/runtime/stage_hud_counter/lookup.ms5d'
    names=('tools/verify_stage_hud_counter.py','tools/pack_stage_hud_counter.py','build/step_stage_hud_counter','engine/tools/step_stage_hud_counter.cpp',
        'engine/src/stage_hud_counter.cpp','engine/include/ms5/stage_hud_counter.h','engine/src/palette_blend_execution.cpp','engine/include/ms5/palette_blend_execution.h',
        'engine/src/palette_control.cpp','engine/include/ms5/palette_control.h','engine/src/stage_block_draw.cpp','engine/include/ms5/stage_block_draw.h',
        'engine/src/sound_word_execution.cpp','engine/include/ms5/sound_word_execution.h','engine/src/sound_byte_execution.cpp','engine/include/ms5/sound_byte_execution.h',
        'engine/include/ms5/scene_map_transfer.h','engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h',
        'engine/include/ms5/object_restart_execution.h','engine/include/ms5/video_port.h','Makefile',
        'extracted/runtime/stage_hud_counter/lookup.ms5d','extracted/runtime/stage_hud_counter/manifest.json')
    inputs={name:sha((root/name).read_bytes()) for name in names}
    payload=program[0x4e272:0x4e292]
    assert resource.read_bytes()==struct.pack('<4s7I',b'MS5D',1,1,0x4e272,0x4e272,32,zlib.crc32(payload),0)+payload
    inp,out,ports=(folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin'));native_folder=root/'artifacts/stage_hud_counter';rows=[]
    for row in native['results']:
        ram=(native_folder/row['input_ram_file']).read_bytes();inp.write_bytes(ram);out.write_bytes(b'old');ports.write_bytes(b'old')
        p=invoke(exe,row['fixture']['incoming'],inactive(),0,inp,out,ports,[resource]);assert not p.returncode,(row['case_index'],p.stderr)
        expected=dict(row['result'],**inactive(),external_reads=0);parsed=json.loads(p.stdout)
        assert parsed==expected and inp.read_bytes()==ram and out.read_bytes()==(native_folder/row['ram_file']).read_bytes() and ports.read_bytes()==(native_folder/row['ports_file']).read_bytes(),(row['case_index'],parsed,expected)
        rows.append(dict(case_index=row['case_index'],fixture=row['fixture'],result=parsed,ram_sha256=sha(out.read_bytes()),ports_sha256=sha(ports.read_bytes()),port_count=row['port_count']))
    extra=run_additional(root,program,exe,resource)
    rejected,case_alias=negatives(exe,folder,resource,native,extra)
    for row in extra:
        for name,digest in row['files'].items():artifacts[str((folder/name).relative_to(root))]=digest
    for name,digest in dict(inputs,**native['inputs'],**artifacts).items():assert sha((root/name).read_bytes())==digest,name
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256 and oracle_provenance()==native['oracle']
    report.write_text(json.dumps(dict(source=source,oracle=native['oracle'],inputs=inputs,native_inputs=native['inputs'],native_artifacts=artifacts,
        native_observation_sha256=sha(raw),cases=len(rows),additional_cases=len(extra),negative_cases=rejected,case_alias_regression=case_alias,
        total_ordered_ports=sum(r['port_count'] for r in rows)+sum(r['port_count'] for r in extra),
        full_RAM_15_registers_pending_ordered_ports_equal=True,source_and_inputs_unchanged=True,
        original_program_modified=False,in_call_SR_read=False,results=rows,additional=extra,
        scope='Immutable original4e286 throughRTS or actual3aea waiting,128 frozen cases plus separate sameCPU wait/external/all154legal-upper-byte and liveA5palette-field-alias observations versus actualCLI. Native stack/CCR retained on resumes; saved HUD WORD and sound phases derived from stack. Host consumer releases and poisoned prefix fields are explicit; no scheduler, physical mirror, CCR/cycle or rendered pixel equivalence claim.'),indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),additional=len(extra),negative_cases=len(rejected),sha256=sha(report.read_bytes()))))


if __name__=='__main__':main()

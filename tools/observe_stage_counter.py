"""Unpatched4843c throughRTS, including all65536 raw counter WORDs.

Default Unicorn is the acceptance oracle. Musashi is separately selectable
only as a known-divergent diagnostic for invalid BCD. Oracle outputs reside
in distinct subdirectories; preserved historical Musashi evidence is kept.

Compact records schema1: big-endian >HH15I32sHB (99 bytes): inputWORD,
outputWORD, D0..D7/A0..A6, full64KiB outputRAM SHA256, trace catalog ID,
actual CPU write count. The catalog retains exact PCs and ordered write
PC/address/size shapes; outputWORD supplies the two actual BYTE values.
All input RAM is reproducible from fixture(profile=inputWORD%3). The compact
rows therefore preserve every observed register, RAM hash and write value;
they do not replace native execution with a BCD algorithm.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct
import time
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
try:
    from .disassemble_program import load_verified_program,disassemble_range
    from .musashi_oracle import MusashiOracle
    from .observe_scene_motion_pair import oracle_provenance
    from .verify_stage_catalog import SOURCE_SHA256
    from .verify_object_reset import make_cpu
    from .observe_scene_frame_execution import oracle_provenance as unicorn_provenance
except ImportError:
    from disassemble_program import load_verified_program,disassemble_range
    from musashi_oracle import MusashiOracle
    from observe_scene_motion_pair import oracle_provenance
    from verify_stage_catalog import SOURCE_SHA256
    from verify_object_reset import make_cpu
    from observe_scene_frame_execution import oracle_provenance as unicorn_provenance

BASE,STACK,RETURN,ENTRY,END=0x100000,0x1feffc,0xff000,0x4843c,0x4847c
KEYS=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(7))
RECORD=struct.Struct('>HH15I32sHB')
READS={0x4843c:0x5683,0x48446:0x7db6,0x4844e:0x7db7,0x4845c:0x567f,0x48460:0x567e}
BRANCHES=(0x48442,0x48458,0x4846a)


class UnicornCPU:
    """Small read-only observer adapter; execute the original ROM directly."""
    def __init__(self,program):
        self.cpu=make_cpu(program);self.baseline=self.cpu.context_save()
        self.observer=None;self.writer=None;self.sentinel=RETURN;self.instructions=0;self.write_count=0;self.error=None
        def code(c,pc,size,user):
            if pc==self.sentinel:c.emu_stop();return
            self.instructions+=1
            try:
                if self.observer:self.observer(pc)
            except BaseException as exc:self.error=exc;c.emu_stop()
        def write(c,access,address,size,value,user):
            self.write_count+=1
            try:
                if self.writer:self.writer(c.reg_read(m.UC_M68K_REG_PC),address,size,value & ((1 << (size*8))-1))
            except BaseException as exc:self.error=exc;c.emu_stop()
        self.cpu.hook_add(UC_HOOK_CODE,code);self.cpu.hook_add(UC_HOOK_MEM_WRITE,write)
    def load(self,address,data):self.cpu.mem_write(address,bytes(data))
    def read(self,address,size):return bytes(self.cpu.mem_read(address,size))
    def reset(self):self.cpu.context_restore(self.baseline)
    def set_reg(self,name,value):self.cpu.reg_write(getattr(m,'UC_M68K_REG_'+name.upper()),value)
    def get_reg(self,name):return self.cpu.reg_read(getattr(m,'UC_M68K_REG_'+name.upper()))&0xffffffff
    def set_instruction_hook(self,callback):self.observer=callback
    def set_write_hook(self,callback):self.writer=callback
    def run(self,budget,sentinel):
        self.instructions=0;self.write_count=0;self.error=None;self.sentinel=sentinel
        self.cpu.emu_start(self.get_reg('pc'),0xffffff,count=budget)
        if self.error:raise RuntimeError('Original Unicorn observer rejected execution') from self.error
        pc=self.get_reg('pc')
        return dict(status='sentinel' if pc==sentinel else 'budget_exhausted',instructions=self.instructions,
            pc=pc,cpu_writes=self.write_count,fault_address=0)


def provenance(root,oracle):return unicorn_provenance() if oracle=='unicorn' else oracle_provenance(root)


def sha(data):return hashlib.sha256(data).hexdigest()


def build_cases():
    cases=[]
    words=(0,1,2,10,0x0100,0x9999,0xffff,0x1234)
    for profile in range(4):
        for flag in (0,1,16,255):
            for first,second in ((0,0),(1,0),(0,1),(1,1),(2,255)):
                cases.append(dict(word=words[len(cases)%len(words)],profile=profile,
                    a5=0x108000,flag=flag,player_status=[first,second]))
    for a5 in (0xfa982,0x108001,0x108002,0x108248):
        for word in (0,1,2,0x000a,0x0100,0x9999,0xffff):
            cases.append(dict(word=word,profile=len(cases)%4,a5=a5,flag=16,player_status=[1,0]))
    # Counter bytes can be outside RAM when the original gate bypasses them.
    cases.append(dict(word=0,profile=3,a5=0xfa97d,flag=0,player_status=[0,0]))
    return cases


RAM_PROFILES=tuple(hashlib.shake_256(b'stage-counter-'+bytes([i])).digest(65536) for i in range(4))


def fixture(case):
    a5=case['a5'];ram=bytearray(RAM_PROFILES[case['profile']])
    values=(0,0xffffffff,0x81231234,0xabcdffff);seed=values[case['profile']]
    regs={key:(seed+i*0x01010101)&0xffffffff for i,key in enumerate(KEYS)};regs['a5']=a5
    writes=[]
    for offset,value in ((0x5683,case['flag']),(0x7db6,case['player_status'][0]),(0x7db7,case['player_status'][1])):
        address=a5+offset;assert BASE<=address<BASE+65536
        ram[address-BASE]=value;writes.append(dict(address=address,size=1,value=value))
    for offset,value in ((0x567e,case['word']>>8),(0x567f,case['word']&255)):
        address=a5+offset
        if BASE<=address<BASE+65536:
            ram[address-BASE]=value;writes.append(dict(address=address,size=1,value=value))
        else:assert not case['flag']&16
    return bytes(ram),regs,writes


class Observer:
    def __init__(self,program,oracle='unicorn'):
        self.program=program;self.cpu=UnicornCPU(program) if oracle=='unicorn' else MusashiOracle()
        self.cpu.load(0,program[:BASE]);self.pcs=[];self.writes=[];self.steps=[]
        self.a5=0;self.record_steps=False
        def code(pc):
            assert ENTRY<=pc<END and pc%2==0,hex(pc)
            self.pcs.append(pc)
            if pc in READS:
                address=self.a5+READS[pc];assert BASE<=address<BASE+65536,(hex(pc),hex(address))
            if self.record_steps:self.steps.append(dict(pc=pc,registers={k:self.cpu.get_reg(k) for k in KEYS}))
        def write(pc,address,size,value):
            assert (pc,address,size) in ((0x48472,self.a5+0x567e,1),(0x48476,self.a5+0x567f,1)),(hex(pc),hex(address),size)
            assert BASE<=address<BASE+65536 and 0<=value<=255
            self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)

    def run(self,case,ram,regs,detailed=False):
        c=self.cpu;c.reset();c.load(BASE,ram);c.load(STACK-32,b'\x5a'*36);c.load(STACK,RETURN.to_bytes(4,'big'))
        c.set_reg('sr',0x2000);c.set_reg('a7',STACK)
        for k in KEYS:c.set_reg(k,regs[k])
        c.set_reg('pc',ENTRY);self.a5=regs['a5'];self.record_steps=detailed
        self.pcs.clear();self.writes.clear();self.steps.clear();status=c.run(64,RETURN)
        assert status['status']=='sentinel' and status['pc']==RETURN and not status['fault_address'],status
        assert c.get_reg('a7')==STACK+4 and c.read(STACK-32,36)==b'\x5a'*32+RETURN.to_bytes(4,'big')
        assert self.pcs[-1]==0x4847a and status['instructions']==len(self.pcs) and status['cpu_writes']==len(self.writes)
        output=c.read(BASE,65536);replay=bytearray(ram)
        for e in self.writes:replay[e['address']-BASE]=e['value']
        assert bytes(replay)==output
        result={k:c.get_reg(k) for k in KEYS}
        for k in KEYS:
            if k not in ('d0','d1','d2'):assert result[k]==regs[k]
        if not case['flag']&16:assert result==regs and output==ram and not self.writes
        if not any(v==1 for v in case['player_status']):assert output==ram and not self.writes
        if self.writes:assert [e['pc'] for e in self.writes]==[0x48472,0x48476]
        info=dict(status=status,final_pc=RETURN,final_a7=STACK+4,pcs=self.pcs.copy(),RAM_writes=self.writes.copy())
        if detailed:info['steps']=self.steps.copy()
        return output,result,info

    def guard_program(self):assert self.cpu.read(0,BASE)==self.program[:BASE]


def sweep_case(word):return dict(word=word,profile=word%3,a5=0x108000,flag=16,player_status=[1,0])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int)
    parser.add_argument('--oracle',choices=('unicorn','musashi'),default='unicorn');args=parser.parse_args()
    if args.limit is not None and not 1<=args.limit<=65536:parser.error('limit must be1..65536; diagnostic only')
    diagnostic=args.limit is not None;count=args.limit if diagnostic else 65536
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/stage_counter'/args.oracle;folder.mkdir(parents=True,exist_ok=True)
    names=('tools/observe_stage_counter.py','tools/disassemble_program.py','tools/musashi_oracle.py',
        'tools/observe_scene_motion_pair.py','tools/build_musashi_oracle.py','tools/native/musashi_oracle.c','tools/verify_stage_catalog.py',
        'tools/verify_object_reset.py','tools/observe_scene_frame_execution.py','docs/analysis/stage-counter-contract.md',
        'tools/check_stage_counter_bcd.py','artifacts/stage_counter_bcd/verification.json')
    reference=json.loads((root/'artifacts/stage_counter_bcd/verification.json').read_bytes())
    assert reference['cases']==512 and reference['unicorn_mismatches']==0 and reference['musashi_mismatches']==301
    references=tuple('artifacts/dependencies/flamewing-bcd/'+name for name in reference['reference_files'])+('artifacts/dependencies/flamewing-bcd/data/bcd-table.bin',)
    for name,metadata in reference['reference_files'].items():
        assert sha((root/'artifacts/dependencies/flamewing-bcd'/name).read_bytes())==metadata['sha256']
    assert sha((root/references[-1]).read_bytes())==reference['table_sha256']
    names=names+references
    inputs={name:sha((root/name).read_bytes()) for name in names}
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    oracle=provenance(root,args.oracle);instructions=disassemble_range(program,ENTRY,END-ENTRY,ENTRY)
    assert all(r['classification']=='candidate_instruction' for r in instructions)
    assert instructions[-1]['raw']=='4e75' and RECORD.size==99
    observer=Observer(program,args.oracle);observer.guard_program();catalog=[];catalog_ids={};branches=collections.defaultdict(collections.Counter);write_total=0;clamped=0
    record_name='diagnostic-%d.records.bin'%count if diagnostic else 'all_words.records.bin';record_path=folder/record_name;start=time.monotonic()
    with record_path.open('wb') as stream:
        for word in range(count):
            case=sweep_case(word);ram,regs,host=fixture(case);output,result,info=observer.run(case,ram,regs)
            shape=dict(pcs=info['pcs'],writes=[{k:e[k] for k in ('pc','address','size')} for e in info['RAM_writes']])
            encoded=json.dumps(shape,sort_keys=True);trace_id=catalog_ids.get(encoded)
            if trace_id is None:trace_id=len(catalog);catalog_ids[encoded]=trace_id;catalog.append(dict(id=trace_id,**shape))
            output_word=int.from_bytes(output[0xd67e:0xd680],'big')
            stream.write(RECORD.pack(word,output_word,*[result[k] for k in KEYS],hashlib.sha256(output).digest(),trace_id,len(info['RAM_writes'])))
            for pc,next_pc in zip(info['pcs'],info['pcs'][1:]):
                if pc in BRANCHES:branches[pc][next_pc]+=1
            write_total+=len(info['RAM_writes']);clamped+=int(0x4846e in info['pcs'])
            if word%256==255:observer.guard_program()
    observer.guard_program();record_digest=sha(record_path.read_bytes())
    # Independently replay compact rows into RAM using observed write shapes.
    with record_path.open('rb') as stream:
        for word in range(count):
            values=RECORD.unpack(stream.read(RECORD.size));input_word,output_word=values[:2];assert input_word==word
            ram,regs,host=fixture(sweep_case(word));replay=bytearray(ram);shape=catalog[values[-2]];assert values[-1]==len(shape['writes'])
            for e in shape['writes']:replay[e['address']-BASE]=output_word>>8 if e['address']==0x10d67e else output_word&255
            assert hashlib.sha256(replay).digest()==values[-3]
        assert not stream.read(1)
    details=[]
    for index,case in enumerate(build_cases()):
        ram,regs,host=fixture(case);output,result,info=observer.run(case,ram,regs,True);observer.guard_program()
        prefix=('diagnostic-' if diagnostic else '')+'case-%03d'%index
        files={prefix+'-input.bin':ram,prefix+'-native.bin':output}
        for name,data in files.items():(folder/name).write_bytes(data)
        details.append(dict(case_index=index,fixture=case,incoming=regs,host_writes=host,result=result,files={name:sha(data) for name,data in files.items()},**info))
        for pc,next_pc in zip(info['pcs'],info['pcs'][1:]):
            if pc in BRANCHES:branches[pc][next_pc]+=1
    assert inputs=={name:sha((root/name).read_bytes()) for name in names} and oracle==provenance(root,args.oracle)
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    if not diagnostic:assert count==65536 and all(len(branches[pc])==2 for pc in BRANCHES)
    report_name='diagnostic.json' if diagnostic else 'observation.json'
    report=dict(source=source,oracle=oracle,oracle_choice=args.oracle,acceptance_oracle=args.oracle=='unicorn',inputs=inputs,instructions=instructions,entry=ENTRY,return_instruction=0x4847a,
        diagnostic_only=diagnostic,full_WORD_domain_completed=not diagnostic,word_cases=count,detailed_cases=len(details),
        compact_records=dict(schema_version=1,file=record_name,sha256=record_digest,record_bytes=RECORD.size,count=count,
            byte_order='big',struct_format=RECORD.format,fields=['input_WORD','output_WORD']+list(KEYS)+['output_RAM_SHA256_bytes32','trace_id_u16','CPU_write_count_u8'],
            input_fixture='sweep_case(input_WORD), profile=input_WORD%3; fixture() supplies complete64KiBRAM and15regs',
            write_values='Trace catalog gives orderedPC/address/size; high counter BYTE is output_WORD>>8, low BYTE is output_WORD&255.'),
        trace_catalog=catalog,branches={hex(pc):{hex(n):c for n,c in sorted(branches[pc].items())} for pc in BRANCHES},
        branch_counts_scope='Full enabled WORD sweep plus separately listed detailed gate/status/A5 cases',
        sweep_RAM_write_count=write_total,sweep_clamp_branch_count=clamped,compact_RAM_write_replay_passed=True,
        full_RAM_15_registers_observed=True,program_code_modified=False,in_call_SR_read=False,SR_before_A7=True,
        oracle_limitations='Unicorn raw SBCD BYTE/C behavior matches the pinned third-party hardware-tested Flamewing reference for all512 source0/destination/X combinations; this is third-party evidence, not local hardware measurement. Musashi has known invalid-BCD mismatches and is diagnostic only. FinalCCR/N/V/cycles are outside scope.',
        Cpp_comparison_performed=False,results=details,elapsed_seconds=round(time.monotonic()-start,3),
        scope='Immutable original4843c throughRTS in selected pinnedM68000 oracle. Every raw16bit counter value, not decimal normalization; nativeSBCD. CPUwriteguard restricts exact counterBYTE writes and order; fullRAM write replay everycase, fixedROM guards every256sweepcases and each detailedcase. All15regs and actual branch PCs retained. Stack sentinel/guard native-only; no CCR/cycle/hardwaremirror/natural scheduler/gameplay claim.')
    path=folder/report_name;path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(diagnostic_only=diagnostic,word_cases=count,detailed_cases=len(details),records_sha256=record_digest,report_sha256=sha(path.read_bytes()),elapsed_seconds=report['elapsed_seconds'])))


if __name__=='__main__':main()

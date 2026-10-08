"""Observe immutable whole49fc6 calling the actual RTS at fixed CPU/ROM03679e.

No unsupported callback is stubbed. The shared CPU hook implementation is borrowed
with temporary, restored code ranges; new stack/register assertions are specific
only to the actual14/3c ->03679e call. Generated ROM-derived files stay ignored.
"""
import collections
from contextlib import contextmanager
import hashlib
import itertools
import json
from pathlib import Path
import struct
import observe_animation_control_commands as core
from disassemble_program import load_verified_program, disassemble_range
from observe_scene_frame_execution import oracle_provenance
from verify_stage_catalog import SOURCE_SHA256

BASE=core.BASE; STACK=core.STACK; RETURN=core.RETURN; KEYS=core.KEYS
ENTRY=0x49fc6; TARGET=0x3679e; SCRIPT=0x106000
RANGES=((ENTRY,0x4a0e4),(0x4a276,0x4a27e),(0x4a30c,0x4a382),(0x4a408,0x4a46c),(TARGET,TARGET+2))
BOUNDARIES=(ENTRY,0x4a30c,0x4a408,TARGET,0x4a354,0x4a376,0x4a37a,0x4a37c,0x4a37e,
            0x4a43e,0x4a460,0x4a464,0x4a466,0x4a468,0x4a276)
SECOND_SELECTORS=(0,1,0x7f,0xff,0x100,0x3fff,0x4000,0x4001,0x7fff,0x8000,0x8001,0xbfff,0xc000,0xfffe,0xffff)
OPERANDS=(0,0x7fff,0x8000,0xffff,0x12348000,0xffffffff)

def sha(data): return hashlib.sha256(data).hexdigest()
def signed_word(value): return (value&65535)-65536 if value&0x8000 else value&65535
def put(ram,address,size,value): core.put(ram,address,size,value)

def target_slots(program):
    return [a for a in range(0x42500,0x52500,4) if int.from_bytes(program[a:a+4],'big')==TARGET]

def second_inventory(program):
    rows=[]
    for raw in (0,0x7fff,0x8000,0xffff):
        matches=[s for s in range(0x8000) if int.from_bytes(program[0x4a76c+signed_word((s*2)&65535):0x4a76e+signed_word((s*2)&65535)],'big')==raw]
        rows.append(dict(raw_word=raw,found=bool(matches),first_selector=matches[0] if matches else None))
    return rows

def cases(program):
    selectors=list(SECOND_SELECTORS)
    for item in second_inventory(program):
        if item['found'] and item['first_selector'] not in selectors: selectors.append(item['first_selector'])
    rows=[]
    for address in target_slots(program):
        base=((address-0x4a500)&65535)//4
        for first,second,operand in itertools.product(tuple(base+0x4000*i for i in range(4)),selectors,OPERANDS):
            rows.append(dict(family='3c-actual-RTS-WORD-alias',opcode=0x3c,first_selector=first,second_selector=second,operand=operand))
        if 0<=address-0x4a500<=0x3fc:
            for operand in OPERANDS:
                rows.append(dict(family='14-actual-RTS-BYTE-selector',opcode=0x14,first_selector=(address-0x4a500)//4,second_selector=None,operand=operand))
    return rows

def fixture(case,index,program=None):
    if program is None: program,_=load_verified_program(Path(__file__).resolve().parents[1])
    ram=bytearray(hashlib.shake_256(('animation-rts-callback-%d'%index).encode()).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(KEYS)}
    regs.update(a5=0x108000,a6=0x102000)
    for address,size,value in ((0x102026,4,SCRIPT),(0x10202a,2,0),(0x10202c,2,0x100),(0x102017,1,0),(0x100010,2,0xbeef)):
        put(ram,address,size,value)
    put(ram,SCRIPT,1,case['opcode'])
    first=case['first_selector']; first_offset=(first*4)&65535
    if case['opcode']==0x3c:
        put(ram,SCRIPT+1,1,0xa5^(index&255));put(ram,SCRIPT+2,2,first);put(ram,SCRIPT+4,2,case['second_selector']);put(ram,SCRIPT+6,4,case['operand']);end=SCRIPT+10
        second_address=0x4a76c+signed_word(case['second_selector']*2&65535)
    else:
        put(ram,SCRIPT+1,1,first);put(ram,SCRIPT+2,4,case['operand']);end=SCRIPT+6;second_address=None
    put(ram,end,2,0)
    address=0x4a500+signed_word(first_offset)
    details=dict(callback_table_address=address,callback=int.from_bytes(program[address:address+4],'big'),
        second_table_address=second_address,second_word=None if second_address is None else int.from_bytes(program[second_address:second_address+2],'big'),
        outer_a0=regs['a6']+0x26,outer_a1=end,terminal=end,padding_address=SCRIPT+1 if case['opcode']==0x3c else None)
    assert details['callback']==TARGET
    return bytes(ram),regs,details

@contextmanager
def configured():
    old_ranges,old_boundaries=core.RANGES,core.BOUNDARIES
    core.RANGES,core.BOUNDARIES=RANGES,BOUNDARIES
    try: yield
    finally: core.RANGES,core.BOUNDARIES=old_ranges,old_boundaries

class Observer:
    def __init__(self,program,branches):
        with configured(): self.original=core.Observer(program,branches)
        self.input=None;self.incoming=None
    @property
    def error(self): return self.original.error
    def prepare(self,ram,regs): self.input=bytes(ram);self.incoming=dict(regs)
    def run(self):
        assert self.input is not None
        with configured(): output,ports,info,trace=self.original.run(self.input,self.incoming)
        info.update(incoming=dict(self.incoming),waiting=False,pending=None,external_reads=0)
        return info,self.input,output,ports,trace

def check(case,details,info,trace):
    bs=trace['boundaries']; call=next(b for b in bs if b['pc']==TARGET)
    return_pc=0x4a354 if case['opcode']==0x3c else 0x4a43e
    after=next(b for b in bs if b['pc']==return_pc)
    restored=next(b for b in bs if b['pc']==(0x4a37a if case['opcode']==0x3c else 0x4a464))
    stack=bytes.fromhex(call['stack_at_sp'])
    assert call['a7']==STACK-14 and int.from_bytes(stack[:4],'big')==return_pc
    assert int.from_bytes(stack[4:6],'big')==0
    assert int.from_bytes(stack[6:10],'big')==details['outer_a1']
    assert int.from_bytes(stack[10:14],'big')==details['outer_a0']
    assert after['registers']==call['registers'] and after['a7']==STACK-10
    r=call['registers']; assert r['a0']==case['operand'] and r['a1']==TARGET and r['d7']==TARGET
    expected_d0=case['operand'] if case['opcode']==0x3c else case['first_selector']*4
    assert r['d0']==expected_d0
    if case['opcode']==0x3c:
        assert r['d1']==(info['incoming']['d1']&0xffff0000)|details['second_word']
        assert not any(x['address']<=details['padding_address']<x['address']+x['size'] for x in trace['reads'])
    else: assert r['d1']==info['incoming']['d1']
    for key in ('d0','d7'):
        assert restored['registers'][key]==signed_word(r[key])&0xffffffff
    for pc in (TARGET,): assert trace['pcs'].count(pc)==1
    assert info['result']['a0']==details['outer_a0'] and info['result']['a1']==details['terminal']+2
    assert info['final_pc']==RETURN and info['final_a7']==STACK+4
    assert info['result']['d0']==signed_word(expected_d0)&0xffffffff
    assert all(x['pc']!=TARGET for x in trace['reads']+trace['ordered_writes'] if x['kind']!='stack')
    publications=[x for x in trace['ordered_writes'] if x['pc']==0x4a278]
    assert publications==[dict(pc=0x4a278,address=details['outer_a0'],size=4,value=details['outer_a1'],kind='ram')]
    return dict(callback_entry=call,callback_return=after,after_MOVEM_WORD=restored)

def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/animation_rts_callback_native';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'observation.json';path.unlink(missing_ok=True)
    program,source=load_verified_program(root);assert sha(program)==SOURCE_SHA256
    assert program[TARGET:TARGET+2]==bytes.fromhex('4e75') and program[0x4a50c:0x4a510]==TARGET.to_bytes(4,'big')
    instructions=[]
    for a,b in RANGES: instructions.extend(disassemble_range(program,a,b-a,a))
    for r in instructions: assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
    branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
    source_path=folder/'source.json';source_path.write_text(json.dumps(dict(source=source,ranges=RANGES,boundaries=BOUNDARIES,instructions=instructions,
        actual_rts=dict(cpu_address=TARGET,rom_offset=TARGET,raw='4e75',sha256=sha(program[TARGET:TARGET+2])),
        dispatch_slots=target_slots(program),second_WORD_inventory=second_inventory(program),note='Fixed CPU addresses equal canonical ROM offsets; RTS target is not a stub.'),indent=2)+'\n')
    names=('tools/observe_animation_rts_callback.py','tools/observe_animation_control_commands.py','tools/disassemble_program.py',
        'tools/verify_object_reset.py','tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py',str(source_path.relative_to(root)))
    inputs={n:sha((root/n).read_bytes()) for n in names};oracle=oracle_provenance();observer=Observer(program,branches)
    rows=[];outcomes=collections.defaultdict(collections.Counter);port_count=0
    for index,case in enumerate(cases(program)):
        ram,regs,details=fixture(case,index,program);observer.prepare(ram,regs);first=observer.run();info,before,output,ports,trace=first
        evidence=check(case,details,info,trace)
        # A second independent reset/execution must reproduce all native values and lossless traces.
        observer.prepare(ram,regs);assert observer.run()==first
        prefix='case_%04d_begin'%index
        payloads={prefix+'_input.bin':before,prefix+'_native.bin':output,prefix+'_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace)+'\n').encode()}
        for n,b in payloads.items(): (folder/n).write_bytes(b)
        info.update(phase='begin',host_changes=[],evidence=evidence,port_count=len(ports)//9,files={n:sha(b) for n,b in payloads.items()},
            input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json')
        for b in trace['branches']:outcomes[b['pc']][b['next_pc']]+=1
        port_count+=len(ports)//9;rows.append(dict(case_index=index,fixture=case,details=details,phases=[info]))
    controls=[]
    for selector in (0x1d,):
        case=dict(opcode=0x14,first_selector=3,second_selector=None,operand=0,family='guard')
        ram,regs,_=fixture(case,100000,program);ram=bytearray(ram);put(ram,SCRIPT+1,1,selector);observer.prepare(ram,regs)
        try: observer.run();raise RuntimeError('unsupported callback was accepted')
        except AssertionError: error=observer.error
        assert error==dict(kind='unsupported-code',pc=0x2b3e8)
        controls.append(dict(name='actual-other-callback-not-stubbed',error=error,artifacts_written=False))
    assert inputs=={n:sha((root/n).read_bytes()) for n in names} and oracle==oracle_provenance()
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    for row in rows:
        for n,h in row['phases'][0]['files'].items():assert sha((folder/n).read_bytes())==h
    report=dict(source=source,oracle=oracle,inputs=inputs,entry_pc=ENTRY,cases=len(rows),phases=len(rows),total_native_ports=port_count,
        cases_by_opcode=dict(collections.Counter(hex(r['fixture']['opcode']) for r in rows)),dispatch_slots=target_slots(program),
        observed_branch_successors={hex(a):{hex(b):v for b,v in sorted(c.items())} for a,c in sorted(outcomes.items())},
        guard_controls=controls,reproduced_twice=True,original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,
        failure=None,results=rows,scope='Unpatched whole49fc6 -> actual RTS03679e via14/3c, synthetic liveRAM scripts; fullRAM15R/RTS carry/orderedPVC/read-write-PC/stack trace.',
        limitations=['No unsupported callback treated as no-op; only ROM03679e raw4e75 target accepted.',
            'Canonical A5/A6; no physicalmirror, fullCCR/cycles/IRQ or natural script/group reachability claim.',
            'Operand LONG is passed without dereference by this actual RTS; this does not generalize to other callees.',
            'Unicorn instruction/memory hooks and isolated non-RAM stack; no physical CPU equivalence or C++ comparison.'])
    path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),phases=len(rows),ports=port_count,sha256=sha(path.read_bytes()))))

if __name__=='__main__':main()

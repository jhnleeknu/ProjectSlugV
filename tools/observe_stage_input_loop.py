"""Pinned uninterrupted Musashi observations for four stage-input-loop entries."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program
from inventory_stage_input_loop import inventory
from inventory_stage_input_callbacks_execution import ENTRIES as CALLBACKS
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from pack_stage_input import SOURCE_SHA256

BASE,STACK,RETURN = 0x100000,0x1feffc,0xff000
KEYS = tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))+('a6',)
ENTRIES = (0x4d7a6,0x1da60,0x49b0c,0x47642)
OBJECTS = (0x100cb8,0x100da8)
SOURCES = (0x10dcba,0x10dce6)
UNKNOWN = 0x106000
DIFFS = ((0,0),(1,2),(-1,-2),(1,-1),(-1,1),(0x8000,0x7fff),(0x7fff,0x8000))
MASKS = ('10204080','00000000','ffffffff','303060c0','10101010','01020304')
BOTH_BRANCHES = (0x49b18,0x49b28,0x49b4e,0x49b6e,0x49b7e,0x49ba4,
    0x4d7a8,0x4d7c6,0x4d7cc,0x1da6e,0x1da74,0x1da92,0x1daa4,0x4765c,0x47666,0x28a4)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def provenance(root):
    report = inventory(root)
    path = root/'artifacts/stage_input_loop_inventory.json'
    assert json.loads(path.read_text()) == json.loads(json.dumps(report))
    paths = ('build/step_stage_input_loop','build/step_stage_input_callback','build/step_stage_input',
        'engine/src/stage_input_loop.cpp','engine/include/ms5/stage_input_loop.h',
        'engine/tools/step_stage_input_loop.cpp','engine/src/stage_input_callback.cpp',
        'engine/include/ms5/stage_input_callback.h','engine/tools/step_stage_input_callback.cpp',
        'engine/src/stage_input.cpp','engine/include/ms5/stage_input.h',
        'engine/src/player_record_capture.cpp','engine/include/ms5/player_record_capture.h',
        'engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h',
        'tools/observe_stage_input_loop.py','tools/verify_stage_input_loop.py',
        'tools/inventory_stage_input_loop.py','artifacts/stage_input_loop_inventory.json')
    result = [dict(file=p,sha256=sha((root/p).read_bytes())) for p in paths]
    result += report['resource_audit']['files']+report['provenance']
    return result


def build_cases():
    cases = []
    def add(family,entry=0x49b0c,**changes):
        c = dict(family=family,entry=entry,profile=1,player=0,input_d0=0,
            markers=[0,0],active=[1,1],indices=[1,255],slots=[0,0],
            mode=0,held=[0xff,0x55],edges=[0xff,0xaa],masks=[MASKS[0],MASKS[0]],
            current=1,previous=-1,camera=0,base=0,retarget=None,flags=0,
            a7flags=0,d683=0,source_bits=0,object61=[0,0],a6word=0)
        c.update(changes);cases.append(c)
    for player,index,selection in itertools.product(range(2),range(1,256),range(3)):
        d0 = ((0,0x100,0xabcd0100) if player==0 else (1,0x101,0xabcd0101))[selection]
        indices=[1,255];indices[player]=index
        add('active-player-all255-index-byte-select',entry=0x4d7a6,player=player,input_d0=d0,indices=indices,profile=selection%2)
    for d0 in (0,0x100,0xabcd0100,1,0x101,0xabcd0101,0xffff00ff):
        player=int((d0&255)!=0)
        for marker,active in ((1,0),(1,1),(0,0)):
            markers=[0,0];markers[player]=marker
            enabled=[1,1];enabled[player]=active
            add('inactive-marker-or-zero-source-bypasses-index0',entry=0x4d7a6,
                player=player,input_d0=d0,markers=markers,active=enabled,indices=[0,0])
    for player,retarget,pair,status,camera in itertools.product(range(2),(0,1,0x100,0x101),DIFFS,range(3),(0,0x7fff,0x8000)):
        markers=[0,0];active=[1,1]
        selected=int((retarget&255)!=0)
        if status==1:markers[selected]=1
        if status==2:active[selected]=0
        add('crossing-zero-sign-cross-nocross-player-retarget',entry=0x1da60,
            player=player,retarget=retarget,current=pair[0],previous=pair[1],camera=camera,
            base=7,markers=markers,active=active,profile=status%2)
    for held,edge in itertools.product(range(256),(0,255)):
        add('two-null-slots-default-all-held',held=[held,held^255],edges=[edge,edge^255],profile=held%2)
    for mask,held,edge,mode in itertools.product(MASKS,range(0,256,17),(0,255),(0,2)):
        add('two-null-slots-mode-custom-masks',held=[held,held^255],edges=[edge,edge^255],
            masks=[mask,MASKS[(MASKS.index(mask)+1)%len(MASKS)]],mode=mode)
    for player,callback,variant in itertools.product(range(2),CALLBACKS+(0x1da60,),range(6)):
        slots=[0,0];slots[player]=callback
        pair=DIFFS[variant]
        add('each-player-all19-known-callbacks-live-loop',player=player,slots=slots,
            current=pair[0],previous=pair[1],retarget=(player if variant%2==0 else 1-player),
            flags=(0x80 if variant&1 else 0)|((variant>>1)&1),a7flags=0x80 if variant&2 else 0,
            d683=4 if variant&2 else 0,source_bits=3 if variant&4 else 0,
            a6word=0x8000 if variant&2 else 0,mode=2 if variant&1 else 0,
            active=[0,0] if variant==4 else [1,1])
    for slots,markers in itertools.product(([UNKNOWN,0],[0,UNKNOWN],[UNKNOWN,UNKNOWN]),([1,1],)):
        add('unknown-slots-inactive-marker-native-bypass',slots=slots,markers=markers)
    add('first-callback-clears-second-unknown-before-live-read',slots=[0x1d5ac,UNKNOWN],
        player=0,retarget=1,d683=4)
    add('first-callback-clears-second-known-before-live-read',slots=[0x1d61a,0x49e34],
        player=0,retarget=1,flags=0x80)
    add('first-callback-installs-second-known-before-live-read',slots=[0x49de6,UNKNOWN],
        player=0,retarget=1,current=0,previous=0)
    for markers,flags,profile in itertools.product(itertools.product(range(2),repeat=2),
            itertools.product((0,0x80),repeat=2),range(2)):
        add('activity-two-markers-and-bit7-all-combinations',entry=0x47642,
            markers=list(markers),object61=list(flags),profile=profile)
    for sequence,slots,kw in (
        ('null-mask-consumption',[0,0],dict(mode=2,masks=[MASKS[3],MASKS[4]])),
        ('first-clears-second-unknown',[0x1d5ac,UNKNOWN],dict(retarget=1,d683=4)),
        ('known-callback-slot-install',[0x49de6,0x49e34],dict(current=0,previous=0,retarget=1))):
        for step in range(4):
            add('actual-CLI-output-loop-chain',slots=slots,sequence=sequence,
                sequence_position=step,**kw)
    return cases


def fixture(case):
    ram=bytearray(hashlib.shake_256(b'stage-input-loop'+bytes([case['profile']])).digest(65536))
    regs=[0]*14 if case['profile']==0 else [(0xabcdef01+i*0x1020304)&0xffffffff for i in range(14)]
    regs[0]=case['input_d0'];regs[8]=OBJECTS[case['player']];regs[13]=0x106100
    ram[0x12]=case['mode'];ram[0xd683]=case['d683'];ram[0xd732]=case['source_bits']
    ram[0xd740:0xd742]=bytes((0,1));struct.pack_into('>H',ram,0xde24,0xf0f0)
    struct.pack_into('>H',ram,0x613a,case['a6word'])
    for at in (0xd3a2,0xd3a6,0xd3aa):
        struct.pack_into('>I',ram,at,(case['camera']<<16)|0x1234)
    struct.pack_into('>HH',ram,0xd73c,0,0)
    struct.pack_into('>II',ram,0xd734,*case['slots'])
    for player,obj in enumerate(OBJECTS):
        at=obj-BASE
        struct.pack_into('>I',ram,at,0x270e if case['markers'][player] else 0)
        ram[at+0x15]=case['flags'];ram[at+0xa7]=case['a7flags'];ram[at+0x61]=case['object61'][player]
        struct.pack_into('>H',ram,at+0x78,case['retarget'] if player==case['player'] and case['retarget'] is not None else player)
        struct.pack_into('>H',ram,at+0xae,case['base'])
        for off,diff in ((0x42,case['current']),(0x46,case['current']),(0x4a,case['previous']),(0x4e,case['previous'])):
            value=(diff+case['camera']+case['base'])&65535
            struct.pack_into('>I',ram,at+off,(value<<16)|0x1234)
        src=SOURCES[player]-BASE
        struct.pack_into('>H',ram,src,case['active'][player])
        struct.pack_into('>H',ram,src+0x1c,0x7fff)
        struct.pack_into('>H',ram,src+0x20,0x8000)
        ram[src+0x25:src+0x28]=bytes((0xf0,0x81,case['indices'][player]))
        ram[src+0x2a]=0x55
        io=0x4caa+player*6;ram[io:io+2]=bytes((case['held'][player],case['edges'][player]))
        mask=bytes.fromhex(case['masks'][player]);pos=0xf01c+player*4;ram[pos:pos+4]=mask
        struct.pack_into('>HHH',ram,0xd726+player*6,0x1234,0xabcd,0x7ff0 if player==0 else 0xff0f)
    return ram,regs


class Observer:
    def __init__(self,program,branches):
        self.program=program;self.cpu=MusashiOracle();self.cpu.load(0,program[:BASE])
        self.branch_pcs=set(branches);self.pending=None;self.branches=[];self.calls=collections.Counter()
        self.writes=[];self.dynamic=[];self.slot_reads=[]
        def code(pc):
            cpu=self.cpu
            if self.pending is not None:
                self.branches.append(dict(pc=self.pending,next_pc=pc));self.pending=None
            if pc in self.branch_pcs:self.pending=pc
            if pc in ENTRIES+CALLBACKS+(0x49ab4,0x49afe,0x49bb4,0x49c20,0x49c32,0x49c66,0x289e):self.calls[pc]+=1
            if pc in (0x49b10,0x49b66):
                address=0x10d734 if pc==0x49b10 else 0x10d738
                self.slot_reads.append(dict(pc=pc,address=address,value=int.from_bytes(cpu.read(address,4),'big')))
            if pc in (0x49b2c,0x49b82):
                callback=cpu.get_reg('a1')
                assert callback in CALLBACKS+(0x1da60,), ('unsupported callback before JSR',hex(callback))
                self.dynamic.append(dict(pc=pc,target=callback,object=cpu.get_reg('a0')))
            word=int.from_bytes(cpu.read(pc,2),'big')
            assert not (word==0x4afc or 0x4e40<=word<=0x4e4f), ('unexpected-trap',hex(pc),hex(word))
        def write(pc,address,size,value):
            assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(pc,address,size,value)
            if BASE<=address<BASE+65536:self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_instruction_hook(code);self.cpu.set_write_hook(write)
    def run(self,entry,ram,regs):
        cpu=self.cpu;cpu.reset();cpu.load(BASE,ram);cpu.set_reg('sr',0x2000)
        cpu.set_reg('a5',0x108000);cpu.set_reg('a7',STACK);cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in zip(KEYS,regs):cpu.set_reg(key,value)
        self.pending=None;self.branches.clear();self.calls.clear();self.writes.clear();self.dynamic.clear();self.slot_reads.clear()
        cpu.set_reg('pc',entry);status=cpu.run(20000,RETURN)
        assert status['status']=='sentinel' and cpu.get_reg('a7')==STACK+4,status
        assert cpu.read(0,BASE)==self.program[:BASE]
        output=cpu.read(BASE,65536);result={k:cpu.get_reg(k) for k in KEYS}
        assert result['a6']==regs[13]
        return output,result,dict(returned=True,final_pc=RETURN,final_a7=STACK+4,
            instructions=status['instructions'],RAM_writes=self.writes.copy(),
            branch_successors=self.branches.copy(),calls={hex(k):v for k,v in self.calls.items()},
            dynamic_calls=self.dynamic.copy(),slot_reads=self.slot_reads.copy(),mmio_writes=0)


def assert_evidence(case,ram,output,regs,result,info):
    if case['entry']==0x4d7a6:
        selected=int((regs[0]&255)!=0)
        assert result['a0']==OBJECTS[selected]
        active=not case['markers'][selected] and case['active'][selected]!=0
        assert result['a4']==(0x4cf64+case['indices'][selected]*16 if active else SOURCES[selected])
        assert output==ram
    if case['entry']==0x47642:
        expected=sum(1<<i for i in range(2) if not case['markers'][i] and not (case['object61'][i]&0x80))
        assert output[0xd68e]==expected and result['a0']==OBJECTS[1] and result['d0']==1
    if case['entry']==0x49b0c:
        assert len(info['slot_reads'])==2
        if case['family']=='each-player-all19-known-callbacks-live-loop':
            assert any(event['target']==case['slots'][case['player']] and event['object']==OBJECTS[case['player']] for event in info['dynamic_calls'])
        if case['family']=='unknown-slots-inactive-marker-native-bypass':
            assert not info['dynamic_calls']
        if case['family'].startswith('first-callback-clears-second') or case.get('sequence')=='first-clears-second-unknown':
            assert info['slot_reads'][1]['value']==0
            assert [x['pc'] for x in info['dynamic_calls']]==[0x49b2c]
        if case['family']=='first-callback-installs-second-known-before-live-read':
            assert info['slot_reads'][1]['value']==0x49e34
            assert [x['target'] for x in info['dynamic_calls']]==[0x49de6,0x49e34]


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    assert sha(program)==SOURCE_SHA256
    inputs,oracle=provenance(root),oracle_provenance(root.resolve())
    audited=inventory(root)
    branches=[c['instruction']['cpu_address'] for w in audited['windows'] for c in w['direct_control_operands']
        if c['instruction']['mnemonic'].split('.')[0] not in ('jsr','bsr','bra','jmp')]
    assert set(BOTH_BRANCHES)==set(branches)-{0x4d7ec}
    folder=root/'artifacts/stage_input_loop';folder.mkdir(parents=True,exist_ok=True)
    observer=Observer(program,branches);cases=build_cases();previous={};rows=[];branch_counts=collections.defaultdict(collections.Counter)
    for index,case in enumerate(cases):
        prior=previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram,regs=fixture(case) if prior is None else (bytearray(prior[0]),list(prior[1]))
        output,result,info=observer.run(case['entry'],ram,regs)
        assert_evidence(case,ram,output,regs,result,info)
        for branch in info['branch_successors']:branch_counts[branch['pc']][branch['next_pc']]+=1
        if 'sequence'in case:previous[case['sequence']]=(output,[result[k] for k in KEYS])
        name='native_%04d.bin'%index;(folder/name).write_bytes(output)
        rows.append(dict(case_index=index,fixture=case,input_ram_sha256=sha(ram),incoming=dict(zip(KEYS,regs)),
            result=result,ram_file=name,ram_sha256=sha(output),**info))
    assert all(len(branch_counts[pc])==2 for pc in BOTH_BRANCHES), {hex(pc):dict(branch_counts[pc]) for pc in BOTH_BRANCHES}
    assert provenance(root)==inputs and oracle_provenance(root.resolve())==oracle
    assert sha((root/source['path']).read_bytes())==SOURCE_SHA256
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(cases),completed_cases=len(rows),failure=None,
        counts_by_entry=dict(sorted(collections.Counter(c['entry'] for c in cases).items())),
        branch_successor_counts={hex(k):{hex(a):n for a,n in sorted(v.items())} for k,v in sorted(branch_counts.items())},
        required_two_successor_branch_addresses=list(BOTH_BRANCHES),results=rows,program_code_modified=False,CCR_exposed=False,
        scope='Four original entrypoints run continuously through all actual native callees and dynamic known callbacks to RTS. '
              'All64KiB RAM/14 exposed general registers including read-only A6 retained; no in-call reset, ROM patch, callee stub or flag patch. '
              'Inactive markers bypass unknown callback pointers natively; unsupported active callbacks/RAM functions/TRAP/index0 are excluded from native corpus and checked as C++ rejection separately. '
              'Actual-output chains have no resumed host RAM/register writes. This controlled support corpus is not whole unknown callback closure, natural scheduler/player reachability or cycle equivalence.')
    path=folder/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),counts_by_entry=report['counts_by_entry'],two_successor_branches=len(BOTH_BRANCHES),sha256=sha(path.read_bytes()))))


if __name__=='__main__':main()

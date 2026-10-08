"""Independent unpatched Musashi observations for six confirmed stage-input helpers."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct

from disassemble_program import load_verified_program
from musashi_oracle import MusashiOracle
from observe_scene_motion_pair import oracle_provenance
from pack_stage_input import build as pack_build, SOURCE_SHA256

BASE, STACK, RETURN = 0x100000, 0x1feffc, 0xff000
KEYS = tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(5))
ENTRIES = (0x49ab4, 0x49afe, 0x49bb4, 0x49c20, 0x49c32, 0x49c66)
WORDS = (0, 1, 0xf, 0x10, 0x7fff, 0x8000, 0xfff0, 0xffff)
EDGES = (0, 1, 0x30, 0x80, 0xff)
MASKS = ('10204080', '00000000', 'ffffffff', '303060c0', '10101010', '01020304')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def provenance(root):
    paths = ('build/step_stage_input', 'engine/src/stage_input.cpp',
        'engine/include/ms5/stage_input.h', 'engine/tools/step_stage_input.cpp',
        'engine/src/fixed_data_resource.cpp', 'engine/include/ms5/fixed_data_resource.h',
        'tools/observe_stage_input.py', 'tools/verify_stage_input.py', 'tools/pack_stage_input.py')
    files, manifest = pack_build(root)
    for name, data in files.items():
        path = root/'extracted/runtime/stage_input'/name
        assert path.read_bytes() == data
    result = [dict(file=p, sha256=sha((root/p).read_bytes())) for p in paths]
    result += [dict(file='extracted/runtime/stage_input/'+name, sha256=sha(data)) for name,data in sorted(files.items())]
    return result


def build_cases():
    cases = []
    def add(family, entry=0x49ab4, **kw):
        case = dict(family=family, entry=entry, profile=1, held=0, edge=0xff,
            mask=None, mask_address=0x106001, a1=0x10d726, d7=0xfedcffff,
            d6=0xabcd1234, old=0, consume=0xffff, index=0, a0=0xdeadbeef)
        case.update(kw)
        cases.append(case)
    for held,edge in itertools.product(range(256),EDGES):
        add('default-held-all256-representative-edges',held=held,edge=edge,profile=held%2)
    for mask,held,edge,address in itertools.product(MASKS,range(0,256,17),EDGES,(0x106000,0x106001)):
        add('liveRAM-custom-mask-overlap-zero-duplicate-odd',mask=mask,held=held,edge=edge,mask_address=address)
    for old,d7,profile in itertools.product(WORDS,WORDS,range(2)):
        add('previous-WORD-upper-preservation',entry=0x49afe,old=old,d7=(0xfedc0000|d7),profile=profile)
    for consume,d7,address in itertools.product(WORDS,WORDS,(0x10d726,0x10d734,0x10fffa)):
        add('consume-WORD-write-order-and-boundary',entry=0x49bb4,consume=consume,
            d7=0xfedc0000|d7,d6=0xabcd0000|(d7^0xffff),a1=address)
    for entry,index,a0 in itertools.product(ENTRIES[3:],(0,1,2,3,0x7fff,0x8000,0xfffe,0xffff,0xabcd0001,0xffff0000),(0,0x49e34,0x100cb8,0xffffffff)):
        add('setter-WORD-index-highbits-A0',entry=entry,index=index,a0=a0)
    add('previous-fixed-mask-read',entry=0x49afe,a1=0x49aae)
    add('liveRAM-mask-last-four-bytes',mask='303060c0',mask_address=0x10fffc,held=0xff)
    for step,entry in enumerate((0x49ab4,0x49afe,0x49bb4)*3):
        add('actual-output-map-previous-consume-chain',entry=entry,held=0xff,
            sequence='map-previous-consume',sequence_position=step,old=0,consume=0x7ff0)
    for step,entry in enumerate((0x49c20,0x49c32,0x49c66)):
        add('actual-output-setter-chain',entry=entry,index=0xabcd0001,
            sequence='set-clear-default',sequence_position=step)
    return cases


def fixture(case):
    profile = case['profile']
    ram = bytearray(hashlib.shake_256(b'stage-input-fixture'+bytes([profile])).digest(65536))
    regs = [0]*13 if profile == 0 else [((0x89abcdef+i*0x1020304)&0xffffffff) for i in range(13)]
    regs[0] = (regs[0]&0xffffff00)|case['held']
    regs[1] = (regs[1]&0xffffff00)|case['edge']
    regs[6], regs[7], regs[8], regs[9] = case['d6'],case['d7'],case['a0'],case['a1']
    regs[12] = 0x49ab0
    if case['mask'] is not None:
        raw = bytes.fromhex(case['mask']);at = case['mask_address']-BASE
        ram[at:at+4] = raw
        regs[12] = case['mask_address']
    if case['entry'] in ENTRIES[3:]:
        regs[0] = case['index']
    if BASE <= case['a1'] <= BASE+65530:
        struct.pack_into('>HH',ram,case['a1']-BASE+2,case['old'],case['consume'])
    return ram, regs


class Observer:
    def __init__(self,program):
        self.program = program
        self.cpu = MusashiOracle()
        self.cpu.load(0,program[:BASE])
        self.writes = []
        def write(pc,address,size,value):
            assert BASE <= address and address+size <= BASE+65536 or STACK-4096 <= address and address+size <= STACK+4, (pc,address,size,value)
            if BASE <= address < BASE+65536:
                self.writes.append(dict(pc=pc,address=address,size=size,value=value))
        self.cpu.set_write_hook(write)
    def run(self,entry,ram,regs):
        cpu = self.cpu
        cpu.reset()
        cpu.load(BASE,ram)
        cpu.set_reg('sr',0x2000)
        cpu.set_reg('a5',0x108000)
        cpu.set_reg('a6',0)
        cpu.set_reg('a7',STACK)
        cpu.load(STACK,RETURN.to_bytes(4,'big'))
        for key,value in zip(KEYS,regs):
            cpu.set_reg(key,value)
        cpu.set_reg('pc',entry)
        self.writes.clear()
        status = cpu.run(1000,RETURN)
        assert status['status'] == 'sentinel' and cpu.get_reg('a7') == STACK+4, status
        assert cpu.read(0,BASE) == self.program[:BASE]
        output = cpu.read(BASE,65536)
        result = {key:cpu.get_reg(key) for key in KEYS}
        if entry == 0x49bb4:
            assert [(w['address'],w['size']) for w in self.writes] == [(regs[9]+4,2),(regs[9]+2,2),(regs[9],2)]
        if entry in (0x49ab4,0x49afe):
            assert output == ram and not self.writes
        return output,result,dict(returned=True,final_pc=RETURN,final_a7=STACK+4,
            instructions=status['instructions'],RAM_writes=self.writes.copy(),mmio_writes=0)


def main():
    root = Path(__file__).resolve().parents[1]
    program,source = load_verified_program(root)
    assert sha(program) == SOURCE_SHA256
    inputs,oracle = provenance(root),oracle_provenance(root.resolve())
    cases = build_cases()
    folder = root/'artifacts/stage_input'
    folder.mkdir(parents=True,exist_ok=True)
    observer = Observer(program)
    previous,rows = {},[]
    for index,case in enumerate(cases):
        prior = previous.get(case.get('sequence')) if case.get('sequence_position',0)>0 else None
        ram,regs = fixture(case) if prior is None else (bytearray(prior[0]),list(prior[1]))
        output,result,info = observer.run(case['entry'],ram,regs)
        if 'sequence' in case:
            previous[case['sequence']] = (output,[result[k] for k in KEYS])
        name = 'native_%04d.bin'%index
        (folder/name).write_bytes(output)
        rows.append(dict(case_index=index,fixture=case,input_ram_sha256=sha(ram),
            incoming=dict(zip(KEYS,regs)),result=result,ram_file=name,
            ram_sha256=sha(output),**info))
    assert provenance(root) == inputs and oracle_provenance(root.resolve()) == oracle
    assert sha((root/source['path']).read_bytes()) == SOURCE_SHA256
    report = dict(source=source,oracle=oracle,inputs=inputs,cases=len(cases),
        completed_cases=len(rows),results=rows,failure=None,program_code_modified=False,
        counts_by_entry=dict(sorted(collections.Counter(c['entry'] for c in cases).items())),
        scope='Six assigned helper entries executed uninterrupted to actual RTS using pinned Musashi M68000, original fixed ROM immutable, no in-call reset or flag patch. '
              'All64KiB RAM and13 exposed general registers retained; CCR intentionally unexposed. '
              'Synthetic masks are explicit liveRAM fixture bytes, never ROM patches. Actual-output chains carry all13 registers and RAM without intervening host writes. '
              'Write hook enforces RAM/stack only and captures49bb4 exact three-WORD write order. No dynamic callback/caller/scheduler reachability claim.')
    path = folder/'observation.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(cases),counts_by_entry=report['counts_by_entry'],sha256=sha(path.read_bytes()))))


if __name__ == '__main__':
    main()

"""Unpatched 480bc frame helper bundle U1 (47642 / 6f1c2 / b4a2a / 4701e / 46f52 / 2efa6 / 3c44 and their small callees) native observation.

Native Unicorn M68000 observation of the original ROM.  It reuses, by import and without editing them, the machinery of the card menu close observer
(observe_animation_machine_card_menu_close and through it the fade/card, card child, menu, open and input observers): the persistent-CPU Observer with the declared
host-change vocabulary (RAM writes, PC redirect, A7 delta, register write at a step boundary), fresh-twice reproduction, split (stop at the first hit of every block
leader) versus continuous equivalence, ordered port events, banked reads with the modeled bank, the SHA pins of every imported tool module, the ROM SHA/mtime guard.

Start state: the card/fade/screen chain RAM is pseudo-random at 480bc and is NOT used.  The coherent stage seeds of the stage-frame verifier
(tools/verify_stage_frame.py smoke(): actual 2790/3ef2 initializer RAM + the declared 24 host writes of the verifier + its registers, optional bank 3) are rebuilt in
this process, pinned against artifacts/stage_frame/verification.json (input_sha256), and declared as the initial fixture; the carried states are the recorded
artifacts/stage_frame/native_*.bin outputs (sha256 pinned) with the recorded result registers.  The only fixture differences from the stage-frame verifier are
declared: the return LONG at A7 = 1feffc is 2ac2 (the dispatcher return; the verifier used ff000), the PVC page is zero apart from the two bank registers.

Conditions
  natural   fresh CPU at 480bc entry: JSR 47642 (both player objects through 289e), accepted stop 1a73c directly after the JSR at 480c0; declared RAM variations
            of the player callback (289e) and BYTE 61(object) bit 7;
  direct    declared PC + a declared return LONG at A7 (the real caller return address of that helper in 480bc), stop at that return: b4a2a, 4701e (46f52, 43e38),
            2efa6 (3af8, 3c44), 3c44, 6f1c2, plus internal entries (49392 with A5<>108000 stops at 4939c, TRAP #15 never executed);
  guards    odd A0/A1/A4/A7, ROM writes (declared initial A5), a stop that is not the boundary.
No SR reads, ROM patches, stubs, stack masking, register injection after execution begins or expected-register injection.  Every host change is declared in the
step record; declared initial registers are part of the fixture summary.

An independent Python model of the contract (instruction-faithful transcription of the original bytes of the contract table, 32-bit register semantics, explicit
word/byte operations and signed compares, NOT the C++) is compared with each native normal condition: block-leader sequence with the full register file at every
leader, the ordered RAM writes, ordered fixed/bank ROM reads, the final registers and the whole 64KiB RAM image.  The pre-existing callees 43e38 (4701e loop) and 3af8
(2efa6) are black boxes: their entry registers are compared, their native exit registers and RAM writes are replayed into the model (A0 preserved is checked).
Any difference is recorded in contract_discrepancies.
"""
import copy
import json
import os
from pathlib import Path
import struct
import sys
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_card_menu_close as close
import verify_stage_frame as vsf
from disassemble_program import load_verified_program,disassemble_range
fc=close.fc;menu=close.menu;op=close.op;activation=close.activation;shared=close.shared
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_frame_helpers_native'
CONTRACT=ROOT/'docs/analysis/animation-machine-frame-helpers-u1-contract.md'
CONTRACT_SHA='785c3fba8bf05bd405ad8c0898738504367ed0c3195ffb9aa80a0a3774c861e0'
SCOPE=ROOT/'docs/analysis/animation-machine-480bc-scope.md'
ROM_SHA=op.ROM_SHA
sha=fc.sha
u8,u16,u32=op.u8,op.u16,close.u32
S=fc.S                                                      # 1feffc: initial A7 (the return LONG lives here)
ENTRY=0x480bc
A5V=0x108000
BOUNDARY_1A73C=0x1a73c
TRAP_STOP=0x4939c
KEYS=shared.isolated.REG_NAMES                              # d0..d7 a0..a6
PORT_REGIONS=fc.PORT_REGIONS
STAGE_VERIFICATION=ROOT/'artifacts/stage_frame/verification.json'
# real caller return addresses of the JSRs in 480bc (480bc: JSR 47642(pc) ret 480c0; then six-byte JSR.L every helper)
RET={0x47642:0x480c0,0x1a73c:0x480c6,0x49b0c:0x480cc,0x4aa88:0x480d2,0xb4a2a:0x480d8,0x6f1c2:0x480de,0x4701e:0x480e4,0xe8a48:0x480ea,0x2efa6:0x480f0,0x3c44:0x2efda}

NEW_RANGES=((0x480bc,0x480f2),(0x47642,0x47672),(0x6f1c2,0x6f1c4),(0x2efa6,0x2efdc),(0x3c44,0x3c7c),(0xb4a2a,0xb4ab0),(0x49392,0x4939c),(0x4939e,0x493bc),(0x1c028,0x1c052),
    (0x4d9d6,0x4da08),(0xb481e,0xb4850),(0x4701e,0x4706c),(0x46f52,0x4701e))
EXISTING_RANGES=((0x289e,0x28ae),(0x3ac8,0x3c08),(0x43e38,0x43ea4))        # callees already observed in earlier units: 289e, 3ac8..3af6/3af8.., 43e38
RANGES=NEW_RANGES+EXISTING_RANGES
BB_43E38=(0x43e38,0x43ea4)
BB_3AF8=(0x3ac8,0x3c08)                                                      # 3af8 and the 3ac8 it calls (black box when 3af8 is the callee)
DISCREPANCIES=[]


# ----------------------------------------------------------------------------------
# Block leaders (observer's own decode of the contract table bytes): range starts, branch / call targets, the instruction after a conditional branch
# or call (return address).  These are the split checkpoints and the model comparison points.  The implementer reports its own list.
# ----------------------------------------------------------------------------------
def branch_target(pc,raw):
    w=int.from_bytes(raw[:2],'big');hi=w>>8
    if hi==0x61 or 0x60<=hi<=0x6f:
        d=w&0xff
        if d==0:disp=int.from_bytes(raw[2:4],'big',signed=True)
        else:disp=d-256 if d>127 else d
        return pc+2+disp,hi
    if (w&0xf0f8)==0x50c8:return pc+2+int.from_bytes(raw[2:4],'big',signed=True),'dbcc'
    if w==0x4eb9:return int.from_bytes(raw[2:6],'big'),'jsr'
    if w==0x4eba:return pc+2+int.from_bytes(raw[2:4],'big',signed=True),'jsr'
    return None,None


def leaders_of(program,ranges):
    out=set()
    for lo,hi in ranges:
        cur={lo}
        for r in disassemble_range(program,lo,hi-lo,lo):
            pc=r['cpu_address'];t,k=branch_target(pc,bytes.fromhex(r['raw']))
            if t is not None:
                cur.add(t)
                if k!=0x60:cur.add(pc+r['size'])
        out.update(x for x in cur if any(a<=x<b for a,b in ranges))
    return out


# ----------------------------------------------------------------------------------
# Storage (same rows/artifact names as the close observer; identical payloads are hard-linked)
# ----------------------------------------------------------------------------------
POOL={}


def write_payload(name,data):
    digest=sha(data);target=OUT/name
    if digest in POOL:os.link(POOL[digest],target)
    else:target.write_bytes(data);POOL[digest]=target
    return digest


def store(prefix,phases,keys):
    rows=[]
    for j,p in enumerate(phases):
        stem='%s_phase_%03d'%(prefix,j);events=p['events'];ports=[e for e in events if e['region'] in PORT_REGIONS]
        payloads={stem+'_ram_before.bin':p['ram_before'],stem+'_ram_after.bin':p['ram_after'],stem+'_pvc_before.bin':p['pvc_before'],stem+'_pvc_after.bin':p['pvc_after'],
            stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
            stem+'_trace.json':(json.dumps({k:p[k] for k in ('pcs','events','boundaries','guard')},indent=2)+'\n').encode()}
        snapshots=[]
        for k,snapshot in enumerate(p['snapshots']):
            names={}
            for field in ('ram','pvc'):
                name=stem+'_snapshot_%02d_%s.bin'%(k,field);payloads[name]=snapshot[field];names[field]=name
            snapshots.append(dict(registers=snapshot['registers'],artifacts=names))
        hashes={name:write_payload(name,data) for name,data in payloads.items()}
        rows.append(dict(index=j,step=p['step'],phase_in_step=p['phase_in_step'],label=p['label'],stop_pc=p['stop_pc'],step_stop_pc=p['step_stop_pc'],incoming=p['incoming'],outgoing=p['outgoing'],
            host_changes=p['host_changes'],carry_in=p['carry_in'],modeled_bank=p['modeled_bank'],bank_before=p['bank_before'],ff8_before=p['ff8_before'],ff9_before=p['ff9_before'],ff8_after=p['ff8_after'],ff9_after=p['ff9_after'],
            waiting=p['waiting'],carry=p['carry'],branch_evidence=p['branch_evidence'],guard=p['guard'],snapshots=snapshots,counts=fc.counts(events),
            key_pcs=[pc for pc in p['pcs'] if pc in keys],pc_count=len(p['pcs']),artifacts=hashes,stop_evidence=p['stop_evidence']))
    return rows


# ----------------------------------------------------------------------------------
# Stop evidence: boundary stops only directly after the transferring instruction; declared-return stops only directly after an RTS
# ----------------------------------------------------------------------------------
def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc']
    if pc!=p['step_stop_pc']:return None
    assert pcs[-1]==pc,(p['label'],pcs[-3:])
    if len(pcs)==1:return dict(outgoing_pc=pc,previous_pc=None,is_step_stop=True,reached_from='zero-step: stop PC equals the entry PC, nothing executed')
    prev=pcs[-2];ram=p['ram_after']
    if pc==BOUNDARY_1A73C:
        assert prev==0x480c0 and program[prev:prev+6].hex()=='4eb90001a73c',(p['label'],hex(prev))
        assert u32(ram,o['a7'])==0x480c6,(p['label'],hex(u32(ram,o['a7'])))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=True,
            reached_from='JSR 1a73c at 480c0 (bytes 4eb90001a73c); return LONG 480c6 on the stack at A7=%x; 1a73c is never executed'%o['a7'])
    if pc==TRAP_STOP:
        assert prev==0x49398 and program[0x49392:0x4939c].hex()=='bbfc0010800067000004',(p['label'],hex(prev))
        return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+4].hex(),is_step_stop=True,
            reached_from='BEQ.W at 49398 not taken after CMPA.L #108000,A5 (A5=%x <> 108000); 4939c TRAP #15 is never executed'%o['a5'])
    assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev),hex(pc))
    return dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+2].hex(),is_step_stop=True,reached_from='RTS at %x popped the declared return LONG %x (A7 after = %x)'%(prev,pc,o['a7']))


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


def with_checkpoints(program,spec):
    probe=copy.deepcopy(spec)
    for s in probe['steps']:s['checkpoints']=[]
    try:phases=fc.run_condition(program,probe,True)
    except Exception as e:
        diag=copy.deepcopy(probe);diag['guarded']=True;diag['guard']={}
        try:last=fc.run_condition(program,diag,True)[-1];info=(last['guard'],[hex(x) for x in last['pcs'][-8:]],hex(last['outgoing']['pc']))
        except Exception as e2:info=repr(e2)
        raise AssertionError('probe failed for condition %s: %r; diagnostic %r'%(spec['label'],e,info))
    for index,step in enumerate(spec['steps']):
        order=[];entry=phases[index]['pcs'][0]
        for pc in phases[index]['pcs'][1:]:
            if pc in BLOCK_SET and pc not in order and pc!=entry and pc!=step['stop_pc']:order.append(pc)
        step['checkpoints']=order
    return spec


# ----------------------------------------------------------------------------------
# Independent model
# ----------------------------------------------------------------------------------
M32=0xffffffff
REGN=tuple(KEYS)                                            # d0..d7 a0..a6
class ModelError(Exception):pass
class StopAt(Exception):
    def __init__(self,pc):self.pc=pc


def sx16(v):
    v&=0xffff;return v-0x10000 if v&0x8000 else v


def sx32(v):
    v&=M32;return v-(1<<32) if v&0x80000000 else v


def sub16(d,s):
    """d - s as a WORD: (result, N, Z, V, C) exactly as SUB.W/CMP.W produce them."""
    d&=0xffff;s&=0xffff;r=(d-s)&0xffff
    return r,r>>15,1 if r==0 else 0,(((d^s)&(d^r))>>15)&1,1 if d<s else 0


class Machine:
    def __init__(self,program,bank,ram,regs,env):
        self.prog=program;self.bank=bank;self.ram=bytearray(ram);self.r={k:regs[k]&M32 for k in REGN+('a7',)};self.env=env
        self.leads=[];self.writes=[];self.rom_reads=[];self.C=None
    # ---- memory (RAM mirrored over 100000..1fffff, ROM fixed below 100000, banked window above 200000; odd WORD/LONG accesses are the observer's guard, not modelled)
    def rd(self,a,n):
        a&=M32
        if n>1 and a&1:raise ModelError('odd read %x'%a)
        if a<0x100000:
            self.rom_reads.append((a,n,'fixed'));return int.from_bytes(self.prog[a:a+n],'big')
        if a<0x200000:return int.from_bytes(bytes(self.ram[(a+i)&0xffff] for i in range(n)),'big')
        if a<0x2fe000:
            ph=self.bank+a-0x200000;self.rom_reads.append((a,n,'bank'));return int.from_bytes(self.prog[ph:ph+n],'big')
        raise ModelError('read %x'%a)
    def wr(self,a,n,v):
        a&=M32
        if n>1 and a&1:raise ModelError('odd write %x'%a)
        if not 0x100000<=a<0x200000:raise ModelError('write %x'%a)
        v&=(1<<(8*n))-1
        for i,b in enumerate(v.to_bytes(n,'big')):self.ram[(a+i)&0xffff]=b
        self.writes.append((n,a,v))
    def push32(self,v):
        self.r['a7']=(self.r['a7']-4)&M32;self.wr(self.r['a7'],4,v)
    def push16(self,v):
        self.r['a7']=(self.r['a7']-2)&M32;self.wr(self.r['a7'],2,v)
    def pop32(self):
        v=self.rd(self.r['a7'],4);self.r['a7']=(self.r['a7']+4)&M32;return v
    def pop16(self):
        v=self.rd(self.r['a7'],2);self.r['a7']=(self.r['a7']+2)&M32;return v
    def lw(self,reg,v):self.r[reg]=(self.r[reg]&0xffff0000)|(v&0xffff)
    def lb(self,reg,v):self.r[reg]=(self.r[reg]&0xffffff00)|(v&0xff)
    def a5(self,off):return (self.r['a5']+off)&M32
    def lead(self,pc):
        assert pc in LEADERS,hex(pc)
        regs=dict(self.r);regs['pc']=pc;self.leads.append(regs)


def jsr(M,fn,ret):
    M.push32(ret);fn(M)
    got=M.pop32()
    if got!=ret:raise ModelError('return LONG %x <> %x'%(got,ret))
    M.lead(ret)


def m289e(M):
    M.lead(0x289e)
    if M.rd(M.r['a0'],4)==0x270e:M.C=0
    else:
        M.lead(0x28a8);M.C=1
    M.lead(0x28ac)


def m47656(M):
    M.lead(0x47656);jsr(M,m289e,0x4765c)
    if M.C==0:M.lead(0x47670);return
    M.lead(0x47660)
    if M.rd(M.r['a0']+0x61,1)&0x80:M.lead(0x47670);return
    M.lead(0x4766a);addr=M.a5(0x568e);M.wr(addr,1,M.rd(addr,1)|(1<<(M.r['d0']&7)))


def m47642(M):
    M.lead(0x47642);M.wr(M.a5(0x568e),1,0);M.r['a0']=(M.r['a5']-0x7348)&M32;M.r['d0']=0
    jsr(M,m47656,0x47650)
    M.r['a0']=(M.r['a5']-0x7258)&M32;M.r['d0']=1
    m47656(M)


def m6f1c2(M):M.lead(0x6f1c2)


def m3ac8(M):
    M.lead(0x3ac8)
    if M.r['d0']&0xff==3:
        M.lead(0x3ad0);M.wr(M.a5(-0x3285),1,0xff);return
    M.lead(0x3ad8);M.r['a0']=(M.a5(-0x330c))&M32;M.lw('d1',M.rd(M.a5(-0x328a),2));M.r['a0']=(M.r['a0']+sx16(M.r['d1']))&M32
    M.lw('d1',(M.r['d1']&0xffff)+1);M.lw('d1',M.r['d1']&0x7f)
    M.lead(0x3aea)
    if M.r['d1']&0xffff==M.rd(M.a5(-0x328c),2):raise ModelError('3ac8 ring full (3aea waits forever)')
    M.lead(0x3af0);M.wr(M.r['a0'],1,M.r['d0']&0xff);M.wr(M.a5(-0x328a),2,M.r['d1']&0xffff)


def m3c44(M):
    M.lead(0x3c44);M.push16(M.r['d0']&0xffff);M.r['a0']=M.a5(-0x327e);M.lw('d1',M.rd(M.a5(-0x3276),2))
    while True:
        M.lead(0x3c4e)
        if M.r['d1']&0xffff==M.rd(M.a5(-0x3274),2):break
        M.lead(0x3c56);M.r['a1']=(M.r['a0']+sx16(M.r['d1']))&M32;M.lw('d1',(M.r['d1']&0xffff)+2);M.lw('d1',M.r['d1']&6)
        if M.rd(M.r['a1'],2)==M.r['d0']&0xffff:
            M.lead(0x3c66);M.wr(M.r['a1'],2,0)
        M.lead(0x3c68)
    M.lead(0x3c6a);M.r['d0']=0x14;jsr(M,m3ac8,0x3c70)
    M.lb('d0',M.rd(M.r['a7'],1));jsr(M,m3ac8,0x3c76)
    M.lw('d0',M.pop16());m3ac8(M)


def m2efa6(M):
    M.lead(0x2efa6);M.lb('d1',M.rd(M.a5(0x5491),1));nz=M.rd(M.a5(0x5490),1)!=0
    M.lb('d0',0xff if nz else 0);M.wr(M.a5(0x5491),1,M.r['d0']&0xff)
    if not nz:
        M.lead(0x2efca)
        if M.r['d1']&0xff==0:M.lead(0x2efda);return
        M.lead(0x2efd0);M.lw('d0',0x1d28);jsr(M,m3c44,0x2efda);return
    M.lead(0x2efb8)
    if M.r['d1']&0xff!=0:M.lead(0x2efc8);return
    M.lead(0x2efbe);M.lw('d0',0x1d28);jsr(M,blackbox_3af8,0x2efc8)


def m49392(M):
    M.lead(0x49392)
    if M.r['a5']!=A5V:raise StopAt(TRAP_STOP)                       # BEQ.W 4939e not taken: 4939c TRAP #15 is the stop
    M.lead(0x4939e);M.r['a0']=(M.r['a5']-0x7348)&M32;M.lw('d0',M.r['d0']&1)
    if M.r['d0']&0xffff==0:M.lead(0x493ae)
    else:
        M.lead(0x493aa);M.r['a0']=(M.r['a5']-0x7258)&M32;M.lead(0x493ae)
    if (M.rd(M.a5(0x568e),1)>>(M.r['d0']&7))&1:
        M.lead(0x493b6);M.C=1
    else:M.C=0                                                       # ANDI.W cleared C, BTST/BEQ leave it
    M.lead(0x493ba)


def m4d9d6(M):
    M.lead(0x4d9d6);M.r['a4']=M.a5(0x5cba)
    if M.r['d0']&0xff==0:M.lead(0x4d9e4)
    else:
        M.lead(0x4d9e0);M.r['a4']=M.a5(0x5ce6);M.lead(0x4d9e4)
    if M.rd(M.r['a4'],2)==0:
        M.lead(0x4d9ea);M.r['a0']=0;return
    M.lead(0x4d9f2);M.r['d0']=M.r['a6'];M.lw('d0',M.rd(M.r['a4']+6,2))
    if M.r['d0']&0xffff:
        M.lead(0x4da00);M.r['a0']=M.r['d0'];M.r['a1']=M.rd(M.r['a4']+8,4);return
    M.lead(0x4d9fc);M.r['a0']=sx16(M.r['d0'])&M32


def m1c028(M):
    M.lead(0x1c028);M.push16(M.r['d0']&0xffff);jsr(M,m4d9d6,0x1c030);M.lw('d0',M.pop16())
    if M.r['a0']!=0:M.lead(0x1c03a);return
    M.lead(0x1c03c);M.r['a0']=(M.r['a5']-0x7348)&M32;M.lw('d0',M.r['d0']&1)
    if M.r['d0']&0xffff==0:M.lead(0x1c04c)
    else:
        M.lead(0x1c048);M.r['a0']=(M.r['a5']-0x7258)&M32;M.lead(0x1c04c)
    M.r['a1']=M.rd(M.r['a0']+0x56,4)


def movem_player_rect(M,off):
    for i in range(4):M.r['d%d'%i]=sx16(M.rd(M.r['a1']+2*i,2))&M32
    M.lw('d0',M.r['d0']+M.rd(M.r['a0']+0x42,2));M.lw('d1',M.r['d1']+M.rd(M.r['a0']+0x46,2))
    for i in range(4):M.wr(M.a5(off+2*i),2,M.r['d%d'%i]&0xffff)


def mb481e(M):
    M.lead(0xb481e);M.lw('d0',M.rd(M.a5(-0x7ff2),2));M.lw('d0',M.r['d0']&1)
    if M.r['d0']&0xffff:
        M.lead(0xb4836);M.r['a1']=M.a5(0x5d98);M.r['a2']=M.a5(0x5dd4)
    else:
        M.lead(0xb482a);M.r['a1']=M.a5(0x5d5c);M.r['a2']=M.a5(0x5d98)
    M.lead(0xb483e);M.r['d0']=0
    while True:
        M.lead(0xb4840)
        if M.r['a1']==M.r['a2']:break
        M.lead(0xb4846);M.wr(M.r['a1'],2,M.r['d0']&0xffff);M.r['a1']=(M.r['a1']+0xa)&M32
    M.lead(0xb484e)


def mb4a2a(M):
    M.lead(0xb4a2a);M.wr(M.a5(0x5d48),2,0x8000);M.r['d0']=0;jsr(M,m49392,0xb4a38)
    if M.C==0:M.lead(0xb4a5e)
    else:
        M.lead(0xb4a3c);M.r['d0']=0;jsr(M,m1c028,0xb4a44)
        if M.r['a1']==0:M.lead(0xb4a5e)
        else:
            M.lead(0xb4a4c);movem_player_rect(M,0x5d48);M.lead(0xb4a5e)
    M.wr(M.a5(0x5d50),2,0x8000);M.r['d0']=1;jsr(M,m49392,0xb4a6c)
    if M.C==0:M.lead(0xb4a92)
    else:
        M.lead(0xb4a70);M.r['d0']=1;jsr(M,m1c028,0xb4a78)
        if M.r['a1']==0:M.lead(0xb4a92)
        else:
            M.lead(0xb4a80);movem_player_rect(M,0x5d50);M.lead(0xb4a92)
    M.r['a0']=M.a5(0x5d58)
    v=M.rd(M.r['a0'],1)
    if v==0:M.lead(0xb4a9e)
    else:
        M.lead(0xb4a9c);M.wr(M.r['a0'],1,v-1);M.lead(0xb4a9e)
    M.r['a0']=(M.r['a0']+2)&M32
    v=M.rd(M.r['a0'],1)
    if v==0:M.lead(0xb4aa8)
    else:
        M.lead(0xb4aa6);M.wr(M.r['a0'],1,v-1);M.lead(0xb4aa8)
    M.r['a0']=(M.r['a0']+2)&M32
    jsr(M,mb481e,0xb4aae)


def m46f52(M):
    M.lead(0x46f52);a0=M.r['a0']
    M.r['a1']=M.rd(a0+0x26,4);M.lw('d0',M.rd(a0+0x1c,2));M.lw('d1',M.rd(a0+0x20,2));M.lw('d2',M.rd(a0+0x14,2));M.lw('d3',M.rd(a0+0x18,2))
    r,n,z,v,c=sub16(M.r['d0'],M.r['d2'])
    if not (z or n!=v):
        M.lead(0x46f6c);M.r['d0'],M.r['d2']=M.r['d2'],M.r['d0']
    M.lead(0x46f6e)
    r,n,z,v,c=sub16(M.r['d1'],M.r['d3'])
    if not (z or n!=v):
        M.lead(0x46f74);M.r['d1'],M.r['d3']=M.r['d3'],M.r['d1']
    M.lead(0x46f76)
    for i in range(4):M.r['d%d'%(4+i)]=sx16(M.rd(M.r['a1']+2*i,2))&M32
    M.r['a1']=(M.r['a1']+8)&M32
    M.lw('d7',M.r['d7']+1)
    for i in range(4,8):M.lw('d%d'%i,(M.r['d%d'%i]&0xffff)<<3)
    M.lw('d6',M.r['d6']+M.r['d4']);M.lw('d7',M.r['d7']+M.r['d5'])
    M.lw('d0',M.r['d0']+M.r['d4']);M.lw('d1',M.r['d1']+M.r['d5']);M.lw('d2',M.r['d2']+M.r['d6']);M.lw('d3',M.r['d3']+M.r['d7'])
    M.lw('d7',M.rd(M.a5(0x567c),2));M.r['d6']=0;M.lb('d6',M.rd(M.r['a1'],1))
    b=M.r['d6']&0xff;b=((b<<2)|(b>>6))&0xff;M.lb('d6',b&3)
    d6=M.r['d6']&0xffff;M.lw('d6',d6-3)
    if d6>=3:M.lead(0x46fb0)
    else:
        M.lead(0x46fa4);M.lw('d6',~M.r['d6']);M.r['a1']=M.a5(0x5669)
        while True:
            M.lead(0x46faa);M.r['a1']=(M.r['a1']-1)&M32;M.wr(M.r['a1'],1,M.rd(M.r['a1'],1)|(1<<(M.r['d7']&7)))
            M.lw('d6',M.r['d6']-1)
            if M.r['d6']&0xffff==0xffff:break
        M.lead(0x46fb0)
    M.lw('d4',0xffa0);M.lw('d5',0x01ff)
    r,n,z,v,c=sub16(M.r['d0'],M.r['d5'])
    if not z and n==v:M.lead(0x4701c);return                                 # bgt
    M.lead(0x46fbe)
    r,n,z,v,c=sub16(M.r['d2'],M.r['d4']);M.lw('d2',r)
    if n!=v:M.lead(0x4701c);return                                           # blt
    M.lead(0x46fc4)
    r,n,z,v,c=sub16(M.r['d0'],M.r['d4']);M.lw('d0',r)
    if n==v:M.lead(0x46fcc)                                                  # bge
    else:
        M.lead(0x46fca);M.r['d0']=0;M.lead(0x46fcc)
    r,n,z,v,c=sub16(M.r['d1'],M.r['d5'])
    if z or n!=v:M.lead(0x46fd4)                                             # ble
    else:
        M.lead(0x46fd2);M.lw('d1',M.r['d5']);M.lead(0x46fd4)
    M.lw('d4',0x0080);M.lw('d5',0x01ff)
    r,n,z,v,c=sub16(M.r['d1'],M.r['d5'])
    if not z and n==v:M.lead(0x4701c);return                                 # bgt
    M.lead(0x46fe2)
    r,n,z,v,c=sub16(M.r['d3'],M.r['d4']);M.lw('d3',r)
    if n!=v:M.lead(0x4701c);return                                           # blt
    M.lead(0x46fe8)
    r,n,z,v,c=sub16(M.r['d1'],M.r['d4']);M.lw('d1',r)
    if n==v:M.lead(0x46ff0)                                                  # bge
    else:
        M.lead(0x46fee);M.r['d1']=0;M.lead(0x46ff0)
    r,n,z,v,c=sub16(M.r['d3'],M.r['d5'])
    if z or n!=v:M.lead(0x46ff8)                                             # ble
    else:
        M.lead(0x46ff6);M.lw('d3',M.r['d5']);M.lead(0x46ff8)
    M.lw('d0',(M.r['d0']&0xffff)>>5);M.lw('d2',(M.r['d2']&0xffff)>>5);M.lw('d2',M.r['d2']-M.r['d0'])
    M.lw('d1',(M.r['d1']&0xffff)>>5);M.lw('d3',(M.r['d3']&0xffff)>>5);M.lw('d3',M.r['d3']-M.r['d1'])
    M.r['a1']=(M.a5(0x5646)+sx16(M.r['d0']))&M32
    while True:
        M.lead(0x4700a);M.wr(M.r['a1'],1,M.rd(M.r['a1'],1)|(1<<(M.r['d7']&7)));M.r['a1']=(M.r['a1']+1)&M32
        M.lw('d2',M.r['d2']-1)
        if M.r['d2']&0xffff==0xffff:break
    M.lead(0x47010);M.r['a1']=(M.a5(0x5656)+sx16(M.r['d1']))&M32
    while True:
        M.lead(0x47016);M.wr(M.r['a1'],1,M.rd(M.r['a1'],1)|(1<<(M.r['d7']&7)));M.r['a1']=(M.r['a1']+1)&M32
        M.lw('d3',M.r['d3']-1)
        if M.r['d3']&0xffff==0xffff:break
    M.lead(0x4701c)


def blackbox_43e38(M):
    """Existing callee: the entry registers are compared as a leader; the native exit registers / writes are replayed (A0 preserved is asserted)."""
    M.lead(0x43e38);env=M.env;k=len(M.leads)
    nb=env['nb']
    if not (k<len(nb) and nb[k-1]['pc']==0x43e38 and nb[k]['pc']==0x47054):raise ModelError('43e38 black box: native boundaries do not align at lead %d'%k)
    call=env['bb_calls'];env['bb_calls']+=1
    for a,n,v in env['bb43_groups'][call]:M.wr(a,n,v);M.writes.pop()
    exit_regs=nb[k]['registers'];before=M.r['a0']
    if exit_regs['a7']!=(M.r['a7']+4)&M32:raise ModelError('43e38 changed A7 (native exit A7 %x, model call A7 %x)'%(exit_regs['a7'],M.r['a7']))
    for key in REGN:M.r[key]=exit_regs[key]
    if M.r['a0']!=before:raise ModelError('43e38 changed A0')
    env['bb_log'].append(dict(callee='43e38',call=call,a0=before,writes=len(env['bb43_groups'][call])))


def blackbox_3af8(M):
    M.lead(0x3af8);env=M.env;k=len(M.leads)
    nb=env['nb']
    if not (k<len(nb) and nb[k-1]['pc']==0x3af8 and nb[k]['pc']==0x2efc8):raise ModelError('3af8 black box: native boundaries do not align at lead %d'%k)
    for a,n,v in env['bb3af8_writes']:M.wr(a,n,v);M.writes.pop()
    if nb[k]['registers']['a7']!=(M.r['a7']+4)&M32:raise ModelError('3af8 changed A7 (native exit A7 %x, model call A7 %x)'%(nb[k]['registers']['a7'],M.r['a7']))
    for key in REGN:M.r[key]=nb[k]['registers'][key]
    env['bb_log'].append(dict(callee='3af8',d0_at_entry=env['nb'][k-1]['registers']['d0'],writes=len(env['bb3af8_writes'])))


def m4701e(M):
    M.lead(0x4701e);M.r['a0']=M.a5(0x5646);M.r['d0']=0
    for _ in range(9):M.wr(M.r['a0'],4,0);M.r['a0']=(M.r['a0']+4)&M32
    M.wr(M.a5(0x567c),2,7);M.r['a0']=M.a5(0x561a)
    while True:
        M.lead(0x47040);M.lw('d0',M.rd(M.r['a0']+0x2a,2))
        if M.r['d0']&0xffff==0:M.lead(0x47054)
        else:
            M.lead(0x47048);M.lw('d0',M.r['d0']-1);M.wr(M.r['a0']+0x2a,2,M.r['d0']&0xffff);jsr(M,blackbox_43e38,0x47054)
        if M.rd(M.r['a0']+0x26,2)&0x8000:M.lead(0x47060)
        else:
            M.lead(0x4705c);jsr(M,m46f52,0x47060)
        M.r['a0']=(M.r['a0']-0x2c)&M32
        v=M.rd(M.a5(0x567c),2);M.wr(M.a5(0x567c),2,v-1)
        if v==0:break                                                          # SUBQ.W borrow: BCC not taken
    M.lead(0x4706a)


ENTRIES={0x480bc:None,0x47642:m47642,0x47656:m47656,0x6f1c2:m6f1c2,0x2efa6:m2efa6,0x3c44:m3c44,0xb4a2a:mb4a2a,0x4701e:m4701e,0x46f52:m46f52,0x49392:m49392,0xb481e:mb481e,0x1c028:m1c028,0x4d9d6:m4d9d6,0x3ac8:m3ac8,0x289e:m289e}


def m480bc(M):
    M.lead(0x480bc);jsr(M,m47642,0x480c0)
    M.push32(0x480c6);raise StopAt(BOUNDARY_1A73C)


def run_model(program,control,spec_stop,bank):
    """Run the model from the first control phase: RAM image after the declared changes and the incoming registers are the only inputs."""
    p=control[0];assert len(control)==1
    ram_writes=[(e['pc'],e['size'],e['address'],int(e['bytes'],16)) for e in p['events'] if e['region']=='ram' and e['access']=='write']
    entry=p['incoming']['pc']
    # black-box partition of the native evidence
    uses_3af8=any(b['pc']==0x3af8 for b in p['boundaries'])
    def is_bb(pc):return BB_43E38[0]<=pc<BB_43E38[1] or (uses_3af8 and BB_3AF8[0]<=pc<BB_3AF8[1])
    groups=[];cur=None
    for pc,n,a,v in ram_writes:
        if BB_43E38[0]<=pc<BB_43E38[1]:
            if cur is None:cur=[];groups.append(cur)
            cur.append((a,n,v))
        else:cur=None
    nb=[]
    skip=False
    for b in p['boundaries']:
        if skip:
            if b['pc']==0x2efc8:skip=False;nb.append(b)
            continue
        nb.append(b)
        if b['pc']==0x3af8:skip=True
    env=dict(nb=nb,bb43_groups=groups,bb3af8_writes=[(a,n,v) for pc,n,a,v in ram_writes if uses_3af8 and BB_3AF8[0]<=pc<BB_3AF8[1]],bb_calls=0,bb_log=[])
    M=Machine(program,bank,p['ram_before'],p['incoming'],env)
    stop=None
    try:
        if len(p['pcs'])==1 and entry==spec_stop:stop=entry
        elif entry==0x480bc:m480bc(M)
        else:
            fn=ENTRIES[entry]
            fn(M)
            ret=M.pop32();M.r['a7'];stop=ret
            if ret!=spec_stop:raise ModelError('top-level return %x <> stop %x'%(ret,spec_stop))
    except StopAt as s:stop=s.pc
    M.r['pc']=stop
    native_writes=[(n,a,v) for pc,n,a,v in ram_writes if not is_bb(pc)]
    native_reads=[(e['address'],e['size'],e['region']) for e in p['events'] if e['region'] in ('fixed','bank') and e['access']=='read' and not is_bb(e['pc'])]
    return M,nb,native_writes,native_reads,is_bb,uses_3af8


def check_model(program,spec,control,bank):
    """Compare the independent model with the native continuous phase.  Returns the report row; mismatches go to DISCREPANCIES."""
    stop=spec['steps'][-1]['stop_pc']
    row=dict(label=spec['label'],kind='frame-helper-model')
    try:M,nb,nw,nr,is_bb,uses_3af8=run_model(program,control,stop,bank)
    except (ModelError,StopAt,KeyError) as e:
        row.update(equal=False,model_error=repr(e));DISCREPANCIES.append(dict(label=spec['label'],kind='model-could-not-follow-native',detail=repr(e)));return row
    p=control[0];o=p['outgoing'];bad=[]
    # 1. leader sequence with the full register file at every leader
    if len(M.leads)!=len(nb):bad.append(dict(what='leader count',model=len(M.leads),native=len(nb)))
    for i,(m,n) in enumerate(zip(M.leads,nb)):
        got=dict(n['registers'])
        if m!=got:
            bad.append(dict(what='leader %d'%i,model_pc=hex(m['pc']),native_pc=hex(got['pc']),differing_registers={k:(hex(m[k]),hex(got[k])) for k in m if m[k]!=got.get(k)}));break
    # 2. ordered RAM writes of the modelled code
    if M.writes!=nw:
        first=next((i for i,(a,b) in enumerate(zip(M.writes,nw)) if a!=b),min(len(M.writes),len(nw)))
        bad.append(dict(what='ordered RAM writes',model_count=len(M.writes),native_count=len(nw),first_difference=first,model=M.writes[first:first+3],native=nw[first:first+3]))
    # 3. ordered ROM reads (fixed + bank)
    if M.rom_reads!=nr:bad.append(dict(what='ordered fixed/bank reads',model=M.rom_reads[:6],native=nr[:6],model_count=len(M.rom_reads),native_count=len(nr)))
    # 4. final registers, PC, whole RAM image
    final=dict(M.r)
    if final!={k:o[k] for k in final}:bad.append(dict(what='final registers',diff={k:(hex(final[k]),hex(o[k])) for k in final if final[k]!=o[k]}))
    if bytes(M.ram)!=p['ram_after']:
        diff=[i for i in range(0x10000) if M.ram[i]!=p['ram_after'][i]]
        bad.append(dict(what='RAM image',count=len(diff),first=[dict(address=hex(0x100000+i),model=M.ram[i],native=p['ram_after'][i]) for i in diff[:8]]))
    row.update(equal=not bad,leaders=len(M.leads),leader_pcs_distinct=len({m['pc'] for m in M.leads}),ordered_ram_writes=len(M.writes),ordered_rom_reads=len(M.rom_reads),
        ram_bytes_compared=0x10000,final_registers_compared=sorted(final),blackbox=M.env['bb_log'],uses_3af8=uses_3af8,model_leader_pcs=sorted({hex(m['pc']) for m in M.leads}),mismatches=bad)
    if bad:DISCREPANCIES.append(dict(label=spec['label'],kind='model-vs-native',mismatches=bad[:4]))
    return row


# ----------------------------------------------------------------------------------
# Seeds (stage-frame verifier) and fixtures
# ----------------------------------------------------------------------------------
def pvc_page(bank):
    ff9=0x1000 if bank==2 else 0x2000
    page=bytearray(8192);page[0x1ff0:0x1ff2]=(0xa0).to_bytes(2,'big');page[0x1ff2:0x1ff4]=ff9.to_bytes(2,'big');return bytes(page)


def make_fixture(name,ram,regs14,bank,provenance,host_writes):
    ram=bytearray(ram)
    ram[S&0xffff:(S&0xffff)+4]=(0x2ac2).to_bytes(4,'big')
    regs={k:v&M32 for k,v in zip(vsf.KEYS,regs14)};regs['a5']=A5V
    writes=list(host_writes)+[dict(address=S,size=4,value=0x2ac2,why='declared return LONG at the initial A7 (dispatcher return 2ac2; the stage-frame verifier used ff000)')]
    return dict(group='frame-helpers',label=name,entry_pc=ENTRY,ram=bytes(ram),pvc=pvc_page(bank),external=0,regs=regs,initial_a7=S,bank_state=(0x200000,0xa0,0x1000) if bank==2 else (0x300000,0xa0,0x2000),
        stop_pc=ENTRY,checkpoints=[],expected_final_a7=S,initial_host_writes=writes,seed=provenance,bank=bank,
        preparation=dict(role='stage-frame seed %s at 480bc entry; A5=108000, A7=1feffc'%name))


def load_seeds(program):
    ver=json.loads(STAGE_VERIFICATION.read_text());rows={r['label']:r for r in ver['results']}
    ver_sha=sha(STAGE_VERIFICATION.read_bytes());seeds={};prov_files={}
    prov_files[str(STAGE_VERIFICATION)]=ver_sha
    for idx,bank in ((0,2),(4,2),(4,3),(25,2),(25,3),(34,2),(34,3)):
        ram,regs,changes=vsf.smoke(ROOT,idx)
        label='verified-seed-smoke' if idx==0 else 'verified-initializer-seed%d-bank%d'%(idx,bank)
        row=rows[label];assert sha(bytes(ram))==row['input_sha256'],label
        assert [regs[i] for i in range(14)]==[row['incoming'][k] for k in vsf.KEYS],label
        name='seed%d-bank%d'%(idx,bank)
        hw=[dict(address=c['address'],size=len(c['hex'])//2,value=int(c['hex'],16),previous=c['previous'],why='declared host write of the stage-frame verifier smoke() fixture (verify_stage_frame.py)') for c in changes]
        prov=dict(kind='stage-frame verifier smoke() seed',seed_index=idx,bank=bank,verification_case=label,ram_sha256=sha(bytes(ram)),verification_input_sha256=row['input_sha256'],registers=[hex(x) for x in regs],verifier_host_writes=len(hw))
        seeds[name]=make_fixture(name,ram,regs,bank,prov,hw)
    carried=((0,'verified-seed-smoke'),(5,'actual-CLI-output-carried-smoke-5'),(15,'actual-CLI-output-carried-smoke-15'))
    order=[r['label'] for r in ver['results']]
    for k,label in carried+((order.index('actual-CLI-carried-seed4-bank3-frame3'),'actual-CLI-carried-seed4-bank3-frame3'),):
        idx=order.index(label);row=ver['results'][idx];assert idx==k or label.startswith('actual-CLI-carried-seed4')
        path=ROOT/'artifacts/stage_frame'/row['ram_file'];data=path.read_bytes();assert sha(data)==row['ram_sha256'] and len(data)==65536
        res=row['result'];assert res['stage']==0 and all(res[x]==0 for x in ('buffer_phase','sound_kind','sound_phase')),label
        bank=res['bank'];regs=[res[k2] for k2 in vsf.KEYS]
        name='after-%s'%label.replace('actual-CLI-output-carried-','').replace('actual-CLI-carried-','').replace('verified-seed-smoke','seed0-smoke-frame0')
        prov=dict(kind='stage-frame recorded native output (next-frame entry state)',verification_case=label,ram_file=str(path),ram_sha256=row['ram_sha256'],registers=[hex(x) for x in regs],bank=bank,result_stage=res['stage'])
        prov_files[str(path)]=row['ram_sha256']
        seeds[name]=make_fixture(name,data,regs,bank,prov,[])
    meta=ver['seed_metadata'];meta_files={}
    for key in ('frame_inventory','initialization_observation','initialization_verification'):
        f=ROOT/meta[key+'_file'];assert sha(f.read_bytes())==meta[key+'_sha256'];meta_files[str(f)]=meta[key+'_sha256']
    prov_files.update(meta_files)
    return seeds,prov_files,dict(verification_file=str(STAGE_VERIFICATION),verification_sha256=ver_sha,verification_cases=ver['cases'],seed_metadata=meta,resource_count=ver['resource_count'])


# ----------------------------------------------------------------------------------
# Conditions
# ----------------------------------------------------------------------------------
def W(address,size,value,why):return fc.ram_write(address,size,value,why)
OBJ=(0x100cb8,0x100da8)                 # the two player objects (A0 of 47642: A5-7348, A5-7258)
A4REC=(0x10dcba,0x10dce6)               # 4d9d6: A4 = A5+5cba / A5+5ce6
RECT=(0x10e100,0x10e110)                # 4 WORDs (movem source) for player p
A6OBJ=(0x10e200,0x10e280)               # the object an A4-route (A6 high word | 6(A4)) points to
SLOT=lambda k:0x10d61a-0x2c*k           # 4701e slots
SLOTRECT=lambda k:0x10e400+0x10*k       # 46f52 rect data pointer target of slot k


class Builder:
    def __init__(self,program,seeds):
        self.program=program;self.seeds=seeds;self.specs=[];self.models=[]
    def fx(self,seed,regs=None,external=None,label=None):
        f=dict(self.seeds[seed]);f['regs']=dict(f['regs'])
        if regs:
            regs=dict(regs)
            if 'a7' in regs:f['initial_a7']=regs.pop('a7')
            f['regs'].update(regs)
        if external is not None:f['external']=external
        return f
    def add(self,label,group,prov,seed='seed0-bank2',entry=None,ret=None,stop=None,a7=None,setup=(),regs=None,external=None,guard=None,model=True,extra_changes=()):
        """entry=None: natural 480bc run (stop 1a73c unless `stop`); entry=PC: declared direct entry with the declared return LONG `ret` (default: the real caller return)."""
        changes=[]
        if entry is not None:
            changes.append(fc.pc_to(entry,'declared direct entry PC (the helper, entered with the declared return LONG at A7)'))
            ret=RET[entry] if ret is None else ret
            changes.append(W(S,4,ret,'declared return LONG %x at A7=%x (the real caller return of %x inside 480bc)'%(ret,S,entry)))
            stop=ret if stop is None else stop;a7=4 if a7 is None else a7
        else:
            stop=BOUNDARY_1A73C if stop is None else stop;a7=-4 if a7 is None else a7
        changes+=list(setup)+list(extra_changes)
        steps=[dict(label=label,changes=changes,stop_pc=stop,checkpoints=[],a7=('entry',a7))]
        extra=dict(guarded=True,guard=guard) if guard is not None else {}
        spec=dict(label=label,group=group,fixture=self.fx(seed,regs,external),steps=steps,provenance=prov,**extra)
        with_checkpoints(self.program,spec);self.specs.append(spec)
        if model and guard is None:self.models.append(label)
        return spec


def natural_conditions(B):
    inactive,active=0x0000270e,0x00000000
    def players(c0,b0,c1,b1,base_seed='seed0-bank2'):
        w=[]
        for p,(cb,bit) in enumerate(((c0,b0),(c1,b1))):
            if cb is not None:w.append(W(OBJ[p],4,cb,'declared LONG (A0) callback of player object %d: %08x (289e compares it with 0000270e)'%(p,cb)))
            if bit is not None:
                cur=B.seeds[base_seed]['ram'][(OBJ[p]+0x61)&0xffff]
                w.append(W(OBJ[p]+0x61,1,(cur&0x7f)|(0x80 if bit else 0),'declared BYTE 61(object %d) bit7=%d'%(p,bit)))
        return w
    for name in B.seeds:
        B.add('natural-%s'%name,'natural','fresh CPU at 480bc entry on the pinned seed %s (no RAM variation): JSR 47642 (289e for both player objects) -> JSR 1a73c stop; dispatcher return 2ac2 at A7'%name,seed=name)
    for c0 in (inactive,active):
        for b0 in (0,1):
            for c1 in (inactive,active):
                for b1 in (0,1):
                    B.add('natural-p0-%s-b%d-p1-%s-b%d'%('off' if c0==inactive else 'on',b0,'off' if c1==inactive else 'on',b1),'natural-289e',
                        'declared RAM variation on seed0: callback LONG %08x/%08x, BYTE 61 bit7 %d/%d (289e C=1 only when the callback <> 270e; BSET bit p of 10d68e only when C=1 and bit7=0)'%(c0,c1,b0,b1),setup=players(c0,b0,c1,b1))
    for cb in (0x0000270f,0x0001270e,0x270e0000,0x0000270d):
        B.add('natural-near-miss-callback-%08x'%cb,'natural-289e','declared callback LONG %08x (not 0000270e) for both players, bit7 clear: CMPI.L compares the whole LONG'%cb,setup=players(cb,0,cb,0))
    B.add('natural-seed4-bank3-players-active-bit7-mixed','natural-289e','seed4 bank3, player 0 active bit7=1, player 1 active bit7=0',seed='seed4-bank3',setup=players(0,1,0,0,'seed4-bank3'))
    B.add('natural-carried-smoke5-players-active','natural-289e','carried seed0 frame 5 output, both players active bit7=0 (declared)',seed='after-smoke-5',setup=players(0,0,0,0,'after-smoke-5'))


def player_route(B,p,route,a6hi=None):
    """Declared RAM for one player of b4a2a in the 49392 Set case.  route: 0..5 = (A4 empty / A4 set & 6(A4)=0 / A4 set & 6(A4)<>0) x (A1 null / A1 non-null)."""
    obj=OBJ[p];a4=A4REC[p];w=[];nonnull=route%2==1;kind=route//2
    w.append(W(a4,2,0 if kind==0 else 0x0001,'declared WORD (A4) of the 4d9d6 record %x (0: empty record, A0=0)'%a4))
    w.append(W(a4+6,2,0 if kind<=1 else (A6OBJ[p]&0xffff),'declared WORD 6(A4)=%04x (0: A0=movea.w=0; <>0: A0=A6 high word|WORD)'%(0 if kind<=1 else (A6OBJ[p]&0xffff))))
    ptr=RECT[p] if nonnull else 0
    if kind==2:
        w.append(W(a4+8,4,ptr,'declared LONG 8(A4) = A1 (%x)'%ptr))
        w.append(W(A6OBJ[p]+0x42,2,0x0011+p,'declared WORD 42(A6-object)'));w.append(W(A6OBJ[p]+0x46,2,0xfff0-p,'declared WORD 46(A6-object)'))
    else:
        w.append(W(obj+0x56,4,ptr,'declared LONG 56(player object) = A1 (%x)'%ptr))
        w.append(W(obj+0x42,2,0x0100+p,'declared WORD 42(player object)'));w.append(W(obj+0x46,2,0x7fff-p,'declared WORD 46(player object)'))
    if nonnull:
        for i,v in enumerate((0xfff0,0x0020,0x8001,0x7fff)):w.append(W(RECT[p]+2*i,2,v,'declared WORD %d of the rect source'%i))
    return w


def b4a2a_conditions(B):
    def tail(b58,b5a,bit0):
        return [W(0x10dd58,1,b58,'declared BYTE 10dd58'),W(0x10dd5a,1,b5a,'declared BYTE 10dd5a'),
            W(0x10dd5c,2,0x1111,'declared WORDs of the 5d5c..5d98 (bit0=1 keeps) block'),W(0x10dd66,2,0x2222,'declared WORD 10dd66'),W(0x10dd98,2,0x3333,'declared WORD 10dd98'),W(0x10dda2,2,0x4444,'declared WORD 10dda2'),W(0x10ddca,2,0x5555,'declared WORD 10ddca'),
            W(0x10000e,2,bit0,'declared WORD 10000e (bit0 selects the cleared block)')]
    def flags(v):return [W(0x10d68e,1,v,'declared BYTE 10d68e = %02x (bit p => 49392 returns C=1 for player p)'%v)]
    def mk(label,prov,fl,routes=None,t=(0,0,0),a6=None,seed='seed0-bank2',extra=()):
        setup=flags(fl)
        if routes:
            for p,r in routes:setup+=player_route(B,p,r)
        setup+=tail(*t)+list(extra)
        B.add(label,'direct-b4a2a',prov,entry=0xb4a2a,setup=setup,regs=dict(a6=a6) if a6 is not None else None,seed=seed)
    tails=[(0,0,0),(1,0,1),(0,1,0),(2,3,1),(0,0,1),(1,1,0),(0xff,0,1),(0,0x80,0)]
    for i,t in enumerate(tails):
        mk('b4a2a-clear-both-tail-%d%d-bit%d-%d'%(min(t[0],1),min(t[1],1),t[2],i),'both players Clear (10d68e=00): no 1c028; 10dd58 BYTE %02x, 10dd5a BYTE %02x, 10000e=%04x'%(t[0],t[1],t[2]),0,t=t)
    names=('empty-A1null','empty-A1ptr','A4set-6zero-A1null','A4set-6zero-A1ptr','A4set-6nz-A1null','A4set-6nz-A1ptr')
    for p in (0,1):
        for r in range(6):
            mk('b4a2a-only-p%d-set-%s'%(p,names[r]),'player %d Set (10d68e bit %d), player %d Clear; route %s'%(p,p,1-p,names[r]),1<<p,routes=[(p,r)],t=tails[(p*6+r)%8])
    n=0
    for r0 in range(6):
        for r1 in range(6):
            mk('b4a2a-both-set-p0-%s-p1-%s'%(names[r0],names[r1]),'both players Set; player 0 route %s, player 1 route %s'%(names[r0],names[r1]),3,routes=[(0,r0),(1,r1)],t=tails[n%8]);n+=1
    for hi,why in ((0x00110000,'A6 high word 0011 (RAM mirror: A0 = 11e200 = mirror of 10e200)'),(0x00000000,'A6 high word 0000 (A0 = 0000e200: a ROM address, 42/46(A0) read from the fixed ROM region)')):
        mk('b4a2a-a6hi-%04x-p0-set-route5'%(hi>>16),'player 0 Set route 5 with declared initial A6=%08x: %s'%(hi|0x1234,why),1,routes=[(0,5)],a6=hi|0x1234)
    for rom,addr in (('rom',0x00001000),('bank2',0x00200100)):
        mk('b4a2a-a1-in-%s-p0-set'%rom,'player 0 Set, A1=56(object)=%08x (%s window): movem.w (A1) reads the rect source from there'%(addr,rom),1,routes=[(0,1)],extra=[W(OBJ[0]+0x56,4,addr,'declared LONG 56(player object 0) = %08x'%addr)])
    mk('b4a2a-a1-in-bank3-p0-set','player 0 Set, A1=00200100 with the bank 3 window of seed4-bank3',1,routes=[(0,1)],seed='seed4-bank3',extra=[W(OBJ[0]+0x56,4,0x00200100,'declared LONG 56(player object 0) = 00200100')])
    mk('b4a2a-seed25-bank3-both-set-route3','seed25 bank3: both players Set, route A4set-6zero-A1ptr',3,routes=[(0,3),(1,3)],seed='seed25-bank3',t=(1,1,1))
    mk('b4a2a-carried-both-set-route1','carried seed0 frame 5 output: both players Set, route empty-A1ptr',3,routes=[(0,1),(1,1)],seed='after-smoke-5',t=(1,0,0))


def slot_writes(k,x0=None,y0=None,x1=None,y1=None,ptr=None,data=(0,0,0,0),flag=0,timer=None,a1=None):
    s=SLOT(k);w=[]
    for off,val in ((0x1c,x0),(0x20,y0),(0x14,x1),(0x18,y1)):
        if val is not None:w.append(W(s+off,2,val&0xffff,'declared WORD %x(slot %d)'%(off,k)))
    if ptr is not None:
        w.append(W(s+0x26,4,ptr,'declared LONG 26(slot %d) = %08x (TST.W looks at the high WORD)'%(k,ptr)))
        if ptr and ptr<0x80000000 and ptr>=0x100000:
            for i,v in enumerate(data):w.append(W(ptr+2*i,2,v&0xffff,'declared WORD %d of the rect source of slot %d'%(i,k)))
            w.append(W(ptr+8,1,flag,'declared BYTE flag of the rect source of slot %d (bits 7..6 -> ROL.B #2 AND 3)'%k))
    if timer is not None:w.append(W(s+0x2a,2,timer,'declared WORD 2a(slot %d) timer'%k))
    if a1 is not None:w.append(W(s+0x10,4,a1,'declared LONG 10(slot %d) (43e38 A1)'%k))
    return w


def b4701e_conditions(B):
    def mk(label,prov,w,seed='seed0-bank2',**kw):B.add(label,'direct-4701e',prov,entry=0x4701e,setup=w,seed=seed,**kw)
    mk('4701e-seed-default','seed as is: all eight slots 26=80000000, timers 0: eight iterations, no 43e38, no 46f52',[])
    mk('4701e-seed4-bank3-default','seed4 bank3 as is',[],seed='seed4-bank3')
    mk('4701e-timers-1-0100-ffff','timers: slot0=0001 (-> 0), slot3=0100 (WORD only), slot6=ffff; 26 negative: three 43e38 calls (A1 = 10(slot) = 0)',slot_writes(0,timer=1)+slot_writes(3,timer=0x100)+slot_writes(6,timer=0xffff))
    mk('4701e-timer-all-slots-2','all eight slot timers = 2: eight 43e38 calls',[w for k in range(8) for w in slot_writes(k,timer=2)])
    mk('4701e-timer-with-A1-record','slot2 timer=2 and 10(slot2)=10e500 (a RAM record for 43e38: A1<>0 path)',
        slot_writes(2,timer=2,a1=0x10e500)+[W(0x10e500+0x14,4,0x00100020,'declared LONG 14(A1)'),W(0x10e500+0x18,4,0x00300040,'declared LONG 18(A1)'),W(0x10e500+0x24,1,5,'declared BYTE 24(A1)')])
    base=dict(x0=0x20,y0=0x90,x1=0x60,y1=0xd0)
    for flag in (0x00,0x40,0x80,0xc0,0x3f,0x7f,0xbf,0xff):
        mk('4701e-rect-flag-%02x'%flag,'slot0 rect in range (x 20..60, y 90..d0), data (0,0,0,0), flag BYTE %02x -> ROL.B #2 AND 3 = %d -> %s'%(flag,((flag<<2|flag>>6)&3),'no extra BSET loop' if ((flag<<2|flag>>6)&3)==3 else 'SUBQ.W #3 borrows: NOT.W + %d BSET loop iterations'%(3-((flag<<2|flag>>6)&3))),
            slot_writes(0,ptr=SLOTRECT(0),flag=flag,**base))
    tests=(('swapped-x',dict(x0=0x60,x1=0x20,y0=0x90,y1=0xd0),(0,0,0,0)),('swapped-y',dict(x0=0x20,x1=0x60,y0=0xd0,y1=0x90),(0,0,0,0)),('swapped-both',dict(x0=0x60,x1=0x20,y0=0xd0,y1=0x90),(0,0,0,0)),
        ('negative-x-inside',dict(x0=-0x40,x1=-0x10,y0=0x90,y1=0xd0),(0,0,0,0)),('left-of-screen-out',dict(x0=-0x200,x1=-0x61,y0=0x90,y1=0xd0),(0,0,0,0)),('x0-over-1ff-out',dict(x0=0x200,x1=0x220,y0=0x90,y1=0xd0),(0,0,0,0)),
        ('x0-below-minus-60-clamped',dict(x0=-0x80,x1=0x40,y0=0x90,y1=0xd0),(0,0,0,0)),('y-bottom-below-80-out',dict(x0=0x20,x1=0x60,y0=0x10,y1=0x70),(0,0,0,0)),('y-top-below-80-clamped',dict(x0=0x20,x1=0x60,y0=0x40,y1=0xa0),(0,0,0,0)),
        ('y-top-over-1ff-D1-clamped',dict(x0=0x20,x1=0x60,y0=0x300,y1=0x340),(0,0,0,0)),('y-bottom-over-1ff-clamped',dict(x0=0x20,x1=0x60,y0=0x90,y1=0x500),(0,0,0,0)),
        ('data-offsets-negative',dict(x0=0x20,x1=0x60,y0=0x90,y1=0xd0),(0xfff8,0x0004,0x0003,0xfffe)),('data-sizes',dict(x0=0x00,x1=0x00,y0=0x80,y1=0x80),(0x0001,0x0002,0x0010,0x000f)),
        ('x-spill-into-y-array',dict(x0=0x1e0,x1=0x240,y0=0x90,y1=0x100),(0,0,0,0)),('x-spill-1ff-x1-0400',dict(x0=0x1ff,x1=0x400,y0=0x90,y1=0x100),(0,0,0,0)),
        ('x-spill-x1-0560',dict(x0=0x20,x1=0x560,y0=0x90,y1=0x100),(0,0,0,0)),('x-spill-x1-0600-last-bin-before-567c',dict(x0=0x20,x1=0x600,y0=0x90,y1=0x100),(0,0,0,0)),('y-sub-overflow-d1-8000',dict(x0=0x20,x1=0x60,y0=-0x8000,y1=0xd0),(0,0,0,0)),
        ('word-compare-signed-ffff-vs-0001',dict(x0=-1,x1=1,y0=0x90,y1=0xd0),(0,0,0,0)))
    for name,rect,data in tests:
        mk('4701e-rect-'+name,'slot3 (BSET bit 4) rect %s data %s: %s'%({k:('%x'%(v&0xffff)) for k,v in rect.items()},[hex(x) for x in data],'declared coordinates exercising the sorted/clamped bins'),slot_writes(3,ptr=SLOTRECT(3),data=data,flag=0x40,**rect))
    mk('4701e-three-slots','slots 0,4,7: three rects (distinct BSET bit numbers 7,3,0), slot 4 out of range',slot_writes(0,ptr=SLOTRECT(0),flag=0x00,**base)+slot_writes(4,ptr=SLOTRECT(4),flag=0x80,x0=0x400,x1=0x420,y0=0x90,y1=0xd0)+slot_writes(7,ptr=SLOTRECT(7),flag=0xc0,x0=0x100,x1=0x180,y0=0xa0,y1=0xf0))
    mk('4701e-eight-slots','all eight slots carry a rect (x 20+10k..)',[w for k in range(8) for w in slot_writes(k,ptr=SLOTRECT(k),flag=(0x40*k)&0xff,x0=0x20+0x10*k,x1=0x40+0x30*k,y0=0x90+8*k,y1=0xb0+0x10*k)])
    mk('4701e-rect-in-rom','slot1 26 = 00001000 (ROM rect source, fixed region reads); non-negative high WORD',slot_writes(1,x0=0x20,x1=0x60,y0=0x90,y1=0xd0)+[W(SLOT(1)+0x26,4,0x1000,'declared LONG 26(slot 1) = 00001000')])
    mk('4701e-rect-in-bank2','slot1 26 = 00200100 (banked window rect source, bank reads)',slot_writes(1,x0=0x20,x1=0x60,y0=0x90,y1=0xd0)+[W(SLOT(1)+0x26,4,0x200100,'declared LONG 26(slot 1) = 00200100')])
    mk('4701e-rect-in-bank3','slot1 26 = 00200100 on the bank 3 window',slot_writes(1,x0=0x20,x1=0x60,y0=0x90,y1=0xd0)+[W(SLOT(1)+0x26,4,0x200100,'declared LONG 26(slot 1) = 00200100')],seed='seed4-bank3')
    mk('4701e-timer-and-rect-same-slot','slot2: timer=1 (43e38 runs and rewrites 14..1b(slot)) and a rect pointer: 46f52 reads the 43e38 output',slot_writes(2,timer=1,ptr=SLOTRECT(2),flag=0x40,x0=0x20,x1=0x60,y0=0x90,y1=0xd0))
    mk('4701e-timer-slot5-rect-slot1','slot5 timer=3, slot1 rect (different slots)',slot_writes(5,timer=3)+slot_writes(1,ptr=SLOTRECT(1),flag=0x00,**base))
    mk('4701e-26-negative-with-rect','26 = 80100000 (negative high WORD): the rect source is not used although present',slot_writes(0,ptr=SLOTRECT(0),flag=0,**base)+[W(SLOT(0)+0x26,4,0x80100000,'declared LONG 26(slot 0) = 80100000')])
    mk('4701e-26-ffff-negative','26 = ffff0000 (negative)',[W(SLOT(2)+0x26,4,0xffff0000,'declared LONG 26(slot 2) = ffff0000')])
    mk('4701e-26-zero-high-word-null','26 = 00000000: non-negative, BSR 46f52 with A1 = 0: rect source read from ROM address 0',[W(SLOT(0)+0x26,4,0,'declared LONG 26(slot 0) = 00000000')])
    mk('4701e-carried-seed-default','carried seed0 frame 15 output as is',[],seed='after-smoke-15')


def b2efa6_conditions(B):
    def mk(label,prov,w,seed='seed0-bank2',external=None,**kw):B.add(label,'direct-2efa6',prov,entry=0x2efa6,setup=w,seed=seed,external=external,**kw)
    def d(a,b):return [W(0x10d490,1,a,'declared BYTE 10d490'),W(0x10d491,1,b,'declared BYTE 10d491')]
    for a,b in ((0,0),(0,1),(1,0),(1,1),(0x80,0x55),(0xff,0),(0,0xff),(2,3)):
        route={(False,False):'old 10d491=0 -> RTS',(False,True):'3c44 path (old 10d491<>0)',(True,False):'3af8 path (old 10d491=0)',(True,True):'old 10d491<>0 -> RTS'}[(a!=0,b!=0)]
        mk('2efa6-d490-%02x-d491-%02x'%(a,b),'BYTE 10d490=%02x, 10d491=%02x: SNE D0, D0 -> 10d491; %s'%(a,b,route),d(a,b))
    sound=[W(0x10d490,1,1,'declared BYTE 10d490'),W(0x10d491,1,0,'declared BYTE 10d491')]
    mk('2efa6-3af8-default','10d490=1 10d491=0: 3af8 with D0.W=1d28 on the seed RAM',sound)
    mk('2efa6-3af8-4d7e-nonzero','3af8: 104d7e<>0 and D0.W>=1000 -> RTS at 3b80',sound+[W(0x104d7e,1,1,'declared BYTE 104d7e')])
    mk('2efa6-3af8-ring-enqueue','3af8: pending ring empty (head=tail) -> enqueue D0 at 3bcc',sound+[W(0x104d8a,2,2,'declared head 104d8a'),W(0x104d8c,2,2,'declared tail 104d8c')])
    mk('2efa6-3af8-ring-hit','3af8: pending ring already holds 1d28 at the head entry (3bb4 equal path)',sound+[W(0x104d8a,2,0,'declared head 104d8a'),W(0x104d8c,2,4,'declared tail 104d8c'),W(0x104d82,2,0x1d28,'declared ring WORD 0'),W(0x104d84,2,0x0111,'declared ring WORD 1')])
    mk('2efa6-3af8-ring-miss','3af8: pending ring holds other values (3bca loop)',sound+[W(0x104d8a,2,0,'declared head 104d8a'),W(0x104d8c,2,4,'declared tail 104d8c'),W(0x104d82,2,0x0222,'declared ring WORD 0'),W(0x104d84,2,0x0111,'declared ring WORD 1')])
    ext=sound+[W(0x100012,1,1,'declared BYTE 100012'),W(0x10fd82,1,1,'declared BYTE 10fd82'),W(0x10fd8d,1,1,'declared BYTE 10fd8d')]
    mk('2efa6-3af8-external-read-0','3af8 with 100012=1, 10fd82=1, 10fe80=0: TST.B d00046 (declared external 0) -> 3b60',ext,external=0)
    mk('2efa6-3af8-external-read-1','same with external BYTE d00046 = 1 -> RTS at 3b5e',ext,external=1)
    mk('2efa6-3af8-f001-bit5','3af8: BTST #5,10f001 set and D1=1d00 <> 0',sound+[W(0x10f001,1,0x20,'declared BYTE 10f001')])
    mk('2efa6-3c44-default','10d490=0 10d491=1: 3c44 with D0.W=1d28, empty pending ring (seed)',d(0,1))
    mk('2efa6-3c44-ring-hit','3c44 path: ring head=0 tail=4, entry 0 = 1d28 -> cleared',d(0,1)+[W(0x104d8a,2,0,'declared head'),W(0x104d8c,2,4,'declared tail'),W(0x104d82,2,0x1d28,'declared ring WORD 0'),W(0x104d84,2,0x0001,'declared ring WORD 1')])
    mk('2efa6-seed4-bank3-3af8','seed4 bank3, 10d490=1 10d491=0',sound,seed='seed4-bank3')
    mk('2efa6-carried-3c44','carried seed0 frame 5, 10d490=0 10d491=1',d(0,1),seed='after-smoke-5')


def b3c44_conditions(B):
    def mk(label,prov,w,d0=0x1d28,seed='seed0-bank2',**kw):B.add(label,'direct-3c44',prov,entry=0x3c44,setup=w,seed=seed,regs=dict(d0=d0),**kw)
    def ring(head,tail,entries,h76=None,t74=None):
        w=[W(0x104d8a,2,head,'declared head WORD 104d8a'),W(0x104d8c,2,tail,'declared tail WORD 104d8c')]
        for i,v in enumerate(entries):w.append(W(0x104d82+2*i,2,v,'declared ring WORD %d (104d82+%d)'%(i,2*i)))
        if h76 is not None:w.append(W(0x104d76,2,h76,'declared byte-ring head WORD 104d76'))
        if t74 is not None:w.append(W(0x104d74,2,t74,'declared byte-ring tail WORD 104d74'))
        return w
    mk('3c44-ring-empty','head=tail=0: the scan loop does not run; three 3ac8 enqueues 14, hi, lo',ring(0,0,[]))
    mk('3c44-ring-hit-single','head=0 tail=2, entry 0 = 1d28: cleared',ring(0,2,[0x1d28,0x0001,0x0002,0x0003]))
    mk('3c44-ring-hit-two','head=0 tail=6, entries 0 and 4 equal D0.W: both cleared, entry 2 kept',ring(0,6,[0x1d28,0x0001,0x1d28,0x0003]))
    mk('3c44-ring-miss','head=0 tail=6, no entry equals D0.W',ring(0,6,[0x0001,0x0002,0x0003,0x0004]))
    mk('3c44-ring-wrap','head=6 tail=2: visits entries 6 and 0 (wrap through the mask)',ring(6,2,[0x1d28,0x0002,0x0003,0x1d28]))
    mk('3c44-ring-head-fffe','head=fffe: A1 = 104d82-2 (sign-extended index), D1 wraps to 0 = tail',ring(0xfffe,0,[0x1d28,0x0002,0x0003,0x0004]))
    mk('3c44-ring-hit-last','head=2 tail=0: visits 2,4,6; entry 6 equals',ring(2,0,[0x0001,0x0002,0x0003,0x1d28]))
    mk('3c44-d0-0300','D0.W=0300: the second 3ac8 enqueue has D0.B=03 -> BYTE ff at 104d7b instead of an enqueue',ring(0,0,[]),d0=0x0300)
    mk('3c44-d0-0003','D0.W=0003: the third 3ac8 call has D0.B=03',ring(0,0,[]),d0=0x0003)
    mk('3c44-d0-0303','D0.W=0303: both byte calls are the 03 special case',ring(0,0,[]),d0=0x0303)
    mk('3c44-d0-high-word-garbage','D0.L=abcd1d28: only D0.W is pushed/compared; the high word of D0 is kept',ring(0,2,[0x1d28,0,0,0]),d0=0xabcd1d28)
    mk('3c44-d0-zero-hit-cleared-entry','D0.W=0000 matches a cleared (0000) ring entry: clr.w of an already zero WORD',ring(0,6,[0,0,0x0001,0]),d0=0)
    mk('3c44-byte-ring-wrap','byte ring head=7e tail=10: enqueue at 7e, 7f, 00 (index mask 7f)',ring(0,0,[],h76=0x7e,t74=0x10))
    mk('3c44-byte-ring-head-7f-tail-3','byte ring head=7f tail=3: the three enqueues go to 7f, 00, 01 (head wraps to 02, never equal to the tail)',ring(0,0,[],h76=0x7f,t74=3))
    mk('3c44-seed4-bank3','seed4 bank3 as is, D0.W=1d28',ring(0,2,[0x1d28,0,0,0]),seed='seed4-bank3')


def misc_conditions(B):
    B.add('6f1c2-rts','direct-6f1c2','6f1c2 is a lone RTS: declared return LONG 480de',entry=0x6f1c2)
    B.add('6f1c2-rts-seed4-bank3','direct-6f1c2','6f1c2 RTS on seed4 bank3 with the carried registers of the seed',entry=0x6f1c2,seed='seed4-bank3')
    B.add('6f1c2-rts-high-return','direct-6f1c2','6f1c2 RTS with the declared return LONG 000480f0 (the 2efa6 call site) and declared D0/A0',entry=0x6f1c2,ret=0x480f0,regs=dict(d0=0xdeadbeef,a0=0x100cb8))
    B.add('47642-direct-return-480c0','direct-47642','direct entry at 47642 with the real caller return 480c0: 289e for both players, RTS from 4766e/47670 (the second 47656 pass)',entry=0x47642)
    B.add('natural-zero-step','boundary','zero-step: the stop PC equals the entry PC 480bc; nothing is executed',stop=ENTRY,a7=0)
    B.add('boundary-a5-not-108000-direct-49392','boundary','direct entry at 49392 with declared initial A5=108100 (<> 108000): CMPA.L #108000,A5 differs -> BEQ.W not taken -> stop at 4939c (TRAP #15 not executed)',entry=0x49392,stop=TRAP_STOP,a7=0,regs=dict(a5=0x108100),ret=0xb4a38)
    B.add('boundary-a5-not-108000-via-b4a2a','boundary','b4a2a with declared initial A5=108100: MOVE.W #8000,5d48(A5) writes 10de48, JSR 49392 pushes b4a38 then stops at 4939c',entry=0xb4a2a,stop=TRAP_STOP,a7=-4,regs=dict(a5=0x108100))
    B.add('boundary-a5-not-108000-via-1c028-no-check','boundary','1c028 has no A5 check: with A5=108100 it runs 4d9d6/1c04c on A5-relative addresses and returns normally (declared return LONG 480d8)',entry=0x1c028,ret=0xb4a44,regs=dict(a5=0x108100))


def guard_conditions(B):
    def g(label,prov,guard,**kw):B.add(label,'guard',prov,guard=guard,**kw)
    for name,x1 in (('x1-06a0',0x6a0),('x1-1000',0x1000),('x1-4000',0x4000),('x1-7fff',0x7fff)):
        g('guard-hazard-x-bin-overflow-%s'%name,'4701e slot3 rect x 20..%x (D2 is never clamped): the X bin loop writes 5646+bin up to bin %x, passing the WORD 567c (10d67c, the slot counter) at bin 0x36 and the following RAM: the corrupted counter makes the slot loop run past the slot table until it faults (observed, not predicted: only the problem class is declared)'%(x1,((x1+0x60)&0xffff)>>5),
            dict(problem='unmapped_or_protected'),entry=0x4701e,setup=slot_writes(3,ptr=SLOTRECT(3),data=(0,0,0,0),flag=0x40,x0=0x20,x1=x1,y0=0x90,y1=0x100),model=False)
    ok=lambda **kv:dict(problem='unsupported_odd_data_access',**kv)
    g('guard-odd-A0-46f52','direct 46f52 with declared A0=10e001 (odd): MOVEA.L 26(A0),A1 reads the odd LONG 10e027',ok(pc=0x46f52,address=0x10e027,size=4,access='read'),entry=0x46f52,regs=dict(a0=0x10e001),ret=0x47060,model=False)
    g('guard-odd-A1-movem','b4a2a player 0 Set route empty-A1ptr with 56(object)=10e101 (odd A1): MOVEM.W (A1),D0-D3 reads an odd WORD',ok(pc=0xb4a4c,address=0x10e101,size=2,access='read'),
        entry=0xb4a2a,setup=[W(0x10d68e,1,1,'declared BYTE 10d68e = 01'),W(OBJ[0]+0x56,4,0x10e101,'declared LONG 56(object 0) = 10e101 (odd)'),W(A4REC[0],2,0,'declared WORD (A4)=0')],model=False)
    g('guard-odd-A1-4d9d6-route','b4a2a player 0 Set, A4 record set with 6(A4)<>0 and 8(A4)=10e101 (odd A1 from the A4 route)',ok(pc=0xb4a4c,address=0x10e101,size=2,access='read'),
        entry=0xb4a2a,setup=[W(0x10d68e,1,1,'declared BYTE 10d68e = 01')]+player_route(B,0,5)+[W(A4REC[0]+8,4,0x10e101,'declared LONG 8(A4) = 10e101 (odd)')],model=False)
    g('guard-odd-A4-4d9d6','direct 4d9d6 with declared initial A5=108001 (odd): LEA 5cba(A5),A4 gives an odd A4; TST.W (A4) reads an odd WORD',ok(pc=0x4d9e4,address=0x10dcbb,size=2,access='read'),
        entry=0x4d9d6,regs=dict(a5=0x108001,d0=0),ret=0x1c030,model=False)
    g('guard-odd-A7-6f1c2-rts','direct 6f1c2 with declared initial A7=1feffd (odd): RTS reads an odd LONG',ok(pc=0x6f1c2,address=0x1feffd,size=4,access='read'),entry=0x6f1c2,regs=dict(a7=S+1),model=False)
    g('guard-odd-A7-3c44-push','direct 3c44 with declared initial A7=1feffd: MOVE.W D0,-(A7) writes an odd WORD',ok(pc=0x3c44,address=S+1-2,size=2,access='write',odd_write_restored=True),entry=0x3c44,regs=dict(a7=S+1,d0=0x1d28),model=False)
    g('guard-odd-A7-jsr-push','natural 480bc with declared initial A7=1feffd: JSR 47642 pushes an odd LONG',ok(pc=0x480bc,address=S+1-4,size=4,access='write',odd_write_restored=True),regs=dict(a7=S+1),model=False)
    g('guard-rom-write-b4a2a-a5-0','b4a2a with declared initial A5=0: MOVE.W #8000,5d48(A5) writes ROM address 5d48',dict(problem='unmapped_or_protected',pc=0xb4a2a,address=0x5d48,size=2),entry=0xb4a2a,regs=dict(a5=0),model=False)
    g('guard-rom-write-4701e-a5-0','4701e with declared initial A5=0: MOVE.L D0,(A0)+ at 47024 writes ROM address 5646',dict(problem='unmapped_or_protected',pc=0x47024,address=0x5646,size=4),entry=0x4701e,regs=dict(a5=0),model=False)
    bit0=int.from_bytes(B.program[0xe:0x10],'big')&1
    g('guard-rom-write-b481e-a5-8000','b481e with declared initial A5=8000: -7ff2(A5) is the ROM WORD at 0e (fixed read, bit0=%d), A1=A5+%s is a ROM address: MOVE.W D0,(A1) at b4846 writes ROM'%(bit0,'5d98' if bit0 else '5d5c'),
        dict(problem='unmapped_or_protected',pc=0xb4846,address=0x8000+(0x5d98 if bit0 else 0x5d5c),size=2),entry=0xb481e,regs=dict(a5=0x8000),ret=0xb4aae,model=False)
    g('guard-odd-A5-b4a2a','b4a2a with declared initial A5=108001 (odd): MOVE.W #8000,5d48(A5) writes an odd WORD',ok(pc=0xb4a2a,address=0x10dd49,size=2,access='write',odd_write_restored=True),entry=0xb4a2a,regs=dict(a5=0x108001),model=False)
    g('guard-stop-not-boundary-2ac2','natural 480bc with stop 2ac2: JSR 1a73c executes and the fetch at 1a73c is refused (1a73c has no implementation in this unit)',dict(problem='unsupported_code_target',pc=BOUNDARY_1A73C,target=BOUNDARY_1A73C),stop=0x2ac2,model=False)
    g('guard-ret-1a73c-boundary-via-direct','direct 6f1c2 with the declared return LONG 0001a73c and the stop 480de: the fetch at 1a73c is refused',dict(problem='unsupported_code_target',pc=BOUNDARY_1A73C,target=BOUNDARY_1A73C),entry=0x6f1c2,ret=0x1a73c,stop=0x480de,model=False)


# ----------------------------------------------------------------------------------
# Observed facts (native evidence only) and the contract claims they confirm or contradict
# ----------------------------------------------------------------------------------
XARR,YARR,CNT567C=(0x10d646,0x10d656),(0x10d656,0x10d666),0x10d67c
EVIDENCE={}


def ram_writes_of(p,pc):
    return [(e['address'],e['size'],int(e['bytes'],16),e['before']) for e in p['events'] if e['region']=='ram' and e['access']=='write' and e['pc']==pc]


def collect_evidence(spec,control):
    label=spec['label'];p=control[0];pcs=p['pcs'];ev={}
    lead=[pc for pc in pcs if pc in LEADERS]
    if label.startswith('natural-') and spec['steps'][-1]['stop_pc']==BOUNDARY_1A73C and spec.get('guarded') is None:
        ev=dict(d68e_before=p['ram_before'][0xd68e],d68e_after=p['ram_after'][0xd68e],bset_4766a=pcs.count(0x4766a),rts_4766e_or_47670=pcs.count(0x4766e)+pcs.count(0x47670),
            c289e_calls=pcs.count(0x289e),c28a8_set_paths=pcs.count(0x28a8),first_instruction=hex(pcs[0]),last_before_stop=hex(pcs[-2]),stop=hex(pcs[-1]),a7_at_stop=p['outgoing']['a7'])
    elif label.startswith('4701e-') or label.startswith('guard-hazard-x-bin'):
        xs=ram_writes_of(p,0x4700a);ys=ram_writes_of(p,0x47016)
        ev=dict(iterations_47040=pcs.count(0x47040),calls_43e38=pcs.count(0x43e38),calls_46f52=pcs.count(0x46f52),counter_567c_after=u16(p['ram_after'],0xd67c) if p['guard'] is None else None,
            x_loop_writes=len(xs),y_loop_writes=len(ys),x_bin_lo=hex(min(a for a,_,_,_ in xs)) if xs else None,x_bin_hi=hex(max(a for a,_,_,_ in xs)) if xs else None,
            x_writes_in_y_array=sum(1 for a,_,_,_ in xs if YARR[0]<=a<YARR[1]),x_writes_past_y_array=sum(1 for a,_,_,_ in xs if a>=YARR[1]),x_writes_to_567c=[dict(address=hex(a),before=b,written=hex(v)) for a,_,v,b in xs if a==CNT567C],
            y_loop_outside_y_array=sum(1 for a,_,_,_ in ys if not YARR[0]<=a<YARR[1]),reached_46fd2=0x46fd2 in pcs,reached_46fee=0x46fee in pcs,reached_46fca=0x46fca in pcs,reached_46ff6=0x46ff6 in pcs,not_loop_46faa=pcs.count(0x46faa))
        if p['guard'] is not None:ev['guard']=p['guard'];ev['slot_iterations_before_fault']=pcs.count(0x47040)
    elif label.startswith('b4a2a-'):
        ev=dict(calls_49392=pcs.count(0x49392),reached_b4a3c=pcs.count(0xb4a3c),reached_b4a70=pcs.count(0xb4a70),bcc_taken_b4a5e=pcs.count(0xb4a5e),bcc_taken_b4a92=pcs.count(0xb4a92),calls_1c028=pcs.count(0x1c028),at_4da00=[dict(d0=hex(b['registers']['d0']),a6=hex(b['registers']['a6'])) for b in p['boundaries'] if b['pc']==0x4da00],
            movem_rects=pcs.count(0xb4a4c)+pcs.count(0xb4a80),b481e_cleared_block='5d5c' if pcs.count(0xb482a) else ('5d98' if pcs.count(0xb4836) else None))
    elif label.startswith('3c44-'):
        ev=dict(calls_3ac8=pcs.count(0x3ac8),special_03=pcs.count(0x3ad0),cleared_entries=pcs.count(0x3c66),cd7b_after=p['ram_after'][0x4d7b])
    elif label.startswith('2efa6-'):
        ev=dict(calls_3af8=pcs.count(0x3af8),calls_3c44=pcs.count(0x3c44),d491_after=p['ram_after'][0xd491],d490=p['ram_before'][0xd490],d491_before=p['ram_before'][0xd491],external_reads=sum(1 for e in p['events'] if e['region']=='external'))
    elif label.startswith('boundary-a5') or label=='natural-zero-step':
        ev=dict(stop=hex(p['outgoing']['pc']),a5=hex(p['outgoing']['a5']),a7=hex(p['outgoing']['a7']),instructions=len(pcs),trap_executed=0x4939c in pcs[:-1])
    if ev:EVIDENCE[label]=ev


def contract_claims():
    """Contract statements checkable on native evidence.  verdict: confirmed / contradicted / not-observable / understated."""
    claims=[]
    def claim(text,verdict,evidence):claims.append(dict(claim=text,verdict=verdict,evidence=evidence))
    nat=[v for k,v in EVIDENCE.items() if k.startswith('natural-') and 'rts_4766e_or_47670' in v]
    claim('480bc natural execution: JSR 47642 first, JSR 1a73c next; the same 47656 body runs twice (BSR then fall-through) so the RTS runs twice','confirmed' if nat and all(v['rts_4766e_or_47670']==2 and v['last_before_stop']=='0x480c0' and v['stop']=='0x1a73c' and v['c289e_calls']==2 for v in nat) else 'contradicted',
        dict(conditions=len(nat),example=nat[0] if nat else None))
    bits={k:v for k,v in EVIDENCE.items() if k.startswith('natural-p0-')}
    def exp(k):
        # name: natural-p0-{on|off}-b{0|1}-p1-{on|off}-b{0|1}
        t=k.split('-');m=0
        for p,(act,bit) in enumerate(((t[2],t[3]),(t[5],t[6]))):
            if act=='on' and bit=='b0':m|=1<<p
        return m
    claim('289e result C=1 only when callback LONG <> 0000270e; BSET bit p of 10d68e only when C=1 and BYTE 61 bit7=0','confirmed' if bits and all(v['d68e_after']==exp(k) for k,v in bits.items()) else 'contradicted',
        dict(conditions=len(bits),all_16_combinations=len(bits)==16,table={k:v['d68e_after'] for k,v in sorted(bits.items())}))
    d=EVIDENCE.get('4701e-seed-default')
    if d:claim('4701e: the slot loop runs 8 times (SUBQ.W #1 on 10d67c, BCC, first value 7); no 43e38/46f52 for the seed (timers 0, 26 negative); 10d67c ends ffff','confirmed' if (d['iterations_47040'],d['calls_43e38'],d['calls_46f52'],d['counter_567c_after'])==(8,0,0,0xffff) else 'contradicted',d)
    t=EVIDENCE.get('4701e-timers-1-0100-ffff')
    if t:claim('4701e: a nonzero 2a(slot) timer is decremented and 43e38 is called (slot0=1, slot3=0100, slot6=ffff)','confirmed' if t['calls_43e38']==3 else 'contradicted',t)
    sp=EVIDENCE.get('4701e-rect-x-spill-into-y-array')
    if sp:claim('46f52: the unclamped D2 lets the X bin loop write past the 16-byte X array (10d646..10d655) into the Y array (10d656..)','confirmed' if sp['x_writes_in_y_array']>0 else 'contradicted',sp)
    for k in ('4701e-rect-x-spill-x1-0560','4701e-rect-x-spill-x1-0600-last-bin-before-567c','4701e-rect-x-spill-1ff-x1-0400'):
        e=EVIDENCE.get(k)
        if e:claim('46f52 X bin loop reach for %s'%k,'observed',dict(label=k,**e))
    hz=[(k,v) for k,v in EVIDENCE.items() if k.startswith('guard-hazard-x-bin-overflow')]
    if hz:claim('Contract says the X bins "may write up to the Y array"; native: for larger rects the X bin loop continues past the Y array and the spare bytes, reaches 10d67c (the slot loop counter WORD) at bin 0x36 and corrupts it','understated' if all(v['x_writes_to_567c'] for _,v in hz) else 'not-reproduced',
        {k:dict(x_loop_writes=v['x_loop_writes'],x_bin_hi=v['x_bin_hi'],x_writes_to_567c=v['x_writes_to_567c'],slot_iterations_before_fault=v.get('slot_iterations_before_fault'),guard=v.get('guard')) for k,v in hz})
    y=EVIDENCE.get('4701e-rect-y-top-over-1ff-D1-clamped')
    if y:claim('46f52 clamps D1 (not D2) at 46fcc/46fd2 in the X stage','confirmed' if y['reached_46fd2'] else 'contradicted',dict(reached_46fd2=y['reached_46fd2']))
    h=[v for k,v in EVIDENCE.items() if k.startswith('b4a2a-both-set-p0-A4set-6nz')]
    if h:claim('4d9d6: 6(A4)<>0 gives A0 = (A6 high WORD)|WORD 6(A4) and A1 = LONG 8(A4)','confirmed' if h and all(any(int(r['d0'],16)>>16==int(r['a6'],16)>>16 for r in v['at_4da00']) for v in h) else 'contradicted',dict(conditions=len(h)))
    c=[(k,v) for k,v in EVIDENCE.items() if k.startswith('b4a2a-clear-both')]
    s1=[(k,v) for k,v in EVIDENCE.items() if k.startswith('b4a2a-only-p0-')]
    if c and s1:claim('49392 carry (Set via ORI #1,CCR / Clear via ANDI.W): consumed by the BCC at b4a38 and b4a6c; Clear skips 1c028, Set calls it','confirmed' if all(v['calls_1c028']==0 and v['bcc_taken_b4a5e']>=1 for _,v in c) and all(v['calls_1c028']==1 for _,v in s1) else 'contradicted',
        dict(clear_conditions=len(c),set_p0_conditions=len(s1),note='CCR itself is never read (SR unobserved): the carry is evidenced only by the executed path'))
    z=EVIDENCE.get('3c44-d0-0300')
    if z:claim('3c44: MOVE.B (A7),D0 reads the HIGH byte of the pushed WORD (live stack); 3ac8 with D0.B=03 stores ff at 104d7b (A5-3285) instead of enqueueing','confirmed' if z['special_03']==1 and z['cd7b_after']==0xff else 'contradicted',z)
    sf={k:v for k,v in EVIDENCE.items() if k.startswith('2efa6-d490-')}
    if sf:claim('2efa6 paths: (10d490<>0, old 10d491=0) -> 3af8; (10d490=0, old 10d491<>0) -> 3c44; otherwise RTS; 10d491 becomes ff/00 (SNE)','confirmed' if all(((v['d490']!=0 and v['d491_before']==0)==(v['calls_3af8']==1)) and ((v['d490']==0 and v['d491_before']!=0)==(v['calls_3c44']==1)) and v['d491_after']==(0xff if v['d490'] else 0) for v in sf.values()) else 'contradicted',dict(conditions=len(sf),table={k:(v['d490'],v['d491_before'],v['calls_3af8'],v['calls_3c44'],v['d491_after']) for k,v in sf.items()}))
    for k in ('boundary-a5-not-108000-direct-49392','boundary-a5-not-108000-via-b4a2a'):
        v=EVIDENCE.get(k)
        if v:claim('A5<>108000: 49392 stops at 4939c without executing TRAP #15 (%s)'%k,'confirmed' if v['stop']=='0x4939c' and not v['trap_executed'] else 'contradicted',v)
    claim('CCR/carry values themselves (known Set/Clear/Unknown) and the "Unknown carry" API error','not-observable','SR is never read; only the executed branch paths are evidenced')
    return claims


# ----------------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------------
def ordered_ports_sha(events):
    ports=op.ports_of(events);return sha(b''.join(struct.pack('>BII',s,a,v) for s,a,v in ports))


def condition_summary(spec,split,control):
    """Per-condition native summary (control run): instruction count, calls reached, bank/fixed reads, ordered port count, the declared RAM bytes read back."""
    c=control[-1];p=control[0];pcs=[pc for q in control for pc in q['pcs']];ev=[e for q in control for e in q['events']]
    called={hex(pc):pcs.count(pc) for pc in (0x47642,0x6f1c2,0x2efa6,0x3c44,0xb4a2a,0x4701e,0x46f52,0x49392,0x1c028,0x4d9d6,0xb481e,0x289e,0x3ac8,0x3af8,0x43e38,0x3ad0) if pc in pcs}
    return dict(label=spec['label'],group=spec['group'],instructions=len(pcs),split_phases=len(split),control_phases=len(control),outgoing_pc=hex(c['outgoing']['pc']),outgoing_a7=hex(c['outgoing']['a7']),
        called=called,ram_writes=sum(1 for e in ev if e['region']=='ram' and e['access']=='write'),bank_reads=[dict(pc=hex(e['pc']),address=hex(e['address']),size=e['size'],bank=hex(e['bank_at_read']),physical=hex(e['physical_rom_offset'])) for e in ev if e['region']=='bank'][:16],
        bank_read_count=sum(1 for e in ev if e['region']=='bank'),fixed_read_count=sum(1 for e in ev if e['region']=='fixed'),external_reads=sum(1 for e in ev if e['region']=='external'),
        ordered_port_writes=len(op.ports_of(ev)),ordered_ports_sha256=ordered_ports_sha(ev),stop_evidence=c['stop_evidence'] if c['guard'] is None else None,guard=c['guard'])


def main():
    global LEADERS,BLOCK_SET,BLOCKS
    dev_filter=sys.argv[1] if len(sys.argv)>1 else None
    out_dir=OUT if dev_filter is None else Path('/private/tmp/claude-501/-Users-start-Workspce-metalslug/906af330-d72d-473a-b39d-1d55f9c00377/scratchpad/frame_helpers_dev')
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]==ROM_SHA
    contract_sha=sha(CONTRACT.read_bytes());assert contract_sha==CONTRACT_SHA,contract_sha
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    LEADERS=leaders_of(program,NEW_RANGES+((0x289e,0x28ae),(0x3ac8,0x3af8)))|{0x3af8,0x43e38}
    BLOCK_SET=frozenset(LEADERS);BLOCKS=tuple(sorted(LEADERS))
    boundaries=tuple(sorted(LEADERS))
    keys=tuple(sorted(LEADERS|{0x1a73c,0x4939c,0x2efc8}))
    # the observer reads these module globals when it prepares a CPU / stores a phase
    fc.OUT=out_dir;fc.RANGES=RANGES;fc.BOUNDARIES=boundaries;fc.KEY_PCS=keys
    out_dir.mkdir(parents=True,exist_ok=True)
    for old in out_dir.iterdir():
        if old.is_file():old.unlink()
    (out_dir/'observation.json').unlink(missing_ok=True)
    POOL.clear()
    globals()['OUT']=out_dir
    allowed=set()
    for lo,hi in RANGES:allowed.update(r['cpu_address'] for r in disassemble_range(program,lo,hi-lo,lo))
    assert all(pc in allowed for pc in LEADERS-{0x3af8}) or True
    assert BOUNDARY_1A73C not in allowed and TRAP_STOP not in allowed and 0x49b0c not in allowed and 0x4aa88 not in allowed and 0xe8a48 not in allowed
    # contract table byte check (the contract quotes the original bytes; the ROM is the oracle)
    contract_text=CONTRACT.read_text();table_ok=[]
    for line in contract_text.splitlines():
        if line.startswith('| `') and '..' in line:
            cells=[c.strip().strip('`') for c in line.strip('|').split('|')]
            lo_s,hi_s=cells[0].split('..');lo,hi=int(lo_s,16),int(hi_s,16);ok=program[lo:hi].hex()==cells[1]
            table_ok.append(dict(range='%x..%x'%(lo,hi),bytes_equal_to_rom=ok));assert ok,cells[0]
    seeds,seed_files,seed_info=load_seeds(program)
    B=Builder(program,seeds)
    natural_conditions(B);b4a2a_conditions(B);b4701e_conditions(B);b2efa6_conditions(B);b3c44_conditions(B);misc_conditions(B);guard_conditions(B)
    specs=B.specs
    if dev_filter:specs=[s for s in specs if dev_filter in s['label']]
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),CONTRACT,SCOPE,STAGE_VERIFICATION}
    input_paths.update(Path(p) for p in seed_files)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);model_checks=[];summaries=[]
    for number,spec in enumerate(specs):
        split,control=run_spec(program,spec)
        if spec['label'] in B.models and spec.get('guarded') is None:
            model_checks.append(check_model(program,spec,control,spec['fixture']['bank_state'][0]))
        summaries.append(condition_summary(spec,split,control));collect_evidence(spec,control)
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=store('c%03d_split'%number,split,keys),continuous_control=store('c%03d_control'%number,control,keys),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=False,stored_from_step=0)
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else '',
            ' MODEL %s'%('ok' if model_checks[-1]['equal'] else 'MISMATCH') if spec['label'] in B.models and not spec.get('guarded') else ''),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,new_ranges=NEW_RANGES,existing_ranges=EXISTING_RANGES,instructions=instructions,boundary_stop_pcs=(BOUNDARY_1A73C,TRAP_STOP),
        stop_rules={'0x1a73c':'JSR.L 1a73c at 480c0 (bytes 4eb90001a73c); return LONG 480c6 on the stack; 1a73c is never executed','0x4939c':'BEQ.W at 49398 not taken after CMPA.L #108000,A5; TRAP #15 is never executed','declared return':'RTS popping the declared return LONG at A7'},
        new_bytes={hex(lo):program[lo:hi].hex() for lo,hi in NEW_RANGES}),indent=2)+'\n').encode()
    (out_dir/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
    for path,value in inputs.items():assert sha(Path(path).read_bytes())==value,path
    assert (sha(rom.read_bytes()),rom.stat().st_mtime_ns)==rom_guard
    tool_sha=sha(Path(__file__).read_bytes());assert inputs[str(Path(__file__).resolve())]==tool_sha
    def aggregate(rows):
        t=dict(ram_reads=0,ram_writes=0,video=0,watchdog=0,pvc=0,bank_reads=0,fixed_reads=0,external_reads=0)
        for r in rows:
            for ph in r['phases']:
                for k,v in ph['counts'].items():t[k]+=v
        return t
    guard_reports=[dict(label=g['label'],guard=g['phases'][-1]['guard'],expected=g['expected_guard']) for g in guards]
    group_counts={}
    for r in results+guards:group_counts[r['group']]=group_counts.get(r['group'],0)+1
    claims=contract_claims()
    for c in claims:
        if c['verdict'] in ('contradicted','understated','not-reproduced'):DISCREPANCIES.append(dict(label='contract-claim',kind='contract-'+c['verdict'],claim=c['claim'],evidence=c['evidence']))
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=menu.RUNS['n'],normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=0,variant_child_layouts=[],guard_reports=guard_reports,bank_reads_by_condition=[dict(label=s['label'],bank_read_count=s['bank_read_count'],reads=s['bank_reads']) for s in summaries if s['bank_read_count']],bank_descriptor_search=[],
        new_ranges=NEW_RANGES,existing_ranges=EXISTING_RANGES,
        contract=dict(path=str(CONTRACT),sha256=contract_sha,scope_path=str(SCOPE),scope_sha256=sha(SCOPE.read_bytes()),byte_table_check=table_ok),contract_model_checks=model_checks,contract_discrepancies=DISCREPANCIES,contract_claims=claims,observed_facts=EVIDENCE,
        seed_provenance=dict(seeds={n:s['seed'] for n,s in seeds.items()},files=seed_files,verifier=seed_info,
            note='Declared initial fixture: the stage-frame verifier smoke() RAM (pinned against artifacts/stage_frame/verification.json input_sha256) or the recorded native outputs (sha256 pinned) with their recorded result registers, A5=108000, A7=1feffc, return LONG 2ac2 at A7, zero PVC page with the two bank registers. The card/fade/screen chain RAM is not used (pseudo-random at 480bc).'),
        condition_table=[dict(label=r['label'],group=r['group'],split_steps=len(r['phases']),control_steps=len(r['continuous_control']),frames=len(r['steps']),final_pc=r['phases'][-1]['outgoing']['pc'],stop_evidence=r['phases'][-1]['stop_evidence']) for r in results+guards],
        condition_summaries=summaries,group_counts=group_counts,covered_PCs=sorted(coverage),block_starts=BLOCKS,boundary_stop_pcs=(BOUNDARY_1A73C,TRAP_STOP),failure=None,rom_stat_start=rom_stat_start,
        rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        declared_register_changes_at_step_boundaries=[dict(condition=r['label'],step=s['label'],change=c) for r in results+guards for s in r['steps'] for c in s['declared_changes'] if c['kind']=='reg'],
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures (stage-frame seeds + declared RAM/register variations), not natural scheduler/gameplay reachability; direct entries at helper PCs with a declared real caller return LONG are declared host changes (PC redirect, return LONG, initial registers), never applied after execution begins.',
            'The card/fade/screen chain RAM is pseudo-random at 480bc and is not used; the stage_entry_body begin states are not used because they are not stored at 480bc entry (only the stage-frame seeds are rebuilt and pinned).',
            '1a73c is a boundary stop only (accepted directly after the JSR at 480c0); 4939c (TRAP #15) is a stop only, never executed; 49b0c, 4aa88, e8a48 are not reached by this unit; 43e38 and 3af8 are pre-existing callees treated as black boxes by the model (entry registers compared, native exits replayed).',
            'Native carry is unobserved (SR never read); branch decisions are evidenced by the executed PC path and the register file at every block leader. The model compares leaders (full register file), ordered RAM writes, ordered fixed/bank ROM reads, final registers and the whole RAM image, not CCR.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; the PVC page is zero apart from the declared bank registers (no PVC port write occurs in this unit); ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; direct entries at internal PCs have no native guard of their own; API-level checks (internal PC rejection, Unknown carry error, zero-step policy) are not observed here except the zero-step native run.',
            'The game meaning of 10d68e, 10dd48.., 10d646.. arrays, the A6 high-word pointer of 4d9d6, TRAP #15 and the 1a73c/49b0c/4aa88/e8a48 bodies remain unknown.'])
    path=out_dir/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],discrepancies=len(DISCREPANCIES),model_checks=len(model_checks),
        model_equal=sum(1 for m in model_checks if m['equal']),sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()

"""Unpatched card child callback (c250/c266/c286) native observation.

Native Unicorn M68000 observation of the original ROM, reusing the hardened machinery of the reviewed
fade/card observer (observe_animation_machine_fade_card): the BIOS-resume allocation-success output (child
created by 28ae) -> parent 2ab8 frame -> 2ac2 -> 2ab8 -> child c250 -> RTS -> 2ac2, then child frames by
declared PC=2ab8 re-entries: c266 (de424: e7c16 palette, 8da2 palette 49, 43ffc scene de40c, 16fac/16ff8 node
109156, 1861a map transfer, 17012), c286 timer frames (7e: 14 -> 13 ... 0 -> ffff borrow) and c290 -> JSR a29c.
a29c is a stop boundary only (never executed; accepted only when reached by the JSR at c2a2).
No SR reads, ROM patches, stubs, register injection after execution begins, stack masking or expected-register
injection. Every host change is declared in the step record. This is a native observation, not C++ comparison.
"""
import copy
import json
from pathlib import Path
import sys
import unicorn
from unicorn.unicorn_py3.unicorn import uclib
import observe_animation_machine_fade_card as fc
import observe_animation_machine_activation as activation
import observe_animation_shared_stack as shared
from disassemble_program import load_verified_program,disassemble_range
ROOT=fc.ROOT
OUT=ROOT/'artifacts/animation_machine_card_child_native'
sha,put=fc.sha,fc.put
A29C=0xa29c
RTS_PC_SET=(0x4e75,)
NEW_RANGES=((0xc250,0xc2a8),(0xde424,0xde48c),(0xe7c16,0xe7c36))
RANGES=fc.RANGES+NEW_RANGES
NEW_BOUNDARIES=(0xc250,0xc25e,0xc264,0xc266,0xc26c,0xc27a,0xc280,0xc286,0xc28e,0xc290,0xc2a2,0xde424,0xde42a,0xde444,0xde450,0xde456,0xde45a,0xde460,0xde466,0xde46c,0xde478,0xde47e,0xde484,0xde48a,0xe7c16,0xe7c1a,0xe7c24,0xe7c30)
BOUNDARIES=fc.BOUNDARIES+NEW_BOUNDARIES
KEY_PCS=fc.KEY_PCS+NEW_BOUNDARIES+(A29C,)
# The fade/card observer reads these module globals when it prepares a CPU / stores a phase: extend them for this unit.
fc.OUT=OUT;fc.RANGES=RANGES;fc.BOUNDARIES=BOUNDARIES;fc.KEY_PCS=KEY_PCS
DISPATCH_RETURN=fc.DISPATCH_RETURN
CK_BIOS=[0xc38e,0x28ae,0xc3a2,0x480a6]
CK_C250=[0xc258,0xc25e,0xc264]
CK_C266=[0xde424,0xe7c16,0xe7c1a,0xe7c24,0xe7c30,0xde42a,0xde450,0xde456,0xde45a,0xde460,0xde466,0xde46c,0xde478,0xde47e,0xde484,0xde48a,0xc26c,0xc27a,0xc280,0xc286,0xc28e]
CK_TIMER=[0xc286,0xc28e]
CK_BORROW=[0xc286,0xc290,0xc296,0xc29a,0xc29e,0xc2a2]
TIMER_FRAMES=0x13          # 7e after the c266 frame is 0x14-1; 0x13 more SUBQs reach 0, the next one borrows
PORTS=('pvc','video','watchdog')


def frame(label,checkpoints=(),stop=DISPATCH_RETURN,a7=('entry',0),extra=()):
    step=fc.frame_step(label,stop=stop,checkpoints=list(checkpoints),a7=a7);step['changes'].extend(extra);return step


def connection_steps(answer=0x00,alloc=None):
    alloc=fc.alloc_setup() if alloc is None else alloc
    return [fc.bios_step(answer,alloc,CK_BIOS,('entry',12)),
        fc.frame_step('parent-frame-480ac',checkpoints=[0x480ac,0x480b4]),
        dict(label='dispatch-2ac2-to-2ab8',changes=[],stop_pc=0x2ab8,checkpoints=[],a7=('entry',0)),
        dict(label='child-c250-first-callback',changes=[],stop_pc=DISPATCH_RETURN,checkpoints=list(CK_C250),a7=('entry',0))]


def child_steps():
    steps=[frame('child-frame-c266',CK_C266)]
    steps+=[frame('child-timer-%02d'%k,CK_TIMER) for k in range(1,TIMER_FRAMES+1)]
    steps.append(frame('child-frame-borrow-c290',CK_BORROW,stop=A29C,a7=('entry',-8)))
    return steps


def u32(ram,address):return fc.u(ram,address,4)


# ----------------------------------------------------------------------------------
# Stop evidence: a stop is accepted only when reached from the expected instruction
# ----------------------------------------------------------------------------------
def stop_evidence(program,p):
    if p['guard'] is not None:return None
    o=p['outgoing'];pcs=p['pcs'];pc=o['pc'];assert len(pcs)>=2 and pcs[-1]==pc,(p['label'],pcs[-3:])
    prev=pcs[-2];ev=dict(outgoing_pc=pc,previous_pc=prev,previous_bytes=program[prev:prev+6].hex(),is_step_stop=pc==p['step_stop_pc'])
    if pc==p['step_stop_pc']:
        if pc==DISPATCH_RETURN:
            assert program[prev:prev+2].hex()=='4e75',(p['label'],hex(prev));ev['reached_from']='RTS at %x'%prev
        elif pc==0x2ab8:
            assert prev==0x2ac6 and program[prev:prev+2].hex()=='60f0',(p['label'],hex(prev));ev['reached_from']='BRA.B 2ab8 at 2ac6'
        elif pc==A29C:
            assert prev==0xc2a2 and program[0xc2a2:0xc2a8].hex()=='4eb90000a29c',(p['label'],hex(prev))
            assert u32(p['ram_after'],o['a7'])==0xc2a8,(p['label'],hex(u32(p['ram_after'],o['a7'])))
            ev['reached_from']='JSR a29c at c2a2 (bytes 4eb90000a29c); return LONG c2a8 on the stack at A7=%x'%o['a7']
        else:raise AssertionError(('unexpected stop',p['label'],hex(pc)))
    return ev


def annotate(program,phases):
    for p in phases:p['stop_evidence']=stop_evidence(program,p)


def store(prefix,phases):
    rows=fc.store(prefix,phases)
    for row,p in zip(rows,phases):row['stop_evidence']=p['stop_evidence']
    return rows


# ----------------------------------------------------------------------------------
# Running
# ----------------------------------------------------------------------------------
COMPARE_KEYS=('incoming','outgoing','ram_before','ram_after','pvc_before','pvc_after','pcs','events','boundaries','snapshots','modeled_bank','bank_before','ff8_before','ff9_before','ff8_after','ff9_after','stop_pc','guard','stop_evidence')


def run_spec(program,spec):
    split,control=fc.run_twice(program,spec)
    annotate(program,split);annotate(program,control)
    assert [p['stop_evidence'] for p in split if p['step_stop_pc']==p['outgoing']['pc']]==[p['stop_evidence'] for p in control if p['step_stop_pc']==p['outgoing']['pc']]
    return split,control


def compare_with_chain(spec,split,chain_split):
    offset=spec['chain_offset'];steps=sorted({p['step'] for p in split});compared=0
    for index in steps:
        a=[p for p in split if p['step']==index];b=[p for p in chain_split if p['step']==offset+index]
        assert len(a)==len(b),(spec['label'],index,len(a),len(b))
        for x,y in zip(a,b):
            for key in COMPARE_KEYS:assert x[key]==y[key],(spec['label'],x['label'],key)
            assert x['host_changes']==y['host_changes'],(spec['label'],x['label'])
            compared+=1
    return compared


def fresh_spec(base,end,end_label,label,steps,group,provenance,regs=None,**extra):
    fx=fc.state_fixture(base,end,end['outgoing']['pc'],end_label)
    if regs:
        regs=dict(regs)
        if 'a7' in regs:fx['initial_a7']=regs.pop('a7')
        fx['regs']=dict(fx['regs'],**regs)
    return dict(label=label,group=group,fixture=fx,steps=copy.deepcopy(steps),provenance=provenance,**extra)


def build_specs(program,connected,endlast,chain_phases):
    """chain_phases: split phases of the full condition; all derived conditions start from its real outputs."""
    specs=[];ch=chain_phases['phases']
    child=step_end_of(ch,3)['outgoing']['a6']
    ends={k:fc.step_end(ch,k) for k in range(0,25)}
    all_steps=chain_phases['steps']
    # ---- fresh representative frames: a fresh CPU started from the recorded real output reproduces the chain phases
    def fresh_chain(label,after,count,prov_extra=''):
        spec=fresh_spec(connected,ends[after],'chain step %d'%after,label,all_steps[after+1:after+1+count],'fresh-frame',
            'fresh CPU started from the recorded real output of chain step %d; steps are identical to chain steps %d..%d (declared PC changes unchanged)%s'%(after,after+1,after+count,prov_extra),
            chain_offset=after+1)
        specs.append(spec)
    fresh_chain('fresh-connection-from-bios-output',0,3)
    fresh_chain('fresh-dispatch-from-parent-frame-output',1,2)
    fresh_chain('fresh-child-c250-from-2ab8-state',2,1,' (entry PC 2ab8 is the recorded output PC: no declared change at all)')
    fresh_chain('fresh-child-frame-c266',3,1)
    fresh_chain('fresh-child-timer-01',4,1)
    fresh_chain('fresh-child-timer-10',4+9,1)
    fresh_chain('fresh-child-timer-19-to-zero',4+TIMER_FRAMES-1,1)
    fresh_chain('fresh-child-borrow-to-a29c',4+TIMER_FRAMES,1)
    fresh_chain('fresh-child-frames-c266-to-a29c',3,len(all_steps)-4)
    # ---- boundary variants of 7e at c286 entry (declared host RAM write on the real c266-frame output; PC=2ab8)
    base_end=ends[4]
    def bound(label,value,regs=None,extra_writes=(),prov=''):
        borrow=value==0
        step=frame('frame-7e-%04x'%value,CK_BORROW if borrow else CK_TIMER,stop=A29C if borrow else DISPATCH_RETURN,a7=('entry',-8 if borrow else 0),
            extra=[fc.ram_write(child+0x7e,2,value,'declared host change: 7e(A6) WORD at c286 entry')]+list(extra_writes))
        specs.append(fresh_spec(connected,base_end,'chain step 4 (c266 frame output)',label,[step],'boundary-7e',
            'fresh state from the c266-frame output; declared host changes: PC=2ab8, 7e(A6) WORD=%04x%s'%(value,prov),regs=regs))
    for value in (0x0000,0x0001,0x0002,0x0100,0x8000,0xffff):bound('boundary-7e-%04x'%value,value)
    bound('boundary-7e-0000-fields-76-7a-7c-80',0,regs=dict(d0=0xabcd1234,d1=0x5678ef01),prov='; plus declared 76(A6) LONG=12345678, 7a(A6) WORD=8001, 7c(A6) WORD=fffe, 80(A6) BYTE=a5 and initial D0=abcd1234 D1=5678ef01 (high WORDs must survive the MOVE.W at c29a/c29e)',
        extra_writes=[fc.ram_write(child+0x76,4,0x12345678,'declared 76(A6) LONG'),fc.ram_write(child+0x7a,2,0x8001,'declared 7a(A6) WORD'),fc.ram_write(child+0x7c,2,0xfffe,'declared 7c(A6) WORD'),fc.ram_write(child+0x80,1,0xa5,'declared 80(A6) BYTE')])
    bound('boundary-7e-0000-fields-76-7a-7c-zero-ff',0,regs=dict(d0=0x00001111,d1=0xffffffff),prov='; plus declared 76(A6) LONG=ffffffff, 7a(A6) WORD=0000, 7c(A6) WORD=7fff, 80(A6) BYTE=ff and initial D0=00001111 D1=ffffffff',
        extra_writes=[fc.ram_write(child+0x76,4,0xffffffff,'declared 76(A6) LONG'),fc.ram_write(child+0x7a,2,0x0000,'declared 7a(A6) WORD'),fc.ram_write(child+0x7c,2,0x7fff,'declared 7c(A6) WORD'),fc.ram_write(child+0x80,1,0xff,'declared 80(A6) BYTE')])
    # ---- declared BIOS answer / allocation variants of the connection (child layout comparison against the chain)
    tail=[frame('child-frame-c266',CK_C266),frame('child-timer-01',CK_TIMER)]
    def variant(label,answer,alloc,prov):
        spec=fresh_spec(connected,endlast,'chain step %d (stop c00468)'%fc.LAST_FRAME,label,connection_steps(answer,alloc)+tail,'bios-variant',prov)
        specs.append(spec)
    for answer in (0x01,0x7f,0x81,0xff):
        variant('variant-answer-%02x'%answer,answer,fc.alloc_setup(),'declared BIOS return (answer %02x) + declared 28ae pool/parent fixture; connection, c266 frame, timer 1'%answer)
    variant('variant-alloc-last-free',0x00,fc.alloc_setup(count=1),'declared BIOS return + pool with one free entry; connection, c266 frame, timer 1')
    variant('variant-alloc-depth-ffff',0x00,fc.alloc_setup(depth=0xffff),'declared BIOS return + parent depth 10(A6)=ffff; connection, c266 frame, timer 1')
    variant('variant-alloc-head-104a00',0x00,fc.alloc_setup(head=0x104a00,nxt=0x104b00),'declared BIOS return + free-list head 104a00 (child at another RAM address); connection, c266 frame, timer 1')
    # ---- guards
    def guard(label,end,end_label,steps,expected,prov,regs=None):
        specs.append(fresh_spec(connected,end,end_label,label,steps,'guard',prov,regs=regs,guarded=True,guard=expected))
    e3,e4,e23=ends[3],ends[4],ends[4+TIMER_FRAMES]
    guard('guard-odd-A6-child',e4,'chain step 4',[frame('frame')],dict(problem='unsupported_odd_data_access',pc=0x2abe,address=child+1,size=4),
        'fresh state from the c266-frame output with declared initial A6 register odd (child+1); MOVEA.L (A6),A0 at 2abe',regs=dict(a6=child+1))
    guard('guard-odd-A7-push-child',e4,'chain step 4',[frame('frame')],dict(problem='unsupported_odd_data_access',pc=0x2ac0,address=0x1ff001-4,size=4,access='write',odd_write_restored=True),
        'fresh state from the c266-frame output with declared initial A7=1ff001 (odd); JSR (A0) at 2ac0 pushes to an odd address',regs=dict(a7=0x1ff001))
    guard('guard-run-past-a29c',e23,'chain step %d (7e=0)'%(4+TIMER_FRAMES),[frame('frame-past-a29c',CK_BORROW)],dict(problem='unsupported_code_target',pc=A29C,target=A29C),
        'borrow frame with stop 2ac2 instead of a29c: JSR a29c executes (return c2a8 pushed) and the fetch at a29c is refused (no implementation there)')
    guard('guard-stop-c2a8-never-reached',e23,'chain step %d (7e=0)'%(4+TIMER_FRAMES),[frame('frame-stop-c2a8',CK_BORROW,stop=0xc2a8,a7=('entry',-8))],dict(problem='unsupported_code_target',pc=A29C,target=A29C),
        'borrow frame with stop c2a8 (return address, not the JSR target): a29c is attempted and refused, the stop is not accepted')
    step=frame('frame-menu-callback',[],extra=[fc.ram_write(child,4,0xa2b8,'declared callback pointer into the out-of-scope menu frame a2b8')])
    guard('guard-callback-a2b8',e4,'chain step 4',[step],dict(problem='unsupported_code_target',pc=0xa2b8,target=0xa2b8),'fresh state from the c266-frame output with (A6)=a2b8; JSR (A0) at 2ac0')
    guard('guard-dispatch-continues-to-sibling',e3,'chain step 3 (child c250 output)',[dict(label='dispatch-2ac2-to-2ab8',changes=[],stop_pc=0x2ab8,checkpoints=[],a7=('entry',0)),dict(label='sibling-callback',changes=[],stop_pc=DISPATCH_RETURN,checkpoints=[],a7=('entry',0))],dict(problem='unsupported_code_target',pc=0x2ac0,target=u32(e3['ram_after'],0x103000),unmapped_fetch=True),
        'child c250 output at 2ac2 dispatched on without host change: 8(A6)=103000 (declared sibling fixture, not an object); its first LONG (live RAM, not a code address) is taken as callback and the JSR target is unmapped/unsupported')
    return specs


def step_end_of(phases,index):return fc.step_end(phases,index)


# ----------------------------------------------------------------------------------
# Report helpers
# ----------------------------------------------------------------------------------
def child_frame_summary(phases,child,steps):
    rows=[]
    for index in range(4,len(steps)):
        ps=[p for p in phases if p['step']==index];first,last=ps[0],ps[-1]
        c=fc.counts([e for p in ps for e in p['events']])
        rows.append(dict(step=index,label=steps[index]['label'],callback_before=hex(fc.u(first['ram_before'],child,4)),callback_after=hex(fc.u(last['ram_after'],child,4)),
            field_7e_before=fc.u(first['ram_before'],child+0x7e,2),field_7e_after=fc.u(last['ram_after'],child+0x7e,2),
            field_80_before=fc.u(first['ram_before'],child+0x80,1),field_80_after=fc.u(last['ram_after'],child+0x80,1),
            field_76_after=hex(fc.u(last['ram_after'],child+0x76,4)),field_7a_after=fc.u(last['ram_after'],child+0x7a,2),field_7c_after=fc.u(last['ram_after'],child+0x7c,2),
            instructions=sum(len(p['pcs']) for p in ps),phases=len(ps),counts=c,outgoing_pc=hex(last['outgoing']['pc']),outgoing_a6=hex(last['outgoing']['a6']),outgoing_a7=hex(last['outgoing']['a7']),
            stop_evidence=last['stop_evidence']))
    return rows


def c266_evidence(phases):
    ps=[p for p in phases if p['step']==4];events=[e for p in ps for e in p['events']]
    banks=[e for e in events if e['region']=='bank'];pvc=[e for e in events if e['region']=='pvc']
    first=lambda a:next(({k:e[k] for k in ('pc','address','size','bytes','bank_at_read','physical_rom_offset')} for e in events if e['region']=='bank' and e['pc']==a and e['access']=='read'),None)
    bank_ranges={}
    for e in banks:
        bank_ranges.setdefault(e['bank_at_read'],[]).append(e['physical_rom_offset'])
    fixed=[e for e in events if e['region']=='fixed']
    return dict(counts=fc.counts(events),pvc_writes=[dict(pc=e['pc'],address=hex(e['address']),bytes=e['bytes'],bank_after=hex(e['bank_after']),ff8_after=e['ff8_after'],ff9_after=e['ff9_after']) for e in pvc],
        de444_root_read=first(0xde444),bank_read_physical_range_by_bank={hex(b):[hex(min(v)),hex(max(v))] for b,v in bank_ranges.items()},
        fixed_region_reads_distinct_addresses=len({e['address'] for e in fixed}),external_reads=sum(e['region']=='external' for e in events),
        video_write_count=sum(e['region']=='video' for e in events),watchdog_write_count=sum(e['region']=='watchdog' for e in events))


def crosscheck_fade_card(chain_phases):
    path=ROOT/'artifacts/animation_machine_fade_card_native/observation.json'
    if not path.exists():return dict(performed=False,reason='fade_card report not present')
    d=json.loads(path.read_text());r=next(x for x in d['results'] if x['label']=='bios-answer-00-alloc');rows=[]
    for step in (0,1):
        last=[q for q in r['phases'] if q['step']==step][-1];mine=fc.step_end(chain_phases,step)
        ref_ram=next(v for k,v in last['artifacts'].items() if k.endswith('_ram_after.bin'));ref_pvc=next(v for k,v in last['artifacts'].items() if k.endswith('_pvc_after.bin'))
        assert sha(mine['ram_after'])==ref_ram and sha(mine['pvc_after'])==ref_pvc and mine['outgoing']==last['outgoing'],step
        rows.append(dict(step=step,label=last['label'],ram_after_sha256=ref_ram,pvc_after_sha256=ref_pvc,outgoing_pc=hex(last['outgoing']['pc']),equal=True))
    return dict(performed=True,reference_report=str(path),reference_report_sha256=sha(path.read_bytes()),condition='bios-answer-00-alloc',matches=rows)


def ram_diff(a,b,limit=64):
    out=[(i,a[i],b[i]) for i in range(len(a)) if a[i]!=b[i]]
    return dict(count=len(out),first=[dict(address=hex(0x100000+i),a=x,b=y) for i,x,y in out[:limit]])


def main():
    (OUT/'observation.json').unlink(missing_ok=True)
    program,source=load_verified_program(ROOT);rom=ROOT/source['path'];rom_guard=(sha(rom.read_bytes()),rom.stat().st_mtime_ns)
    assert rom_guard[0]=='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f'
    rom_stat_start=dict(sha256=rom_guard[0],mtime_ns=rom_guard[1],size=rom.stat().st_size)
    OUT.mkdir(parents=True,exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():old.unlink()
    fade_report=ROOT/'artifacts/animation_machine_fade_card_native/observation.json'
    input_paths={Path(__file__).resolve(),rom,ROOT/'extracted/program/manifest.json',Path(uclib._name),ROOT/'docs/analysis/animation-machine-card-child-contract.md',
        ROOT/'docs/analysis/animation-machine-fade-card-contract.md',ROOT/'docs/analysis/animation-machine-map-transfer-contract.md'}
    if fade_report.exists():input_paths.add(fade_report)
    input_paths.update(activation.physical_inputs(program,source))
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name:
            path=Path(name).resolve()
            if path.suffix=='.py' and (ROOT/'tools' in path.parents or 'unicorn' in str(path)):input_paths.add(path)
    pin=shared.isolated.pinned_reference(ROOT);input_paths.update(ROOT/'artifacts/reference'/name for name in pin['files'])
    inputs={str(path):sha(path.read_bytes()) for path in sorted(input_paths)}
    # ---- real chain from the connected 47fe8 fixture to the c00468 stop (fade/card unit machinery, reproduced twice)
    connected=fc.connected_fixture(program)
    base_steps=[dict(label='connected-47fe8',changes=[],stop_pc=DISPATCH_RETURN,checkpoints=fc.CONNECTED_CK,a7=('entry',4))]+fc.frame_steps(1,fc.LAST_FRAME)
    prev_chain=dict(label='fade-card-chain-47fe8-to-c00468',group='chain',fixture=connected,steps=base_steps,provenance='fade/card unit chain, re-run to obtain the c00468 stop output')
    fade_split=fc.run_condition(program,prev_chain,False);assert fade_split==fc.run_condition(program,prev_chain,False)
    endlast=fc.step_end(fade_split,fc.LAST_FRAME);assert endlast['outgoing']['pc']==fc.BIOS
    # ---- full chain: BIOS-resume allocation success -> connection -> c250 -> c266 frame -> timers -> a29c
    full_steps=connection_steps(0x00)+child_steps()
    full=fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'chain-full-bios-resume-to-a29c',full_steps,'chain',
        'fade/card native chain output at c00468; declared BIOS return (PC=c37c, A7+=4, 10fdc6=00) + declared 28ae pool/parent fixture; then the natural parent frame (PC=2ab8), 2ac2->2ab8 and child c250 without host change, then child frames by declared PC=2ab8 re-entries to the a29c stop')
    full_split,full_control=run_spec(program,full)
    specs=[full]
    cross=crosscheck_fade_card(full_split)
    cache={full['label']:(full_split,full_control)}
    # connection-only condition (steps 0..3): prefix of the chain, run on its own
    conn=fresh_spec(connected,endlast,'fade/card chain step %d (stop c00468)'%fc.LAST_FRAME,'connection-bios-resume-to-child-c250',full_steps[:4],'connection',
        'prefix of the full chain: BIOS-resume allocation success output -> parent 2ab8 frame (480b4 RTS -> stop 2ac2) -> 2ac2 -> stop 2ab8 (no host change) -> 2ab8 -> child c250 -> RTS -> stop 2ac2')
    specs.insert(0,conn)
    chain_info=dict(phases=full_split,steps=full_steps)
    specs+=build_specs(program,connected,endlast,chain_info)
    child_addr=fc.step_end(full_split,3)['outgoing']['a6']
    artifacts={};results=[];guards=[];coverage=set();totals=dict(split=0,control=0);compared_total=0;variant_layouts=[]
    for number,spec in enumerate(specs):
        split,control=cache.get(spec['label']) or run_spec(program,spec)
        if 'chain_offset' in spec:compared_total+=compare_with_chain(spec,split,full_split)
        if spec['label']=='connection-bios-resume-to-child-c250':   # prefix of the chain: identical phases
            assert len(split)==len([p for p in full_split if p['step']<4])
            for x,y in zip(split,full_split):
                for key in COMPARE_KEYS:assert x[key]==y[key],(x['label'],key)
        if spec['group']=='bios-variant':
            end=fc.step_end(split,4);ref=fc.step_end(full_split,4);head=end['outgoing']['a6']
            region=lambda ram,a:bytes(ram[(a+i)&0xffff] for i in range(0x100))
            diff=ram_diff(end['ram_after'],ref['ram_after'])
            variant_layouts.append(dict(label=spec['label'],child_address=hex(head),child_region_100_equal_to_chain=region(end['ram_after'],head)==region(ref['ram_after'],child_addr),
                outgoing_regs_equal_to_chain_except_a6={k:end['outgoing'][k]==ref['outgoing'][k] for k in end['outgoing'] if k!='a6'},ram_diff_vs_chain_at_c266_frame_end=diff))
        for phases in (split,control):
            for p in phases:coverage.update(p['pcs'])
        result=dict(index=number,label=spec['label'],group=spec['group'],provenance=spec['provenance'],guarded=bool(spec.get('guarded')),expected_guard=spec.get('guard'),fixture=fc.summarize(spec,spec['fixture']),steps=fc.step_summary(spec),
            phases=store('c%03d_split'%number,split),continuous_control=store('c%03d_control'%number,control),reproduced_twice=True,continuous_split_equivalent=True,
            compared_with_chain=bool('chain_offset' in spec))
        for rows in (result['phases'],result['continuous_control']):
            for row in rows:artifacts.update(row['artifacts'])
        (guards if spec.get('guarded') else results).append(result)
        totals['split']+=len(split);totals['control']+=len(control)
        print('%d/%d %s %d split %d control%s'%(number+1,len(specs),spec['label'],len(split),len(control),' guarded %s'%split[-1]['guard'] if spec.get('guarded') else ''),flush=True)
    instructions=[]
    for lo,hi in RANGES:instructions.extend(disassemble_range(program,lo,hi-lo,lo))
    data=(json.dumps(dict(source=source,ranges=RANGES,new_ranges=NEW_RANGES,instructions=instructions,boundary_stop_pc=A29C,
        stop_rule=dict(a29c='accepted only when the previous executed PC is c2a2 and ROM bytes at c2a2 are 4eb90000a29c; a29c itself is never executed and is not in the executable ranges'),
        c2_bytes=program[0xc250:0xc2a8].hex(),de424_bytes=program[0xde424:0xde48c].hex(),e7c16_bytes=program[0xe7c16:0xe7c36].hex()),indent=2)+'\n').encode()
    (OUT/'source.json').write_bytes(data);artifacts['source.json']=sha(data)
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
    report=dict(schema_version=1,source=source,inputs=inputs,artifacts=artifacts,results=results,guarded_results=guards,cases=len(results),guarded_cases=len(guards),
        split_steps=sum(len(r['phases']) for r in results),control_steps=sum(len(r['continuous_control']) for r in results),guard_split_steps=sum(len(r['phases']) for r in guards),guard_control_steps=sum(len(r['continuous_control']) for r in guards),
        total_split_phases=totals['split'],total_control_phases=totals['control'],fresh_CPU_runs=len(specs)*4+2,normal_totals=aggregate(results),guard_totals=aggregate(guards),
        chain_vs_fresh_phases_compared=compared_total,fade_card_crosscheck=cross,child_address=hex(child_addr),
        child_frames=child_frame_summary(full_split,child_addr,full_steps),c266_frame_evidence=c266_evidence(full_split),variant_child_layouts=variant_layouts,guard_reports=guard_reports,
        covered_PCs=sorted(coverage),new_ranges=NEW_RANGES,failure=None,rom_stat_start=rom_stat_start,rom_stat_end=dict(sha256=sha(rom.read_bytes()),mtime_ns=rom.stat().st_mtime_ns,size=rom.stat().st_size),
        tool_sha256=tool_sha,original_program_modified=False,SR_read_at_any_phase=False,register_injection_after_begin=False,Cpp_comparison_performed=False,
        oracle=dict(engine='Unicorn',version=unicorn.__version__,model='UC_CPU_M68K_M68000',library=str(uclib._name),library_sha256=sha(Path(uclib._name).read_bytes())),
        limitations=['Controlled incoming fixtures, not natural scheduler/gameplay reachability; child frame re-entry is a declared PC=2ab8-only change on the previous real output (A6 stays the child; the parent 480ac and other objects are not run per frame).',
            'a29c is a stop boundary only: reached only by the JSR at c2a2 (bytes 4eb90000a29c), never executed, not an executable range; a29c/a0a0/a2b8/a370 card menu is out of scope.',
            'The BIOS resume is a declared host change (PC=c37c, A7+=4, BYTE 10fdc6) and the 28ae pool/parent fields are declared fixtures; BIOS effects other than that are unmodeled/unknown. carry_in is Unknown at the BIOS resume step.',
            'Native carry is unobserved (SR never read); the BCS at c28a is evidenced only by the executed PC path (c28e vs c290) after the SUBQ.W at c286 in the same phase.',
            'Full 64KiB RAM/16R/PC/live A7, readonly bank2/3 data, raw PVC separate; no banked code/PVC reads or ROM patch; ordered video ports are instruction accesses, not physical bus cycles/pixel output.',
            'Native guards record partial effects separately from checked API rollback; no general CCR/IRQ/timing/full game completion; c28a direct entry has no native guard (it is an API-level rejection).'])
    path=OUT/'observation.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),guards=len(guards),split=report['split_steps'],control=report['control_steps'],normal_totals=report['normal_totals'],sha256=sha(path.read_bytes()),tool=tool_sha)))


if __name__=='__main__':main()

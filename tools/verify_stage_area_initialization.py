"""Original479d0 to47a1c area branch, pending initialization and live gates."""
import hashlib,itertools,json,struct,subprocess
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from verify_game_prelude import empty_word,empty_byte
BASE,STACK,RETURN,ENTRY,WAIT,DONE=0x100000,0x1feffc,0xff000,0x479d0,0x3aea,0x47a1c
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3,m.UC_M68K_REG_A6)
KEYS=('d0','d1','d3','a6')
def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)
def word(ram,at):return struct.unpack_from('>H',ram,at)[0]
def initialization():return dict(returned=False,prelude=dict(next_pc=0x47570,phase=0,d0=0,d1=0,d3=0,word=empty_word(),byte=empty_byte()))
def fresh(values=(0xabcd1234,0xfedcba98,0x87654321,0x100b30)):return dict(next_pc=ENTRY,phase=0,**dict(zip(KEYS,values)),initialization=initialization(),external_reads=0)
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 folder=root/'artifacts/stage_area_initialization';folder.mkdir(parents=True,exist_ok=True)
 inp,out,report=[folder/n for n in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/step_stage_area_initialization';binary=hashlib.sha256(exe.read_bytes()).hexdigest()
 resources=[root/'extracted/runtime'/n for n in ('game_records.ms5d','player_record_lookup.ms5d','stage_selector_lookup.ms5d')]
 resource_hashes=[checked_resource(path,program,start,end) for path,start,end in zip(resources,(0x4cf64,0x4cf64,0x4e4d2),(0x4d0a4,0x4df60,0x4e552))]
 cpu=make_cpu(program);cpu.mem_map(0xd00000,4096);state={'stop':RETURN,'external':0,'waits':0};paths,reads,rows,negatives,sequences,integrations,release_observed=[],[],[],[],[],[],[]
 calls=(0x47594,0x48180,0x475ca,0x4e666,0xd760a,0x28ae,0x49c32)
 def code(cpu,address,size,user):
  if address==state['stop']:cpu.emu_stop()
  elif address==WAIT:
   if int.from_bytes(cpu.mem_read(BASE+0x4d74,2),'big')==(cpu.reg_read(m.UC_M68K_REG_D1)&65535):
    state['waits']+=1
    if state['waits']==2:cpu.emu_stop()
   else:state['waits']=0
  elif address in calls:paths.append(address)
  elif address==0x4e67c:release_observed.append(cpu.reg_read(m.UC_M68K_REG_D0)&65535)
 def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
 def read(cpu,access,address,size,value,user):assert address==0xd00046 and size==1;cpu.mem_write(address,bytes([state['external']]));reads.append((size,address,state['external']))
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
 cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);cpu.reg_write(m.UC_M68K_REG_D0,0);call(cpu,0x49a1a);boot=bytes(cpu.mem_read(BASE,65536))
 def fixture(area=0,gate=0,active=3,identifier=1,count=80):
  ram=bytearray(boot);ram[0xbad]=area;ram[0xbac]=6;ram[0xd684]=gate;put(ram,0x4ca0,count)
  for index,(obj,record) in enumerate(((0xcb8,0xdcba),(0xda8,0xdce6))):
   struct.pack_into('>I',ram,obj,0 if active&(1<<index) else 0x270e);struct.pack_into('>I',ram,obj+0x8c,0x10d450+index*16)
   ram[record:record+44]=hashlib.shake_256(b'area-record'+bytes([index,identifier])).digest(44);put(ram,record,1);ram[record+0x27]=identifier
  for at in (0x4d74,0x4d76,0x4d8a,0x4d8c):put(ram,at,0)
  ram[0x12]=0;ram[0xdd2a]=0;ram[0xdd2b]=127;ram[0xdd1e]=255
  for at in (0xd734,0xd738):struct.pack_into('>I',ram,at,0xdeadbeef)
  return ram
 def args(pending,external=0,selected=None):
  command=[str(exe),'--state']+list(map(str,[pending[key] for key in ('next_pc','d0','d1','d3','a6','phase')]))
  if pending['phase']==1:
   inner=pending['initialization']['prelude'];command+=['--init',str(inner['next_pc']),str(inner['phase'])]
   if inner['word']['waiting']:command+=['--word']+list(map(str,[inner['word'][key] for key in ('phase','low','cursor','command','tail','next')]))
   if inner['byte']['waiting']:command+=['--byte']+list(map(str,[inner['byte'][key] for key in ('command','tail','next')]))
  return command+[str(external),str(inp),str(out)]+list(map(str,selected or resources))
 def compare(ram,pending=None,context=None,external=0,label='matrix'):
  pending=pending or fresh();cpu.mem_write(BASE,bytes(ram))
  if context is None:
   cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  else:
   cpu.context_restore(context)
   assert cpu.reg_read(m.UC_M68K_REG_PC)==pending['next_pc'] and cpu.reg_read(m.UC_M68K_REG_A5)==0x108000
   if pending['phase']==0:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK
  for reg,key in zip(REGS,KEYS):cpu.reg_write(reg,pending[key])
  state.update(stop=DONE,external=external,waits=0);reads.clear();paths.clear();release_observed.clear()
  cpu.emu_start(pending['next_pc'],0xffffff,count=300000);pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (WAIT,DONE),hex(pc)
  values=tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS);result=dict(next_pc=pc,phase=1 if pc==WAIT else 2,**dict(zip(KEYS,values)),external_reads=len(reads),initialization=initialization())
  first_area=pending['phase']==1 or ram[pending['a6']-BASE+0x7d]==0
  if pc==WAIT:
   inner=result['initialization']['prelude'];inner.update(next_pc=WAIT,d0=values[0],d1=values[1],d3=values[2]);sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big')
   assert sp==STACK-4-{0x3c00:10,0x4759e:4,0x3d4c:12,0x3d42:8}[ret]
   captured=dict(waiting=True,command=values[0]&255,tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=values[1]&65535)
   if ret in (0x3c00,0x4759e):
    phase=1 if ret==0x3c00 else 2;inner['phase']=1;inner['word'].update(captured,kind=1,phase=phase,low=cpu.mem_read(sp+4,1)[0] if phase==1 else captured['command'],cursor=0)
   else:inner['phase']=2 if ret==0x3d4c else 3;inner['byte']=captured
  elif first_area:
   result['initialization'].update(returned=True);result['initialization']['prelude'].update(next_pc=0x475a4,phase=4,d0=0,d1=0,d3=0)
  if pc==DONE:
   assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK and values[0]==4
   assert bytes(cpu.mem_read(BASE+0xd734,8))==bytes(8)
  expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram);actual=subprocess.run(args(pending,external),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
  if actual_ram!=expected or parsed!=result:
   diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,diff[:20],result,parsed)))
  if pending['phase']==1:assert not reads and not {0x47594,0x48180} & set(paths)
  rows.append(dict(profile=label,incoming=pending,result=parsed,native_calls=paths.copy(),read_events=reads.copy(),release_lookup_indices=release_observed.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
  return bytearray(actual_ram),parsed,cpu.context_save()
 for area,gate,active,identifier,high in itertools.product((0,1),(0,1,255),range(4),(1,255),(0,0xabcd,0xffff)):
  compare(fixture(area,gate,active,identifier),fresh((high<<16|0x1234,0xfedcba98,0x87654321,0x100b30)),label='first-nonfirst-gates-snapshot-active-zero-callback')
 for selector in range(256):
  ram=fixture();ram[0xdd2a]=selector;ram[0xdd2b]=selector
  compare(ram,label='all-selector-bytes-release-bit7-skip-and-128-address-window')
 assert set(index for row in rows for index in row['release_lookup_indices'])==set(range(128))
 for area in (0,1):
  ram=fixture(area,count=0);struct.pack_into('>I',ram,0x4c9c,0xdeadbeef);compare(ram,label='allocation-normal-failure-unused-invalid-head')
 # A controlled free-node callback store changes live d684 after its gate was read.
 ram=fixture(area=1);struct.pack_into('>I',ram,0x4c9c,0x10d682);struct.pack_into('>I',ram,0xd68a,0x101200)
 alias_ram,alias_state,alias_context=compare(ram,label='allocation-free-node-callback-store-changes-live-d684')
 assert alias_ram[0xd684]==0x76 and alias_state['d0']==4
 rows[-1]['live_d684_alias_transition']=[0,alias_ram[0xd684]]
 wait_kinds=set()
 for oldest,step,live_gate in itertools.product((None,0x0455,0x0355,0x5503),(1,2),(0,1)):
  ram=fixture();put(ram,0x4d74,step)
  if oldest is not None:put(ram,0x4d8c,6);put(ram,0x4d82,oldest)
  ram[0x12],ram[0xfd82],ram[0xfd8d]=1,1,1
  start=len(rows);ram,pending,context=compare(ram,label='first-area-initialization-wait')
  edits=[];rounds=0
  while pending['phase']==1:
   inner=pending['initialization']['prelude'];wait_kinds.add((inner['phase'],inner['word']['phase']))
   prior=bytes(ram);ram,pending,context=compare(ram,pending,context,external=255,label='repeated-wait-preserves-prefix-and-no-resample');assert ram==prior
   inner=pending['initialization']['prelude'];captured=inner['word'] if inner['phase']==1 else inner['byte'];released=(captured['next']+10)&127
   edits.append(dict(offset=0x4d74,new=released));put(ram,0x4d74,released);ram[0xd684]=live_gate;ram[0xbad]=1 # Host changes area while suspended; original branch must not restart.
   ram,pending,context=compare(ram,pending,context,external=255,label='host-released-cli-state-carry-live-d684')
   rounds+=1;assert rounds<=6
  assert (0x4e666 in rows[-1]['native_calls'])==(live_gate==0) and (0xd760a in rows[-1]['native_calls'])==(live_gate==0)
  sequences.append(dict(calls=len(rows)-start,actual_cli_ram_full_regs_pending_carry=True,host_sound_head_edits=edits,host_live_d684=live_gate,host_area_changed_to_nonfirst_while_waiting=True,native_context_stack_preserved=True))
 assert {(1,1),(1,2),(2,0),(3,0)}<=wait_kinds
 for area in (0,1):
  ram=fixture(area,gate=3)
  for at in (0x9a8,0xa6c):struct.pack_into('>I',ram,at,0)
  pending=fresh();cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,key in zip(REGS,KEYS):cpu.reg_write(reg,pending[key])
  state.update(stop=ENTRY,waits=0);cpu.emu_start(0x479ba,0xffffff,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==ENTRY and cpu.reg_read(m.UC_M68K_REG_A7)==STACK
  expected=bytes(cpu.mem_read(BASE,65536));expected_regs=tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS);context=cpu.context_save()
  inp.write_bytes(ram);portfile=folder/'predecessor.ports.bin'
  command=[str(root/'build/step_stage_players'),'0x479ba']+[str(pending[key]) for key in KEYS]+[str(inp),str(out),str(portfile),str(root/'extracted/runtime/stage_players.ms5d')]
  actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
  parsed=json.loads(actual.stdout);assert out.read_bytes()==expected and tuple(parsed[key] for key in KEYS)==expected_regs and not portfile.read_bytes()
  pending=fresh(tuple(parsed[key] for key in KEYS));compare(bytearray(out.read_bytes()),pending,context,label='actual-player-cli-output-to-area-initialization-same-context')
  integrations.append(dict(area=area,actual_cli_ram_full_exposed_registers_carried=True,native_context_preserved_no_a5_a7_sr_stack_reset=True))
 sentinel=b'old-output\0\xff'
 def reject(ram,pending=None,selected=None,label='invalid',command=None):
  inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run(command or args(pending or fresh(),selected=selected),capture_output=True,text=True)
  assert actual.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stderr)
  negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
 for size in (0,65535,65537):reject(bytes(size),label='invalid-size')
 for pointer in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(),fresh((0,0,0,pointer)),label='invalid-controller-span')
 for key,value in itertools.product(('next_pc','d0','d1','d3','a6','phase'),('-1','4294967296','0x','1x','')):
  pending=fresh();pending[key]=value;reject(fixture(),pending,label='invalid-state-parser')
 badfile=folder/'bad.ms5d';badfile.write_bytes(b'bad')
 for index in range(3):selected=resources.copy();selected[index]=badfile;reject(fixture(),selected=selected,label='malformed-resource')
 ram=fixture(1);ram[0xdce6+0x27]=0;reject(ram,label='late-second-snapshot-zero-id')
 ram=fixture();struct.pack_into('>I',ram,0x4c9c,0xdeadbeef);reject(ram,label='late-allocation-after-initialization')
 badfile.write_bytes(resources[2].read_bytes()[:32]);selected=resources.copy();selected[2]=badfile;reject(fixture(),selected=selected,label='truncated-release-window')
 pending=fresh();pending.update(next_pc=WAIT,phase=1);reject(fixture(),pending,label='missing-initialization-pending')
 for kind in ('same','hardlink','symlink'):
  ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True)
   if kind=='hardlink':alias.hardlink_to(inp)
   else:alias.symlink_to(inp)
  command=args(fresh());command[10]=str(alias);actual=subprocess.run(command,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram
  negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
 assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,resources_sha256=resource_hashes,cases=len(rows),negative_cases=len(negatives),full_ram_d0_d1_d3_a6_pending_equal=True,program_code_modified=False,mmio_writes=0,external_reads=sum(len(row['read_events']) for row in rows),release_lookup_observed_indices=list(range(128)),wait_kinds=sorted(wait_kinds),carry_sequences=sequences,player_caller_integrations=integrations,results=rows,negative_results=negatives,scope='Native2790/3ef2/49a1a runtime fixtures with controlled source records and valid stored pointers. Original479d0 branches and every nested helper run unmodified; stop47a1c beforelaterbody. Source record and playerobject fields are distinct. Lookup128 is an addresswindow with bit7skip, not proof of natural selector usage. Wait sequences carry actualCLI RAM/fullD0D1D3A6/pending and preserve native CPUcontext/stack while host explicitly changes soundhead and LIVE d684; no naturalIRQ timing claim. The controlled allocator callback store changes d684 after its gate read; this is alias/access-order evidence, not a second live-gate test. Live-gate evidence is the separate suspended host d684 change. Stored d764a callback is not executed. Other CPU registers/CCR are excluded.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

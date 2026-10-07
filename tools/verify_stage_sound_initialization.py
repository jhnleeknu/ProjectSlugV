"""Native47a1c..47a94 stage sound calls with independently captured pending."""
import hashlib,itertools,json,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256,verify_resources
from verify_game_prelude import empty_word,empty_byte
BASE,STACK,RETURN,ENTRY,WAIT,DONE=0x100000,0x1feffc,0xff000,0x47a1c,0x3aea,0x47a94
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3,m.UC_M68K_REG_A6);KEYS=('d0','d1','d3','a6')
def put(ram,at,v):struct.pack_into('>H',ram,at,v&65535)
def word(ram,at):return struct.unpack_from('>H',ram,at)[0]
def fresh(values=(0xabcd1234,0xfedcba98,0x87654321,0x100b30)):return dict(next_pc=ENTRY,phase=0,**dict(zip(KEYS,values)),external_reads=0,word=empty_word(),byte=empty_byte())
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 catalog=root/'extracted/runtime/stages';groups=verify_resources(catalog,program,source);records=[r['source_cpu_address'] for g in groups for r in g['records']];assert len(records)==59
 music={a:int.from_bytes(program[a+16:a+18],'big') for a in records};by_music={value:next(a for a in records if music[a]==value) for value in set(music.values())};assert 0x10fe not in by_music
 folder=root/'artifacts/stage_sound_initialization';folder.mkdir(parents=True,exist_ok=True)
 inp,out,report=[folder/n for n in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/step_stage_sound_initialization';binary=hashlib.sha256(exe.read_bytes()).hexdigest()
 cpu=make_cpu(program);cpu.mem_map(0xd00000,4096);state={'stop':RETURN,'external':0,'waits':0};reads,paths,rows,negatives,sequences,integrations=[],[],[],[],[],[]
 def code(cpu,address,size,user):
  if address==state['stop']:cpu.emu_stop()
  elif address in (0x3af8,0x3d44,0x3c84):paths.append(address)
  elif address==WAIT:
   if int.from_bytes(cpu.mem_read(BASE+0x4d74,2),'big')==(cpu.reg_read(m.UC_M68K_REG_D1)&65535):
    state['waits']+=1
    if state['waits']==2:cpu.emu_stop()
   else:state['waits']=0
 def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
 def read(cpu,access,address,size,value,user):assert address==0xd00046 and size==1;cpu.mem_write(address,bytes([state['external']]));reads.append((size,address,state['external']))
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=0xd00046,end=0xd00046)
 cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);boot=bytes(cpu.mem_read(BASE,65536))
 def fixture(address,equal=False):
  ram=bytearray(boot);struct.pack_into('>I',ram,0xba6,address);put(ram,0xd686,music[address] if equal else music[address]^65535)
  for at in (0x4d74,0x4d76,0x4d8a,0x4d8c):put(ram,at,0)
  struct.pack_into('>4H',ram,0x4d82,0x0455,0x0566,0x0677,0x0788);ram[0x12]=0;ram[0x4d7e]=0
  return ram
 def args(pending,external=0,cat=catalog):
  command=[str(exe),'--state']+list(map(str,[pending[k] for k in ('next_pc','d0','d1','d3','a6','phase')]))
  if pending['word']['waiting']:command+=['--word']+list(map(str,[pending['word'][k] for k in ('kind','phase','low','cursor','command','tail','next')]))
  if pending['byte']['waiting']:command+=['--byte']+list(map(str,[pending['byte'][k] for k in ('command','tail','next')]))
  return command+[str(external),str(inp),str(out),str(cat)]
 def compare(ram,pending=None,context=None,external=0,label='matrix'):
  pending=pending or fresh();cpu.mem_write(BASE,bytes(ram))
  if context is None:
   cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  else:
   cpu.context_restore(context);assert cpu.reg_read(m.UC_M68K_REG_PC)==pending['next_pc'] and cpu.reg_read(m.UC_M68K_REG_A5)==0x108000
  for reg,key in zip(REGS,KEYS):cpu.reg_write(reg,pending[key])
  state.update(stop=DONE,external=external,waits=0);reads.clear();paths.clear();cpu.emu_start(pending['next_pc'],0xffffff,count=200000)
  pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (WAIT,DONE)
  result=fresh(tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS));result.update(next_pc=pc,phase=9,external_reads=len(reads))
  if pc==WAIT:
   sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big')
   captured=dict(waiting=True,command=result['d0']&255,tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=result['d1']&65535)
   word_returns={0x47a50:1,0x47a74:4,0x47a7e:5,0x47a88:6}
   if ret==0x3c00 or ret in word_returns:
    phase=1 if ret==0x3c00 else 2;outer_ret=int.from_bytes(cpu.mem_read(sp+6,4),'big') if phase==1 else ret
    result['phase']=word_returns[outer_ret];result['word'].update(captured,kind=1,phase=phase,low=cpu.mem_read(sp+4,1)[0] if phase==1 else result['d0']&255,cursor=0)
    assert sp==STACK-(10 if phase==1 else 4)
   else:
    high=ret==0x3d4c;outer_ret=int.from_bytes(cpu.mem_read(sp+4,4),'big') if high else ret;assert outer_ret in (0x47a6a,0x47a94)
    result['phase']=(2 if high else 3) if outer_ret==0x47a6a else (7 if high else 8);result['byte']=captured;assert sp==STACK-(8 if high else 4)
  else:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK and bytes(cpu.mem_read(BASE+0x4d7e,1))==b'\0'
  expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram);actual=subprocess.run(args(pending,external),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
  if actual_ram!=expected or parsed!=result:
   diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,diff[:20],result,parsed)))
  rows.append(dict(profile=label,incoming=pending,result=parsed,read_events=reads.copy(),native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
  return bytearray(actual_ram),parsed,cpu.context_save()
 for address,equal,high in itertools.product(records,(False,True),(0,0xabcd,0xffff)):
  compare(fixture(address,equal),fresh((high<<16|0x1234,high<<16|0x9876,0x87654321,0x100b30)),label='all59-original-records-equal-and-different-music-highwords')
 for mode,fd82,fd8d,external,block in itertools.product((0,1),(0,1),(0,1),(0,1),(0,1)):
  ram=fixture(by_music[0x19d2]);ram[0x12],ram[0xfd82],ram[0xfd8d],ram[0x4d7e]=mode,fd82,fd8d,block
  compare(ram,external=external,label='conditional-word-filter-external-read-and-common-clear')
 observed=set()
 for selected,tail,mode in itertools.product((0x19d2,0x19c0),(0,127),(0,1)):
  ram=fixture(by_music[selected]);ram[0x12]=mode;ram[0xfd82]=1;ram[0xfd8d]=1;put(ram,0x4d8c,6);put(ram,0x4d76,tail);put(ram,0x4d74,(tail+1)&127);start=len(rows)
  ram,pending,context=compare(ram,label='every-word-and-byte-wait-native-start');rounds=0
  while pending['phase']!=9:
   observed.add((pending['phase'],pending['word']['phase']));prior=bytes(ram)
   ram,pending,context=compare(ram,pending,context,external=255,label='unchanged-wait-no-record-reread-no-resample');assert ram==prior and pending['external_reads']==0
   captured=pending['word'] if pending['word']['waiting'] else pending['byte'];put(ram,0x4d74,(captured['next']+1)&127)
   struct.pack_into('>I',ram,0xba6,by_music[0x19c1]);put(ram,0xd686,0x1234) # Controlled changes must not restart the record comparison.
   ram,pending,context=compare(ram,pending,context,external=0 if mode else 255,label='actual-cli-carry-host-release-record-and-oldmusic-changed');rounds+=1;assert rounds<=14
  assert word(ram,0xd686)==0x1234
  sequences.append(dict(calls=len(rows)-start,selected_original_music=selected,input_mode=mode,actual_cli_ram_full_regs_pending_carried=True,native_context_stack_preserved=True,host_changes='soundhead next+1,live record pointer19c1 and oldmusic1234',record_comparison_not_repeated=True))
 expected_waits={(p,q) for p in (1,4,5,6) for q in (1,2)}|{(p,0) for p in (2,3,7,8)};assert expected_waits<=observed,(expected_waits,observed)
 # Connect two actual area-initialization CLI results at the native successor.
 for area in (0,1):
  address=by_music[0x19d2];ram=fixture(address,True);ram[0xbad]=area;ram[0xd684]=1
  for i,(obj,record) in enumerate(((0xcb8,0xdcba),(0xda8,0xdce6))):
   struct.pack_into('>I',ram,obj,0);struct.pack_into('>I',ram,obj+0x8c,0x10d450+i*16);put(ram,record,1);ram[record+0x27]=1
  pending=fresh();cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,key in zip(REGS,KEYS):cpu.reg_write(reg,pending[key])
  state.update(stop=ENTRY,waits=0);cpu.emu_start(0x479d0,0xffffff,count=200000);assert cpu.reg_read(m.UC_M68K_REG_PC)==ENTRY and cpu.reg_read(m.UC_M68K_REG_A7)==STACK
  expected=bytes(cpu.mem_read(BASE,65536));values=tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS);context=cpu.context_save();inp.write_bytes(ram)
  resources=[root/'extracted/runtime'/n for n in ('game_records.ms5d','player_record_lookup.ms5d','stage_selector_lookup.ms5d')]
  command=[str(root/'build/step_stage_area_initialization'),'--state','0x479d0']+[str(pending[key]) for key in KEYS]+['0','0',str(inp),str(out)]+list(map(str,resources))
  actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr;parsed=json.loads(actual.stdout)
  assert out.read_bytes()==expected and tuple(parsed[key] for key in KEYS)==values
  compare(bytearray(out.read_bytes()),fresh(tuple(parsed[key] for key in KEYS)),context,label='actual-area-cli-to-sound-caller-same-original-context')
  integrations.append(dict(area=area,actual_cli_ram_full_exposed_regs_carried=True,native_context_no_a5_a7_sr_stack_reset=True))
 sentinel=b'old-output\0\xff'
 def reject(ram,pending=None,cat=catalog,label='invalid',command=None):
  inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run(command or args(pending or fresh(),cat=cat),capture_output=True,text=True)
  assert actual.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stderr)
  negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
 for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
 for pointer in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(records[0]),fresh((0,0,0,pointer)),label='invalid-controller')
 for pointer in (0,0x100000,0xffffffff):
  ram=fixture(records[0]);struct.pack_into('>I',ram,0xba6,pointer);reject(ram,label='unsupported-record-pointer')
 for key,value in itertools.product(('next_pc','d0','d1','d3','a6','phase'),('-1','4294967296','0x','1x','')):
  pending=fresh();pending[key]=value;reject(fixture(records[0]),pending,label='invalid-state-parser')
 ram=fixture(by_music[0x19d2]);put(ram,0x4d8a,1);reject(ram,label='invalid-word-head')
 ram=fixture(by_music[0x19c0]);put(ram,0x4d74,128);reject(ram,label='invalid-byte-head')
 ram=fixture(by_music[0x19d2]);put(ram,0x4d8c,4);put(ram,0x4d74,128);reject(ram,label='late-common-overflow-after-initial-word-and-music-cache')
 for value in ('-1','256'):
  command=args(fresh());command[-4]=value;reject(fixture(records[0]),command=command,label='invalid-external-byte')
 pending=fresh();pending.update(next_pc=WAIT,phase=1);reject(fixture(records[0]),pending,label='missing-word-pending')
 reject(fixture(records[0]),cat=folder/'missing-catalog',label='missing-catalog')
 for kind in ('same','hardlink','symlink'):
  ram=fixture(records[0]);inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True)
   if kind=='hardlink':alias.hardlink_to(inp)
   else:alias.symlink_to(inp)
  command=args(fresh());command[10]=str(alias);actual=subprocess.run(command,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram
  negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
 assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,cases=len(rows),negative_cases=len(negatives),canonical_records=len(records),canonical_music_values=sorted(by_music),unreached_10fe_branch=True,observed_wait_subphases=sorted(observed),full_ram_full_d0_d1_d3_a6_pending_equal=True,program_code_modified=False,mmio_writes=0,external_reads=sum(len(row['read_events']) for row in rows),carry_sequences=sequences,area_integrations=integrations,results=rows,negative_results=negatives,scope='Original47a1c through47a94 stops beforelaterbody. Canonical59ROMrecords are never altered; equal/19c1 skip,19c0 initial08/20 and othermusicwordpaths compared. Canonical catalog hasno10fe record, so thatbranch is not claimed covered. All12native waitsubphases independently extracted fromactualstack returns and fullCLI RAM/register/pending state carried. Host explicitly releases soundhead and changes recordpointer/oldmusicwhilewaiting; originalmustnotreread record. AreaCLI integrations retainoriginal CPUcontext/stack, excludingnatural scheduling/IRQ/otherregisters/CCR/device timing.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

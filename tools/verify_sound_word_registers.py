"""Original3af8 fullD0/D1, captured3aea enqueue continuations, immutable ROM."""
import hashlib,itertools,json,struct,subprocess
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE,STACK,RETURN,ENTRY,WAIT,EXTERNAL=0x100000,0x1feffc,0xff000,0x3af8,0x3aea,0xd00046
KEYS=('kind','phase','low','cursor','command','tail','next')
def word(ram,at):return struct.unpack_from('>H',ram,at)[0]
def put(ram,at,value):struct.pack_into('>H',ram,at,value&65535)
def idle():return dict(kind=0,phase=0,low=0,cursor=0,waiting=False,command=0,tail=0,next=0)
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 folder=root/'artifacts/sound_word_registers';folder.mkdir(parents=True,exist_ok=True)
 inp,out,report=[folder/n for n in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/step_sound_word_registers';binary=hashlib.sha256(exe.read_bytes()).hexdigest()
 cpu=make_cpu(program);cpu.mem_map(0xd00000,4096);state={'external':0,'waits':0};reads,rows,negatives,sequences=[],[],[],[]
 def code(cpu,address,size,user):
  if address==RETURN:cpu.emu_stop()
  elif address==WAIT:
   if int.from_bytes(cpu.mem_read(BASE+0x4d74,2),'big')==(cpu.reg_read(m.UC_M68K_REG_D1)&65535):
    state['waits']+=1
    if state['waits']==2:cpu.emu_stop()
   else:state['waits']=0
 def read(cpu,access,address,size,value,user):assert address==EXTERNAL and size==1;cpu.mem_write(address,bytes([state['external']]));reads.append((size,address,state['external']))
 def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_READ,read,begin=EXTERNAL,end=EXTERNAL);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 def fixture(head=0,tail=0,bytehead=0,bytetail=0,slots=(0x0455,0x0566,0x0677,0x0788)):
  ram=bytearray(hashlib.shake_256(b'sound-word-registers'+len(rows).to_bytes(4,'big')).digest(65536))
  for at in (0x12,0xfd82,0xfe80,0xfd8d,0x4d7e,0xf001,0x4d7b):ram[at]=0
  struct.pack_into('>4H',ram,0x4d82,*slots);put(ram,0x4d8a,head);put(ram,0x4d8c,tail);put(ram,0x4d74,bytehead);put(ram,0x4d76,bytetail)
  return ram
 def args(d0,d1,external=0,pending=None):
  command=[str(exe),'resume' if pending is not None else 'enqueue',str(inp),str(out),str(d0),str(d1)]
  return command+([str(pending[key]) for key in KEYS] if pending is not None else [str(external)])
 def compare(ram,d0,d1,external=0,pending=None,context=None,label='matrix'):
  cpu.mem_write(BASE,bytes(ram))
  if context is None:
   cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.reg_write(m.UC_M68K_REG_D3,0x87654321)
  else:cpu.context_restore(context)
  cpu.reg_write(m.UC_M68K_REG_D0,d0);cpu.reg_write(m.UC_M68K_REG_D1,d1);state.update(external=external,waits=0);reads.clear()
  cpu.emu_start(WAIT if pending else ENTRY,0xffffff,count=100000);pc=cpu.reg_read(m.UC_M68K_REG_PC);assert pc in (RETURN,WAIT)
  result=dict(d0=cpu.reg_read(m.UC_M68K_REG_D0)&0xffffffff,d1=cpu.reg_read(m.UC_M68K_REG_D1)&0xffffffff,external_reads=len(reads),pending=idle())
  assert cpu.reg_read(m.UC_M68K_REG_D3)==0x87654321
  command=d0&65535;high=command&0xff00
  expected_read=int(pending is None and command<0x2000 and command&255>=0x20 and high not in (0x100,0x200,0x300) and ram[0x12]==1 and high!=0 and ram[0xfd82]!=0 and ram[0xfe80]==0)
  assert reads==([(1,EXTERNAL,external)] if expected_read else [])
  if pc==WAIT:
   sp=cpu.reg_read(m.UC_M68K_REG_A7);ret=int.from_bytes(cpu.mem_read(sp,4),'big');assert ret in (0x3c00,RETURN)
   phase=1 if ret==0x3c00 else 2;assert sp==(STACK-6 if phase==1 else STACK)
   result['pending'].update(kind=1,phase=phase,low=cpu.mem_read(sp+4,1)[0] if phase==1 else result['d0']&255,waiting=True,command=result['d0']&255,tail=cpu.reg_read(m.UC_M68K_REG_A0)-BASE-0x4cf4,next=result['d1']&65535)
  else:assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
  expected=bytes(cpu.mem_read(BASE,65536));inp.write_bytes(ram);actual=subprocess.run(args(d0,d1,external,pending),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
  if actual_ram!=expected or parsed!=result:
   diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,d0,d1,pending,diff[:20],result,parsed)))
  rows.append(dict(profile=label,incoming_d0=d0,incoming_d1=d1,incoming_pending=pending,result=parsed,reads=reads.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),ram_changed=bytes(ram)!=expected))
  return bytearray(actual_ram),parsed,cpu.context_save()
 commands=(0,0x1f,0x20,0xff,0x100,0x120,0x1ff,0x220,0x320,0x420,0xfff,0x1000,0x1020,0x1fff,0x2000,0xffff)
 for command,mode,fd82,fe80,fd8d,block,bit5,external in itertools.product(commands,(0,1),(0,1),(0,1),(0,1),(0,1),(0,32),(0,1)):
  ram=fixture();ram[0x12],ram[0xfd82],ram[0xfe80],ram[0xfd8d],ram[0x4d7e],ram[0xf001]=mode,fd82,fe80,fd8d,block,bit5
  compare(ram,0xabcd0000|command,0xfedc9876,external,label='all-filter-profiles-full-registers')
 for head,tail,command,high in itertools.product((0,2,4,6),(0,2,4,6),(0x0455,0x0566,0x0677,0x0788,0x0866),(0,0xffff)):
  compare(fixture(head,tail),(high<<16)|command,(high<<16)|0x1234,label='duplicate-one-following-slot-append-overflow-highwords')
 for head,oldest,bytehead,bytetail,high in itertools.product((0,2,4,6),(0,0x0303,0x0355,0x5503,0x0455),(0,1,2),(0,127),(0,0x1234)):
  slots=[0x0566]*4;slots[head//2]=oldest;ram=fixture(head,(head+6)&6,(bytetail+bytehead)&127,bytetail,slots)
  compare(ram,(high<<16)|0x0866,0xbeef9876,label='oldest-zero-high-low-special3-or-ordinary-ring-wrap')
 for command in (0,0x1f,0x2000,0xffff):
  ram=fixture(65535,65535,65535,65535);ram,result,context=compare(ram,0x12340000|command,0xfedc9876,label='early-filter-bypasses-all-invalid-indices')
  assert result['d1']==0xfedc9876
 for head in (0,2,4,6):
  compare(fixture(head,(head+6)&6,65535,65535,(0,0,0,0)),0x12340866,0xfedc9876,label='zero-oldest-overflow-bypasses-invalid-byte-indices')
 wait_kinds=set()
 for oldest,bytetail,step,high in itertools.product((0x0455,0x0355,0x5503),(0,127),(1,2),(0,0xabcd)):
  ram=fixture(0,6,(bytetail+step)&127,bytetail,(oldest,0x0566,0x0677,0x0788));start=len(rows)
  ram,result,context=compare(ram,(high<<16)|0x0866,0xfedc9876,label='carried-enqueue-overflow-start')
  rounds=0
  while result['pending']['waiting']:
   pending=result['pending'];wait_kinds.add(pending['phase']);prior=bytes(ram)
   ram,result,context=compare(ram,result['d0'],result['d1'],pending=pending,context=context,label='carried-unchanged-wait-no-resample');assert ram==prior
   pending=result['pending'];put(ram,0x4d74,(pending['next']+4)&127);put(ram,0x4d76,53);put(ram,0x4d8a,65535);put(ram,0x4d8c,65535);put(ram,0x4d82,0xaabb)
   ram,result,context=compare(ram,result['d0'],result['d1'],pending=pending,context=context,label='host-release-live-head-tail-word-slot-mutations');rounds+=1;assert rounds<=4
  sequences.append(dict(calls=len(rows)-start,actual_cli_ram_full_d0_d1_pending_carried=True,native_cpu_context_stack_preserved=True,host_mutations='bytehead release,byte live tail53,word live indicesffff andoldslot aabb',natural_concurrency_claim=False))
 for tail,high in itertools.product((0,127),(0,0xffff)):
  ram=fixture(0,6,(tail+1)&127,tail);start=len(rows)
  ram,result,context=compare(ram,(high<<16)|0x0866,0xabcd9876,label='actual-cli-high-to-low-to-return-start');assert result['pending']['phase']==1
  for step,expected_phase in ((2,2),(4,0)):
   put(ram,0x4d74,(tail+step)&127)
   ram,result,context=compare(ram,result['d0'],result['d1'],pending=result['pending'],context=context,label='actual-cli-high-to-low-to-return-carry')
   assert result['pending']['phase']==expected_phase
  sequences.append(dict(calls=len(rows)-start,actual_cli_ram_full_d0_d1_pending_carried=True,native_cpu_context_stack_preserved=True,explicit_phases=[1,2,0],host_mutations='bytehead step2 thenstep4',natural_concurrency_claim=False))
 assert wait_kinds=={1,2}
 sentinel=b'old-output\0\xff'
 def reject(ram,d0=0xabcd0866,d1=0xfedc9876,pending=None,external=0,label='invalid',command=None):
  inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run(command or args(d0,d1,external,pending),capture_output=True,text=True)
  assert actual.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stderr)
  negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
 for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
 for at,value in ((0x4d8a,1),(0x4d8c,8),(0x4d74,128),(0x4d76,65535)):
  ram=fixture(0,6);put(ram,at,value);reject(ram,label='invalid-used-index')
 for key,value in itertools.product(('d0','d1'),('-1','4294967296','0x','1x','')):
  values=dict(d0=0xabcd0866,d1=0xfedc9876);values[key]=value;reject(fixture(),**values,label='invalid-register-parser')
 for external in ('-1','256','0x','1x',''):reject(fixture(),external=external,label='invalid-external-byte')
 pending=idle();pending.update(kind=1,phase=1,low=55,waiting=True,command=4,tail=0,next=1)
 for key,value in (('kind',2),('phase',3),('cursor',1),('command',3),('tail',128),('next',2)):
  bad=pending.copy();bad[key]=value;reject(fixture(),d0=0xabcd0804,d1=0xfedc0001,pending=bad,label='invalid-captured-state')
 ram,result,context=compare(fixture(0,6,1),0xabcd0866,0xfedc9876,label='negative-valid-wait-fixture')
 bad=bytearray(ram);put(bad,0x4d74,128);reject(bad,result['d0'],result['d1'],result['pending'],label='invalid-live-head-on-resume')
 reject(ram,result['d0']^1,result['d1'],result['pending'],label='captured-command-register-mismatch')
 reject(ram,result['d0'],result['d1']^1,result['pending'],label='captured-next-register-mismatch')
 for kind in ('same','hardlink','symlink'):
  ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True)
   if kind=='hardlink':alias.hardlink_to(inp)
   else:alias.symlink_to(inp)
  command=args(0xabcd0866,0xfedc9876);command[3]=str(alias);actual=subprocess.run(command,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram
  negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
 assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,cases=len(rows),negative_cases=len(negatives),full_ram_d0_d1_pending_equal=True,program_code_modified=False,mmio_writes=0,external_reads=sum(len(row['reads']) for row in rows),native_d3_preserved_only_observation=True,native_a7_wait_and_rts_endpoints_verified=True,carry_sequences=sequences,results=rows,negative_results=negatives,scope='Original3af8enqueue and actual3aea continuation execute unmodified throughRTS or producerwait. FullRAM/fullD0D1/pending and conditional externalreads compared; D3preservation observed only becauseAPI excludesit. Nativeexternalstack remainsoutsideRAM and A7wait/RTSendpoints independentlychecked. CLIoutputs carryactualRAM/registers/capturedpending; host changes queues only in explicitlymarked fixtures, no naturalIRQ/concurrency claim. ProducerperformsnoMMIOwrites. Other CPUregisters/CCR excluded.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

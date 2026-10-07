"""Native player-record reads, snapshots and stage-area resume boundary."""
import hashlib,itertools,json,struct,subprocess
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256,checked_resource
BASE,STACK,RETURN=0x100000,0x1feffc,0xff000
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D2,m.UC_M68K_REG_D3,m.UC_M68K_REG_D4,m.UC_M68K_REG_D5,m.UC_M68K_REG_D6)
KEYS=tuple('d'+str(i) for i in range(7))
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 folder=root/'artifacts/player_record_capture';folder.mkdir(parents=True,exist_ok=True)
 inp,out,report=[folder/n for n in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
 executable=root/'build/step_player_record_capture';area_executable=root/'build/step_stage_area_resume';binaries={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in (executable,area_executable)}
 resource=root/'extracted/runtime/player_record_lookup.ms5d';resource_sha=checked_resource(resource,program,0x4cf64,0x4df60)
 cpu=make_cpu(program);state={'stop':RETURN};paths,rows,areas,negatives,sequences=[],[],[],[],[]
 calls=(0x289e,0x4d7a6,0x48180,0x1bd12,0xe89fa,0x3d42,0x3dce,0x49a8e,0x4aa30,0xb4a24,0x2ef90,0x6f1c2,0x46f2e,0x4d13c,0x4ddb6,0x475ca)
 def code(cpu,address,size,user):
  if address==state['stop']:cpu.emu_stop()
  elif address in calls:paths.append(address)
 def write(cpu,access,address,size,value,user):
  assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);boot=bytes(cpu.mem_read(BASE,65536))
 def fixture(identifier=1,active=3,source_words=(1,1),seed=0):
  ram=bytearray(boot)
  for index,(obj,record) in enumerate(((0xcb8,0xdcba),(0xda8,0xdce6))):
   struct.pack_into('>I',ram,obj,0 if active&(1<<index) else 0x270e);struct.pack_into('>I',ram,obj+0x8c,0x10d450+index*0x10)
   ram[record:record+0x2c]=hashlib.shake_256(b'capture-fixture'+bytes([seed,index])).digest(0x2c)
   struct.pack_into('>H',ram,record,source_words[index]);ram[record+0x27]=identifier
  return ram
 def init_native(ram,values,entry,context=None):
  if context is None:
   cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  else:
   cpu.context_restore(context);assert cpu.reg_read(m.UC_M68K_REG_PC)==entry and cpu.reg_read(m.UC_M68K_REG_A5)==0x108000 and cpu.reg_read(m.UC_M68K_REG_A7)==STACK
  cpu.mem_write(BASE,bytes(ram))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  paths.clear();state['stop']=0x479fe if entry==0x479ee else RETURN
  cpu.emu_start(entry,0xffffff,count=300000)
  assert cpu.reg_read(m.UC_M68K_REG_PC)==state['stop'] and cpu.reg_read(m.UC_M68K_REG_A7)==(STACK if entry==0x479ee else STACK+4)
 def args(entry,values,selected=resource,area=False):
  values=[values[i] for i in (0,1,3)] if area else values
  return [str(area_executable if area else executable),str(entry)]+list(map(str,values))+list(map(str,(inp,out,selected)))
 def compare(ram,entry,values,label,area=False,context=None):
  init_native(ram,values,entry,context);expected=bytes(cpu.mem_read(BASE,65536));native_values=tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS)
  result=dict(zip(KEYS,native_values));result={key:result[key] for key in ('d0','d1','d3')} if area else result
  inp.write_bytes(ram);actual=subprocess.run(args(entry,values,area=area),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
  if actual_ram!=expected or parsed!=result:
   diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,hex(entry),values,diff[:20],result,parsed)))
  row=dict(profile=label,entry=entry,incoming=dict(zip(KEYS,values)),result=parsed,native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest())
  (areas if area else rows).append(row)
  # Area CLI exposes only D0/D1/D3; remaining native registers are explicit fixture state.
  carried=tuple(parsed[key] if key in parsed else native_values[i] for i,key in enumerate(KEYS))
  return bytearray(actual_ram),carried
 highs=((0,0,0,0,0,0,0),(0xabcd1234,0x12345678,0x87654321,0xfedcba98,0x76543210,0xbeef8000,0x98765432))
 for entry,identifier,selector,values in itertools.product((0x4d7a6,0x48180),range(1,256),(0,1),highs):
  incoming=list(values);incoming[0]=(incoming[0]&0xffff0000)|selector
  compare(fixture(identifier,seed=identifier),entry,incoming,'all-active-byte-ids-original-lookup-window')
 for entry,active,words,selector,values in itertools.product((0x4d7a6,0x48180),range(4),((0,0),(0,1),(1,0),(0x8000,0xffff)),(0,1,2,0x100),highs):
  incoming=list(values);incoming[0]=(incoming[0]&0xffff0000)|selector
  # Active ID0 wouldTRAP, so only nonzero source IDs here.
  compare(fixture(255,active,words),entry,incoming,'inactive-or-zero-source-word-defaults-selector-byte-vs-parity')
 for entry,identifier,selector in itertools.product((0x4d7a6,0x48180),(1,255),(0,1)):
  ram=fixture(identifier)
  for at in (0xcb8,0xda8):struct.pack_into('>I',ram,at,0x1234)
  values=list(highs[1]);values[0]=(values[0]&0xffff0000)|selector
  compare(ram,entry,values,'nonzero-active-callback-same-record-read')
 for entry,identifier,selector in itertools.product((0x4d7a6,0x48180),range(1,256),(0,1)):
  values=list(highs[1]);values[0]=(values[0]&0xffff0000)|selector
  compare(fixture(identifier,source_words=(0,0)),entry,values,'all-byte-ids-zero-source-word-bypasses-lookup')
 for entry,selector in itertools.product((0x4d7a6,0x48180),(0,1)):
  values=list(highs[1]);values[0]=(values[0]&0xffff0000)|selector
  compare(fixture(0,active=0),entry,values,'inactive-callback-bypasses-source-id-zero')
 for fill in (0,128,255):
  ram=fixture(255)
  for at in (0xdcba,0xdce6):
   ram[at+0x25:at+0x27]=bytes([fill])*2;ram[at+0x2a]=fill
   struct.pack_into('>H',ram,at+0x1c,fill*257);struct.pack_into('>H',ram,at+0x20,fill*257)
  for entry,selector in itertools.product((0x4d7a6,0x48180),(0,1)):
   values=list(highs[1]);values[0]=(values[0]&0xffff0000)|selector
   compare(ram,entry,values,'captured-fields-byte-word-boundaries')
 for identifier,selector in itertools.product((1,20,127,255),(0,1)):
  ram=fixture(identifier);values=list(highs[1]);values[0]=(values[0]&0xffff0000)|selector;start=len(rows)
  ram,values=compare(ram,0x4d7a6,values,'actual-cli-read-to-snapshot-register-carry')
  values=((values[0]&0xffff0000)|selector,)+values[1:] # Host selects destination/source after read.
  for iteration in range(3):ram,values=compare(ram,0x48180,values,'actual-cli-repeated-snapshot-register-ram-carry')
  sequences.append(dict(calls=len(rows)-start,actual_cli_ram_full_d0_to_d6_carried=True,host_input='D0.word snapshot selector after read'))
 for entry,identifier,active,values in itertools.product((0x475ca,0x479ee),(1,20,255),range(4),highs):
  compare(fixture(identifier,active),entry,values,'original-area-tail-and-double-snapshot',area=True)
 integrations=[]
 for identifier in (1,255):
  ram=fixture(identifier);ram[0xbac]=6;ram[0xbad]=1;ram[0xd684]=3
  for at in (0x9a8,0xa6c):struct.pack_into('>I',ram,at,0)
  values=highs[1];cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A6,0x100b30);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  state['stop']=0x479d0;cpu.emu_start(0x479ba,0xffffff,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==0x479d0 and cpu.reg_read(m.UC_M68K_REG_A7)==STACK
  expected=bytes(cpu.mem_read(BASE,65536));native_values=tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS)
  inp.write_bytes(ram);portfile=folder/'predecessor.ports.bin'
  command=[str(root/'build/step_stage_players'),'0x479ba']+[str(values[i]) for i in (0,1,3)]+['0x100b30',str(inp),str(out),str(portfile),str(root/'extracted/runtime/stage_players.ms5d')]
  actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
  parsed=json.loads(actual.stdout);assert out.read_bytes()==expected and not portfile.read_bytes() and parsed['writes']==0
  for i in (0,1,3):assert parsed[KEYS[i]]==native_values[i]
  assert parsed['a6']==0x100b30
  state['stop']=0x479ee;cpu.emu_start(0x479d0,0xffffff,count=10);assert cpu.reg_read(m.UC_M68K_REG_PC)==0x479ee
  context=cpu.context_save();carried=tuple(parsed[KEYS[i]] if i in (0,1,3) else native_values[i] for i in range(7))
  compare(bytearray(out.read_bytes()),0x479ee,carried,'actual-player-caller-cli-to-area-original-bne',area=True,context=context)
  integrations.append(dict(identifier=identifier,actual_cli_ram_d0_d1_d3_carried=True,native_context_preserved_without_a5_a7_sr_stack_reset=True,unexposed_d2_d4_d5_d6_are_native_fixture=True,original479d0_bne_executed=True))
 sentinel=b'old-output\0\xff'
 def reject(ram,entry=0x48180,values=highs[1],selected=resource,area=False,label='invalid'):
  inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run(args(entry,values,selected,area),capture_output=True,text=True)
  assert actual.returncode and out.read_bytes()==sentinel,(label,actual.stderr)
  negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
 for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
 for entry in (0,0x4d7f0):reject(fixture(),entry=entry,label='unsupported-entry')
 for index,value in itertools.product(range(7),('-1','4294967296','0x','1x','')):
  values=list(highs[1]);values[index]=value;reject(fixture(),values=values,label='invalid-uint32')
 for entry in (0x4d7a6,0x48180):reject(fixture(0),entry=entry,label='active-record-zero-id-native-trap-excluded')
 ram=fixture(1);ram[0xdce6+0x27]=0;reject(ram,entry=0x479ee,area=True,label='late-second-snapshot-id-zero-rollback')
 ram=fixture(1);struct.pack_into('>I',ram,0xda8+0x8c,0xffffffff);reject(ram,entry=0x475ca,area=True,label='late-second-object-stored-pointer')
 badfile=folder/'bad.ms5d';badfile.write_bytes(b'bad');reject(fixture(),selected=badfile,label='malformed-resource')
 raw=bytearray(resource.read_bytes());raw[-1]^=1;badfile.write_bytes(raw);reject(fixture(),selected=badfile,label='resource-crc-error')
 for kind in ('same','hardlink','symlink'):
  ram=fixture();inp.write_bytes(ram);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True)
   if kind=='hardlink':alias.hardlink_to(inp)
   else:alias.symlink_to(inp)
  command=args(0x48180,highs[1]);command[10]=str(alias);actual=subprocess.run(command,capture_output=True,text=True)
  assert actual.returncode and inp.read_bytes()==ram
  negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
 assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
 assert binaries=={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in (executable,area_executable)}
 assert {0x1bd12,0xe89fa,0x3d42,0x3dce,0x49a8e,0x4aa30,0xb4a24,0x2ef90,0x6f1c2,0x46f2e,0x4d13c,0x4ddb6}<=set(pc for row in areas for pc in row['native_calls'])
 report.write_text(json.dumps(dict(source=source,binaries_sha256=binaries,resource_sha256=resource_sha,cases=len(rows),area_cases=len(areas),negative_cases=len(negatives),program_code_modified=False,full_ram_d0_to_d6_equal=True,area_full_ram_d0_d1_d3_equal=True,mmio_writes=0,stack_rts_endpoint_equal=True,carry_sequences=sequences,player_caller_integrations=integrations,results=rows,area_results=areas,negative_results=negatives,scope='Actual2790/3ef2 initialized fixtures; controlled source records and callbacks. Allactive IDs1..255 use the exact4092-byte read window; ID0nativeTRAP excluded and tested as transactional error. Full RAM and D0..D6 compared at helper/snapshot return. Area tails execute every original callee and stop479fe before continuation body or return475ca. Area API exposes only D0/D1/D3; remaining registers are native fixture state, not C++ output. Explicit selectors supplied between read/snapshot CLIcarry calls. No natural scheduling, other CPU registers/CCR or hardware timing claims.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),area_cases=len(areas),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

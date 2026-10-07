"""Actual47742/476dc player selection, cleanup/restart and RNG differential."""
import hashlib,itertools,json,struct,subprocess
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_palette_state import call
from verify_stage_catalog import SOURCE_SHA256,checked_resource
BASE,STACK,RETURN=0x100000,0x1feffc,0xff000
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D3,m.UC_M68K_REG_A6)
KEYS=('d0','d1','d3','a6')
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 folder=root/'artifacts/stage_players';folder.mkdir(parents=True,exist_ok=True)
 inp,out,portfile,report=[folder/n for n in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/step_stage_players';binary=hashlib.sha256(exe.read_bytes()).hexdigest();resource=root/'extracted/runtime/stage_players.ms5d';resource_sha=checked_resource(resource,program,0x476bc,0x47acc)
 state={'stop':RETURN}
 cpu=make_cpu(program);cpu.mem_map(0x300000,0x1000);trace,paths,rows,negatives,sequences=[],[],[],[],[]
 def code(cpu,address,size,user):
  if address==state['stop']:cpu.emu_stop()
  elif address in (0x289e,0x2a48,0x2a28,0x1bd2e,0x49a58,0x8ff4,0x43e38):paths.append(address)
 def write(cpu,access,address,size,value,user):
  if address==0x300001:assert size==1;trace.append((size,address,value&255))
  else:assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 cpu.mem_write(BASE,bytes(65536));call(cpu,0x2790);call(cpu,0x3ef2);cpu.reg_write(m.UC_M68K_REG_D0,0);call(cpu,0x49a1a);boot=bytes(cpu.mem_read(BASE,65536))
 def fixture(active=0,gates=0,stage=6,area=0,cursor=0x10d720):
  ram=bytearray(boot)
  for index,obj in enumerate((0xcb8,0xda8)):struct.pack_into('>I',ram,obj,0 if active&(1<<index) else 0x270e)
  for index,obj in enumerate((0x9a8,0xa6c)):struct.pack_into('>I',ram,obj,0 if gates&(1<<index) else 0x270e)
  ram[0xbac]=stage;ram[0xbad]=area;struct.pack_into('>I',ram,0xd722,cursor)
  return ram
 def args(entry,values,selected=resource):return [str(exe),str(entry)]+list(map(str,values))+list(map(str,(inp,out,portfile,selected)))
 def compare(ram,entry,values,label,context=None):
  if context is None:
   cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  else:
   cpu.context_restore(context)
   assert cpu.reg_read(m.UC_M68K_REG_PC)==entry and cpu.reg_read(m.UC_M68K_REG_A5)==0x108000 and cpu.reg_read(m.UC_M68K_REG_A7)==STACK
   assert bytes(cpu.mem_read(STACK,4))==RETURN.to_bytes(4,'big')
  cpu.mem_write(BASE,bytes(ram))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  state['stop']=0x479d0 if entry==0x479ba else RETURN
  trace.clear();paths.clear();cpu.emu_start(entry,0xffffff,count=100000)
  assert cpu.reg_read(m.UC_M68K_REG_PC)==state['stop'] and cpu.reg_read(m.UC_M68K_REG_A7)==(STACK if entry==0x479ba else STACK+4)
  expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result['writes']=len(trace)
  inp.write_bytes(ram);actual=subprocess.run(args(entry,values),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();ports=b''.join(struct.pack('>BII',*event) for event in trace)
  if actual_ram!=expected or parsed!=result or portfile.read_bytes()!=ports:
   diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,hex(entry),values,diff[:20],result,parsed,trace)))
  rows.append(dict(profile=label,entry=entry,incoming=dict(zip(KEYS,values)),result=parsed,ports=trace.copy(),native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
  return bytearray(actual_ram),tuple(parsed[key] for key in KEYS)
 highs=((0,0,0),(0xabcd0000,0xfedc0000,0x87654321),(0xffff0000,0xffff0000,0xffffffff))
 for selector,choice,active,high in itertools.product((0,1,2,0xffff),(0,1,3,4,0x7fff,0x8000,0xffff),range(4),highs):
  compare(fixture(active),0x47742,(high[0]|selector,high[1]|choice,high[2],0x100b30),'single-selector-signed-choice-active-zero-callback')
 for stage in range(256):compare(fixture(gates=3,stage=stage,area=2),0x476dc,(0xabcd1234,0xfedc9876,0x87654321,0x100b30),'all-stage-bytes-gated-table-selection')
 for stage,area in itertools.product((6,7,8),range(256)):compare(fixture(gates=3,stage=stage,area=area),0x476dc,(0xffff1234,0xabcd9876,0x76543210,0x100b30),'all-area-bytes-actual-read-window-gated')
 for stage,area,gates,active in itertools.product((6,7,8),range(5),range(4),range(4)):
  known=(stage,area) in ((6,0),(6,1),(7,0),(7,1),(8,0))
  compare(fixture(active,gates,stage,area),0x476dc,(0xabcd1234,0xfedc9876,0x87654321,0x100b30),'known-leading-pairs-gates-and-player-actions' if known else 'controlled-pointer-code-overlap-pairs-natural-use-unproven')
  rows[-1].update(stage_byte=stage,area_byte=area,known_leading_pair=known,natural_use_proven=False)
 for cursor,selector in itertools.product((0x10d6b4,0x10d71e,0x10d720),(0,2)):
  ram=fixture(3,cursor=cursor);values=(0xabcd0000|selector,0xfedc0004,0x87654321,0x100b30);start=len(rows)
  for index in range(4):
   ram,values=compare(ram,0x47742,values,'actual-cli-rng-and-register-ram-carry')
   values=(values[0],(values[1]&0xffff0000)|4,values[2],values[3]) # Host requests another random choice.
  sequences.append(dict(calls=len(rows)-start,actual_cli_ram_full_registers_carried=True,host_input='D1.lowword=4 each subsequent call'))
 # Native palette acquisitions and coordinate stamp cleanup on signed removal path.
 for slot,shared in itertools.product(range(8),(False,True)):
  ram=fixture(3);cpu.mem_write(BASE,bytes(ram))
  for obj in ((0x100cb8,0x100da8) if shared else (0x100cb8,)):
   for identifier in (7,263):cpu.reg_write(m.UC_M68K_REG_A6,obj);cpu.reg_write(m.UC_M68K_REG_D0,identifier);cpu.reg_write(m.UC_M68K_REG_D1,0);call(cpu,0x8ebe)
  ram=bytearray(cpu.mem_read(BASE,65536));ram[0xd24]=slot;at=0xd4e6+slot*0x2c
  struct.pack_into('>5I',ram,at,0xffff0001,0x7fffffff,1,0x80000001,0);struct.pack_into('>II',ram,at+0x14,0x11112222,0x87654321);ram[at+0x24]=255;ram[0xd494]=0
  compare(ram,0x47742,(0xabcd0000,0xfedcffff,0x87654321,0x100b30),'signed-removal-real-palette-and-coordinate-cleanup')
 for flag in range(256):
  ram=fixture(gates=3);ram[0xd684]=flag
  compare(ram,0x479ba,(0xabcd1234,0xfedc9876,0x87654321,0x100b30),'all-caller-mask-bytes-gated')
 ram=fixture(gates=3);ram[0xd680]=6;ram[0xd681]=0;ram[0xd684]=3
 compare(ram,0x479ba,(0xabcd1234,0xfedc9876,0x87654321,0x10d604),'caller-d681-write-aliases-live-area')
 # Validate the actual predecessor and continue its native context at479ba.
 integrations=[]
 for mask in (0,3):
  ram=fixture(gates=3);ram[0xd684]=mask;values=(0xabcd1234,0xfedc9876,0x87654321,0x100b30)
  cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  state['stop']=0x479ba;trace.clear();cpu.emu_start(0x479b0,0xffffff,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==0x479ba and cpu.reg_read(m.UC_M68K_REG_A7)==STACK
  expected=bytes(cpu.mem_read(BASE,65536));expected_values=tuple(cpu.reg_read(reg)&0xffffffff for reg in REGS);context=cpu.context_save()
  inp.write_bytes(ram);command=[str(root/'build/step_stage_preparation'),'0x479b0']+list(map(str,values))+list(map(str,(inp,out,portfile,root/'extracted/runtime/main_startup.ms5d',root/'extracted/runtime/stage_palettes.ms5d')))
  actual=subprocess.run(command,capture_output=True,text=True);assert not actual.returncode,actual.stderr
  parsed=json.loads(actual.stdout);assert out.read_bytes()==expected and tuple(parsed[key] for key in KEYS)==expected_values and portfile.read_bytes()==b''.join(struct.pack('>BII',*event) for event in trace)
  ram,values=compare(bytearray(out.read_bytes()),0x479ba,tuple(parsed[key] for key in KEYS),'actual-preparation-cli-to-player-caller',context)
  integrations.append(dict(mask=mask,actual_cli_ram_full_registers_carried=True,native_predecessor_and_caller_same_context=True))
 sentinel=b'old-output\0\xff'
 def reject(ram,entry=0x47742,values=(0,4,0,0x100b30),selected=resource,label='invalid'):
  inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel);actual=subprocess.run(args(entry,values,selected),capture_output=True,text=True)
  assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel,(label,actual.stderr)
  negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
 for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
 for entry in (0,0x47740):reject(fixture(),entry=entry,label='unsupported-entry')
 for index,value in itertools.product(range(4),('-1','4294967296','0x','1x','')):
  values=[0,4,0,0x100b30];values[index]=value;reject(fixture(),values=values,label='invalid-uint32')
 for pointer in (0,0x100001,0x110000,0xffffffff):reject(fixture(3,cursor=pointer),label='invalid-used-random-cursor')
 for pointer in (0,0x100001,0x10ff3e,0xffffffff):reject(fixture(),entry=0x476dc,values=(0,0,0,pointer),label='invalid-wrapper-controller-span')
 ram=fixture(3);struct.pack_into('>H',ram,0xcc8,1);reject(ram,values=(0,0xffff,0,0x100b30),label='static-depth-native-trap-excluded')
 # First player restarts before the second signed-removal cleanup fails.
 ram=fixture(2,stage=6,area=0);ram[0xe14]=8;reject(ram,entry=0x476dc,label='wrapper-late-second-coordinate-transaction')
 badfile=folder/'bad.ms5d';badfile.write_bytes(b'bad');reject(fixture(),selected=badfile,label='malformed-resource')
 raw=bytearray(resource.read_bytes());raw[-1]^=1;badfile.write_bytes(raw);reject(fixture(),selected=badfile,label='resource-crc-error')
 ram=fixture(3);ram[0xd24]=8;reject(ram,values=(0,0xffff,0,0x100b30),label='invalid-used-coordinate-slot')
 ram=fixture(3);ram[0xcd5]=5;reject(ram,values=(0,0xffff,0,0x100b30),label='invalid-palette-count')
 for kind in ('same','hardlink','symlink'):
  ram=fixture();inp.write_bytes(ram);portfile.write_bytes(sentinel);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True)
   if kind=='hardlink':alias.hardlink_to(inp)
   else:alias.symlink_to(inp)
  command=args(0x47742,(0,4,0,0x100b30));command[7]=str(alias);actual=subprocess.run(command,capture_output=True,text=True)
  assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
  negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
 assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 observed=set(pc for row in rows for pc in row['native_calls']);assert {0x2a48,0x2a28,0x1bd2e,0x49a58,0x8ff4,0x43e38}<=observed
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,resource_sha256=resource_sha,cases=len(rows),ports=sum(row['result']['writes'] for row in rows),negative_cases=len(negatives),program_code_modified=False,full_ram_d0_d1_d3_a6_ordered_ports_equal=True,stack_rts_endpoint_equal=True,carry_sequences=sequences,preparation_integrations=integrations,results=rows,negative_results=negatives,scope='Actual2790/3ef2/49a1a establish runtime fixtures. Callback0 is active; helpers execute original restart/removal/selector/RNG code. All256 stage and area byte cases deliberately gate off helper calls to isolate actual pointer/window reads; 1040-byte MS5D is a read-address window, not a logical256-area table. Known leading pairs are(6,0),(6,1),(7,0),(7,1),(8,0); remaining selected area0..4 pairs are controlled pointer/code-overlap fixtures whose natural use is unproven. Both categories exercise helpers and are recorded separately. Predecessor integrations continue the original CPU context without resetting A5/A7/SR or the external return stack; only actual CLI RAM/exposed registers are carried. CLI outputs carry RAM/registers; repeated RNG choice requests are explicit host D1.lowword changes. No game scheduler, callbackbody, arbitrary other register/CCR or timing claims.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),ports=sum(row['result']['writes'] for row in rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

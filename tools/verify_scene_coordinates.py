"""Full-register node primitives and actual1a7a8 coordinate prefix."""
import hashlib,itertools,json,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_scene_command import REGS,KEYS
from verify_scene_node import ENTRIES
from verify_stage_catalog import SOURCE_SHA256
BASE,STACK,RETURN,PREFIX,STOP=0x100000,0x1feffc,0xff000,0x1a7a8,0x1a8ca
NODES=(0xd38e,0x9156,0xb1d6,0xd256,0xd2d6)

def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256 and len(ENTRIES)==10
 folder=root/'artifacts/scene_coordinates';folder.mkdir(parents=True,exist_ok=True);inp,out,report=[folder/n for n in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
 executables={False:root/'build/step_scene_node_registers',True:root/'build/update_scene_coordinates'};binaries={str(k):hashlib.sha256(v.read_bytes()).hexdigest() for k,v in executables.items()}
 cpu=make_cpu(program);state={'stop':RETURN};paths=[];rows=[];negatives=[];sequences=[]
 def code(cpu,address,size,user):
  if address==state['stop']:cpu.emu_stop()
  elif address in ENTRIES:paths.append(address)
 def write(cpu,access,address,size,value,user):assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 highs=((0,)*12,(0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xfeedbeef))
 def put_node(ram,node,parent,variant):
  data=((0x00000000,0x00000000,0,0),(0xffff00ff,0x7fff00ff,0x00010001,0x8000ffff),(0x7fffffff,0x80000001,0xffff0001,0x7fff0001),(0x8000ffff,0xffffffff,0x800000ff,0xffff00ff))[variant%4]
  struct.pack_into('>5I',ram,node,*data,parent);struct.pack_into('>4I',ram,node+0x14,0x12345678,0x87654321,0x7fffffff,0x80000000);ram[node+0x24]=0 if variant%2 else 0xff;ram[node+0x25]=0xa0
  factor=(0,1,0x7fff,0x8000,0xffff,0x100)[variant%6];struct.pack_into('>HH',ram,node+0x28,factor,factor);ram[node+0x2c]=ram[node+0x2d]=(0,1,255)[variant%3]
 def fixture(node=0x1000,parent=0,variant=0):
  ram=bytearray(hashlib.shake_256(b'scene-coordinates'+variant.to_bytes(2,'big')).digest(65536));put_node(ram,node,parent,variant)
  if parent and parent!=BASE+node:
   struct.pack_into('>II',ram,parent-BASE+0x14,0x00010001,0x80000001);ram[parent-BASE+0x25]=0x40
  ram[0xd494]=(0,1,255)[variant%3];return ram
 def coordinates(mask,variant):
  ram=bytearray(hashlib.shake_256(b'scene-coordinate-prefix'+variant.to_bytes(2,'big')).digest(65536));put_node(ram,0x2000,0,variant)
  for index,node in enumerate(NODES):
   parent=0 if variant%4==0 else BASE+NODES[0] if variant%4==1 and index else BASE+node if variant%4==2 else BASE+0x2000
   put_node(ram,node,parent,variant+index)
  struct.pack_into('>II',ram,0xd3bc,((0,0xffff0001,0x80000000,0x7fffffff)[variant%4]),((0,0x7fffffff,0xffffffff,0x80000001)[variant%4]));struct.pack_into('>H',ram,0xd404,(0,1,0x7fff,0x8000,0xffff)[variant%5]);ram[0xd40c]=mask;ram[0xd494]=(0,1,255)[variant%3];return ram
 def args(prefix,entry,values):return [str(executables[prefix])]+([] if prefix else [str(entry)])+list(map(str,values))+list(map(str,(inp,out)))
 def compare(ram,entry,values,label):
  prefix=entry==PREFIX;state['stop']=STOP if prefix else RETURN;cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A3,0);cpu.reg_write(m.UC_M68K_REG_A6,0);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  paths.clear();cpu.emu_start(entry,0xffffff,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==state['stop'] and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+(0 if prefix else 4)
  expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
  inp.write_bytes(ram);actual=subprocess.run(args(prefix,entry,values),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr);parsed=json.loads(actual.stdout);actual_ram=out.read_bytes()
  assert expected==actual_ram and result==parsed,(label,hex(entry),values,[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b][:20],result,parsed)
  rows.append(dict(profile=label,entry_cpu_address=entry,stop_cpu_address=state['stop'],incoming=dict(zip(KEYS,values)),result=parsed,native_calls=paths.copy(),ram_sha256=hashlib.sha256(expected).hexdigest(),a7_verified=True));assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
  return bytearray(actual_ram),tuple(parsed[key] for key in KEYS)
 for entry,node,profile,variant in itertools.product(ENTRIES,(0x1000,0x9156,0xb1d6,0xd256,0xd2d6),range(2),range(4)):
  values=list(highs[profile]);values[8]=BASE+node;values[9]=0;compare(fixture(node,0,variant),entry,values,'all-ten-leaf-entries-real-node-full-registers')
 for entry,parent,node,variant in itertools.product((0x43e22,0x16fee,0x43e38,0x43ea8,0x1728c),(0,0x102000,0x101000,0x101004,0x10d480),(0x1000,0xd480),range(6)):
  ram=fixture(node,parent,variant);values=list(highs[1]);values[0]=(0xffff0000,0x7fffffff,0x80000001,0xffffffff)[variant%4];values[1]=(0x7fff0000,0x800000ff,0xffffffff,0xffff00ff)[variant%4];values[8]=BASE+node;values[9]=parent;compare(ram,entry,values,'leaf-parent-overlap-self-stamp-alias-carry')
 for entry,factor,high,low,fraction in itertools.product((0x1724c,0x1726c),(0,1,0x100,0x7fff,0x8000,0xffff),(0,0x7fff,0x8000,0xffff),(0,0xff,0xffff),(0,1,255)):
  ram=fixture();struct.pack_into('>HH',ram,0x1028,factor,factor);ram[0x102c]=ram[0x102d]=fraction;values=list(highs[1]);values[0]=values[1]=(high<<16)|low;values[8]=0x101000;compare(ram,entry,values,'scale-full-scratch-mul-ASR-fraction-overflow')
 for mask,variant,profile in itertools.product(range(256),range(8),range(2)):compare(coordinates(mask,variant),PREFIX,highs[profile],'actual-prefix-all256masks-offset-factor-fraction-parent-stamp')
 for mask in (0,0x55,0xaa,0xff):
  ram=coordinates(mask,3);values=highs[1];first=len(rows)
  for frame in range(5):ram,values=compare(ram,PREFIX,values,'actual-cli-prefix-ram-full-register-carry')
  sequences.append(dict(mask=mask,calls=5,first_result_index=first,actual_cli_ram_full_registers_carried=True,entry_stack_sr_reset_between_calls=True))
 sentinel=b'old-coordinate-output\0\xff'
 def reject(ram,entry,values,label):
  inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run(args(entry==PREFIX,entry,values),capture_output=True,text=True);assert actual.returncode and out.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stderr);negatives.append(dict(failure=label,output_preserved=True,native_executed=False))
 for entry in (PREFIX,0x43e38):
  for size in (0,65535,65537):reject(bytes(size),entry,highs[1],'invalid-ram-size')
  for index,text in itertools.product(range(12),('-1','4294967296','0x','1x','')):
   values=list(highs[1]);values[8]=0x101000;values[9]=0;values[index]=text;reject(coordinates(0,0) if entry==PREFIX else fixture(),entry,values,'invalid-register-parser')
 for pointer in (1,0x100001,0x10fff0,0xffffffff):
  ram=coordinates(0,0);struct.pack_into('>I',ram,NODES[-1]+0x10,pointer);reject(ram,PREFIX,highs[1],'late-last-node-invalid-parent-rollback')
  values=list(highs[1]);values[8]=0x101000;values[9]=pointer;reject(fixture(),0x16fee,values,'set-late-invalid-parent-rollback')
 inp.write_bytes(coordinates(0,0));before=inp.read_bytes();line=args(True,PREFIX,highs[1]);line[-1]=str(inp);actual=subprocess.run(line,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==before;negatives.append(dict(failure='input-output-alias',output_preserved=True))
 assert all(hashlib.sha256(v.read_bytes()).hexdigest()==binaries[str(k)] for k,v in executables.items())
 report.write_text(json.dumps(dict(source=source,binary_sha256=binaries,cases=len(rows),leaf_cases=sum(row['entry_cpu_address']!=PREFIX for row in rows),prefix_cases=sum(row['entry_cpu_address']==PREFIX for row in rows),negative_cases=len(negatives),mmio_writes=0,full_ram_12_registers_and_a7_equal=True,original_rom_immutable=True,results=rows,negative_results=negatives,carry_sequences=sequences,scope='Actual tenleaf entries throughRTS and1a7a8 through1a8ca before1afda and four19e64 calls. Prefix internalcalls execute continuously withoutcontextreset; prefixA7=initialSP,leafA7=SP+4. Initialized camera/nodes and parent/self/overlap/stamp aliases are controlled fixtures, not scene/frame scheduler. ActualCLI RAM/fullregister outputs carry with externalstack/SR resets between calls only. MMIO forbidden; originalROMunchanged.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

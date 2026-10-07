"""Native19938 motion evaluation, strict canonical and relocated RAM synthetic paths."""
import hashlib,itertools,json,struct,subprocess,zlib
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_scene_command import REGS,KEYS
from verify_stage_catalog import SOURCE_SHA256,checked_resource
BASE,STACK,RETURN,ENTRY=0x100000,0x1feffc,0xff000,0x19938
SCRATCH,FIXED=0x106000,0x60000

def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 scripts=root/'extracted/runtime/scene_scripts';manifest=json.loads((scripts/'manifest.json').read_text());paths=[]
 for item in manifest['dependencies']:
  if item['file'].startswith('motion_'):
   path=scripts/item['file'];checked_resource(path,program,item['source_cpu_address'],item['end_exclusive']);paths.append((path,item['source_cpu_address'],path.read_bytes()[32:]))
 assert len(paths)==37
 folder=root/'artifacts/scene_motion';folder.mkdir(parents=True,exist_ok=True);inp,out,report=[folder/name for name in ('input.bin','cpp.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/evaluate_scene_motion';binary=hashlib.sha256(exe.read_bytes()).hexdigest();cpu=make_cpu(program);rows=[];limits=[];negatives=[];sequences=[];writes=[];visited=[];type_sets={False:set(),True:set()};mode={'relocated':False}
 def code(cpu,address,size,user):
  if address==RETURN:cpu.emu_stop()
  elif address in (0x196ac,0x196de,0x19710,0x1971c,0x1972a,0x18fd2,0x18c06):visited.append(address)
  if address==0x18fd2:type_sets[mode['relocated']].add(int.from_bytes(cpu.mem_read(cpu.reg_read(m.UC_M68K_REG_A1)+2,2),'big'))
 def write(cpu,access,address,size,value,user):
  assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value)
  writes.append((size,address,value&((1<<(size*8))-1)))
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 offsets=((0,0),(0x7fff,0x8000),(0xffff,0xffff),(0x8000,0x7fff))
 highs=((0,)*12,(0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xfeedbeef))
 def fixture(cursor,index):
  ram=bytearray(hashlib.shake_256(b'scene-motion'+bytes([index%4])).digest(65536));struct.pack_into('>IHH',ram,0xd3b4,cursor,*offsets[index%4]);return ram
 def compare(ram,values,path,label,relocated=False):
  mode['relocated']=relocated;native_ram=bytearray(ram)
  if relocated:
   pointer=int.from_bytes(native_ram[0xd3b4:0xd3b8],'big');struct.pack_into('>I',native_ram,0xd3b4,SCRATCH+pointer-FIXED)
  cpu.mem_write(BASE,bytes(native_ram));cpu.reg_write(m.UC_M68K_REG_A3,0);cpu.reg_write(m.UC_M68K_REG_A6,0);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  visited.clear();writes.clear();error=None
  try:cpu.emu_start(ENTRY,0xffffff,count=100000)
  except unicorn.UcError as failure:error=str(failure)
  assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
  if cpu.reg_read(m.UC_M68K_REG_PC)!=RETURN:
   limits.append(dict(profile=label,cursor=int.from_bytes(ram[0xd3b4:0xd3b8],'big'),d7=values[7],pc=cpu.reg_read(m.UC_M68K_REG_PC),error=error,instruction_cap=100000,native_returned=False,cpp_comparison_performed=False,relocated=relocated,path_file=path.name));return None
  assert cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
  expected=bytearray(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
  if relocated:
   struct.pack_into('>I',expected,0xd3b4,int.from_bytes(expected[0xd3b4:0xd3b8],'big')-SCRATCH+FIXED);result['a1']=result['a1']-SCRATCH+FIXED
  inp.write_bytes(ram);actual=subprocess.run([str(exe)]+list(map(str,values))+list(map(str,(inp,out,path))),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);output=out.read_bytes()
  assert parsed==result and output==expected,(label,path.name,values,[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,output)) if a!=b][:20],result,parsed)
  rows.append(dict(profile=label,path_file=path.name,cursor=int.from_bytes(ram[0xd3b4:0xd3b8],'big'),incoming=dict(zip(KEYS,values)),result=parsed,ram_sha256=hashlib.sha256(output).hexdigest(),native_calls=visited.copy(),relocated=relocated,mmio_writes=0,native_a7_rts_valid=True,synthetic_payload_hex=path.read_bytes()[32:].hex() if relocated else None,synthetic_payload_sha256=hashlib.sha256(path.read_bytes()[32:]).hexdigest() if relocated else None))
  return bytearray(output),tuple(parsed[key] for key in KEYS)
 for path,address,data in paths:
  count=(len(data)-4)//10
  for record in range(count):
   time,nexttime=struct.unpack_from('>H',data,record*10)[0],struct.unpack_from('>H',data,(record+1)*10)[0]
   phases=sorted({(value+delta)&65535 for value in (time,nexttime) for delta in (-1,0,1)})
   for phase,fraction,profile in itertools.product(phases,(0,1,0x8000,0xffff),range(2)):
    values=list(highs[profile]);values[7]=(phase<<16)|fraction;compare(fixture(address+record*10,record+phase+fraction),values,path,'canonical-record-time-nexttime-fraction-high-registers')
  for direction in (1,-1):
   phases=[struct.unpack_from('>H',data,index*10)[0] for index in range(count+1)];phases=phases if direction==1 else phases[::-1];ram=fixture(address+(0 if direction==1 else count-1)*10,direction);values=highs[1];first=len(rows);calls=0
   for phase in phases:
    values=list(values);values[7]=(phase<<16)|0x8000;result=compare(ram,values,path,'actual-cli-carry-forward-backward-host-d7-update')
    if result is None:break
    ram,values=result;calls+=1
   sequences.append(dict(path_file=path.name,direction=direction,calls=calls,first_result_index=first,cli_ram_full_registers_carried=True,host_d7_update_only=True,entry_context_reset_between_calls=True))
 path=paths[0][0]
 for index,profile in itertools.product(range(4),range(2)):compare(fixture(0,index),highs[profile],path,'null-path-no-resource-use')
 # All36 dispatch types use RAM-native paths; only A1 and RAMd3b4 are relocated.
 synthetic=folder/'synthetic.ms5d'
 for type_word,variant in itertools.product(range(0,0x90,4),range(4)):
  dx,dy=offsets[variant];data=b''.join(struct.pack('>5H',time,kind,10,x,y) for time,kind,x,y in ((0,0x14,0xffff,0x8000),(10,type_word,dx,dy),(20,0x14,0x7fff,1)))+struct.pack('>2H',30,0xffff)
  synthetic.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,FIXED,FIXED,len(data),zlib.crc32(data)&0xffffffff,0)+data)
  for cursor,phase,fraction in itertools.product((0,10,20),(9,10,11,19,20),(1,0x8000,0xffff)):
   ram=fixture(FIXED+cursor,variant);ram[SCRATCH-BASE:SCRATCH-BASE+len(data)]=data;values=list(highs[1]);values[7]=(phase<<16)|fraction;compare(ram,values,synthetic,'relocated-RAM-synthetic-all36-types-overflow-ASR-fractions',True)
 # N16 subtraction, rather than signed relational comparison, selects direction.
 for middle,nexttime,terminal in ((0x7000,0x7100,0x7200),(0xf000,0xf100,0xf200)):
  data=b''.join(struct.pack('>5H',time,kind,10,x,y) for time,kind,x,y in ((0,0x14,0xffff,0x8000),(middle,8,0x7fff,0xffff),(nexttime,0x14,0x8000,1)))+struct.pack('>2H',terminal,0xffff)
  synthetic.write_bytes(struct.pack('<4s7I',b'MS5D',1,1,FIXED,FIXED,len(data),zlib.crc32(data)&0xffffffff,0)+data)
  for cursor,phase,fraction,profile in itertools.product((10,20),(0x7000,0x7100,0x7fff,0x8000,0xf000,0xf100,0xffff),(0,1,0x8000,0xffff),range(2)):
   ram=fixture(FIXED+cursor,profile);ram[SCRATCH-BASE:SCRATCH-BASE+len(data)]=data;values=list(highs[profile]);values[7]=(phase<<16)|fraction;compare(ram,values,synthetic,'relocated-RAM-N16-subtraction-overflow-direction-boundaries',True)
 sentinel=b'previous-motion-output\0\xff'
 def reject(ram,values,path,label):
  inp.write_bytes(ram);out.write_bytes(sentinel);actual=subprocess.run([str(exe)]+list(map(str,values))+list(map(str,(inp,out,path))),capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram and out.read_bytes()==sentinel,(label,actual.stderr);negatives.append(dict(failure=label,output_preserved=True,native_executed=False))
 path,address,data=paths[0];ram=fixture(address,0)
 for size in (0,65535,65537):reject(bytes(size),highs[1],path,'invalid-ram-size')
 for index,text in itertools.product(range(12),('-1','4294967296','0x','1x','')):
  values=list(highs[1]);values[index]=text;reject(ram,values,path,'invalid-register-parser')
 for cursor in (address-1,address+1,address+len(data),0xffffffff):reject(fixture(cursor,0),highs[1],path,'invalid-cursor')
 malformed=folder/'bad.ms5d';malformed.write_bytes(b'bad');reject(ram,highs[1],malformed,'malformed-resource')
 inp.write_bytes(ram);actual=subprocess.run([str(exe)]+list(map(str,highs[1]))+list(map(str,(inp,inp,path))),capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram;negatives.append(dict(failure='input-output-alias',output_preserved=True,native_executed=False))
 assert hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 assert type_sets[True]==set(range(0,0x90,4)),type_sets
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,cases=len(rows),canonical_cases=sum(not row['relocated'] for row in rows),relocated_synthetic_cases=sum(row['relocated'] for row in rows),negative_cases=len(negatives),native_nonreturns=len(limits),canonical_observed_types=sorted(type_sets[False]),synthetic_observed_types=sorted(type_sets[True]),limit_observations=limits,results=rows,negative_results=negatives,carry_sequences=sequences,mmio_writes=0,fixed_rom_immutable=True,scope='Actual19938 throughRTS, fullRAM12regs andA7. Canonical paths compare strict addresses. Synthetic rawthree-record paths live atRAM106000, same scratchbytes in bothRAMs, CPP fixedMS5D source60000; normalize only outgoingA1 andRAMd3b4. NoROMpatch;36types synthetic, canonical11types. Native countcap/nonreturn cases excluded from passing comparison. HostD7 updates/call-boundary stackSR resets explicit; no natural motion/frame scheduling claim.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),native_nonreturns=len(limits),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

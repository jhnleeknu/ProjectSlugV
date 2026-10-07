"""Continuous original scene path execution observations; controlled fixtures only."""
import argparse,base64,collections,hashlib,itertools,json,struct,zlib
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program
from verify_stage_catalog import SOURCE_SHA256
from verify_object_reset import make_cpu
from observe_scene_map_transfer import NAMES,REGS,BASE,NODE,STACK,RETURN
META=0x10d356

def fixture(index,case):
 ram=bytearray(hashlib.shake_256(b'scene-path-execution-native'+struct.pack('>I',index)).digest(65536));at=NODE-BASE
 for offset,value in ((0x26,case.get('slot',0xffff)),(0x14,case.get('current_x',0)),(0x18,case.get('current_y',0)),(0x1c,case.get('old_x',0)),(0x20,case.get('old_y',0)),(0x32,case.get('origin_x',-6)),(0x34,case.get('origin_y',39))):struct.pack_into('>H',ram,at+offset,value&65535)
 struct.pack_into('>I',ram,at+0x2e,case.get('old_descriptor',0));struct.pack_into('>I',ram,at+0x36,0)
 ram[at+0x3a:at+0x7a]=bytes((0,1,7,0xf8,0xff)[(i+case['profile'])%5] for i in range(64));ram[at+0x7a]=case.get('node_flags',0)
 struct.pack_into('>IhhhhH',ram,META-BASE,case.get('cursor',0),case.get('meta_x',-6),case.get('meta_y',39),case.get('meta_dx',0),case.get('meta_dy',0),case.get('meta_flags',0)&65535)
 if case.get('stream_hex'):ram[0x6000:0x6000+len(bytes.fromhex(case['stream_hex']))]=bytes.fromhex(case['stream_hex'])
 if case.get('target_hex'):ram[0x6100:0x6100+len(bytes.fromhex(case['target_hex']))]=bytes.fromhex(case['target_hex'])
 return ram

def build_cases(program,root):
 inventory=json.loads((root/'artifacts/scene_paths/inventory.json').read_text());unique={r['cpu_address']:r for p in inventory['paths'] for r in p['rows']};descriptors=[r['descriptor_cpu_address'] for p in inventory['paths'] for r in p['rows'] if r['opcode_word']==4];descriptor=descriptors[0];cases=[]
 def add(entry,**kw):
  c=dict(entry=entry,profile=0,label='canonical',cursor=0,old_descriptor=0);c.update(kw);cases.append(c)
 for cursor,row in sorted(unique.items()):
  for old,profile,moving in itertools.product((0,descriptor),range(2),(False,True)):
   add(0x19e64,cursor=cursor,old_descriptor=old,profile=profile,node_flags=6 if moving else 0,old_x=-16 if moving else 0,old_y=16 if moving else 0,meta_flags=(0x0bff,0x70a5)[profile],meta_dx=(0,1)[profile],meta_dy=(0,-1)[profile],label='canonical218-cursors-full-handler-effects')
 for cursor,profile in itertools.product((p['root_cpu_address'] for p in inventory['paths']),range(2)):
  add(0x19e64,cursor=cursor,profile=profile,slot=0,node_flags=0,label='canonical72-whole-paths-primary-video-enabled')
 for profile in range(2):add(0x19e64,profile=profile,cursor=0,old_descriptor=descriptor,node_flags=6,label='null-cursor-bypasses-moved-refresh')
 for x,y,profile in itertools.product((0,0x7ff,0x800,0xfff,0x1000,0x8000,0xffff),(0,0x7ff,0x800,0xfff,0xffff),range(2)):
  add(0x16ff8,profile=profile,input_x=x,input_y=y,map_pointer=descriptor,column_pointer=(0,0xffffffff)[profile],label='signed12bit-node-map-origin')
 # RAM synthetic branch programs use original handlers and untouched fixed code.
 target=struct.pack('>HHHHHHH',0x18,0x80f1,1,2,0x1c,3,4)+b'\xff\xff'
 for opcode,current,old,threshold,profile in itertools.product((8,12,16,20),(0,0x7fff,0x8000,0xffff),(0,1,0xffff),(0,1,0x7fff,0x8000,0xffff),range(2)):
  stream=struct.pack('>HHHHHIH',opcode,threshold,0xa531,0x8000,0x7fff,0x106100,0xffff)
  add(0x19e64,cursor=0x106000,old_descriptor=descriptor,profile=profile,current_x=current,current_y=current,old_x=old,old_y=old,origin_x=-6,origin_y=39,meta_flags=0x0b55,stream_hex=stream.hex(),target_hex=target.hex(),branch_opcode=opcode,label='RAM-synthetic-conditional-N-only-and-TST-signed-threshold-wrap')
 for opcode,profile in itertools.product((0,0x18,0x1c),range(2)):
  stream=(struct.pack('>HHH',0,0x8000,0x7fff) if opcode==0 else struct.pack('>HHHH',opcode,0xa531,0x8000,0x7fff) if opcode==0x18 else struct.pack('>HHH',opcode,0x8000,0x7fff))+b'\xff\xff'
  add(0x19e64,cursor=0x106000,profile=profile,stream_hex=stream.hex(),meta_flags=0x0b55,label='RAM-synthetic-metadata-reset-OR-word-add')
 selected=next(cursor for cursor,row in sorted(unique.items()) if row['opcode_word']==4)
 for flag_high,old in itertools.product(range(256),(0,descriptor)):
  add(0x19e64,cursor=selected,old_descriptor=old,profile=0,slot=0xffff,node_flags=0,meta_flags=(flag_high<<8)|0xa5,meta_dx=1,meta_dy=-1,label='canonical04-all256-metadata-highbyte-oldmap-null-or-nonnull')
 return cases

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');o=parser.parse_args();root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256;cases=build_cases(program,root)
 if o.smoke:cases=[next(c for c in cases if c['entry']==entry) for entry in (0x16ff8,0x19e64)]
 folder=root/'artifacts/scene_path_execution';folder.mkdir(parents=True,exist_ok=True);report=folder/'observation.json';report.unlink(missing_ok=True)
 cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);baseline=cpu.context_save();ports=[];visits=[];rows=[];start_index=0;state=dict(bank=0x200000,error=None,count=0)
 def code(cpu,address,size,user):
  state['count']+=1
  if address==RETURN:cpu.emu_stop();return
  if address in (0x19e64,0x19e74,0x19e7e,0x19e84,0x19eaa,0x19ec2,0x19ed0,0x19f9e,0x19fc4,0x19ff4,0x1a01c,0x1a04a,0x1a060,0x1a068,0x16ff8,0x1861a,0x18656,0x18702,0x183c6):visits.append(address)
  word=int.from_bytes(cpu.mem_read(address,2),'big')
  if word==0x4afc or 0x4e40<=word<=0x4e4f:state['error']=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
 def write(cpu,access,address,size,value,user):
  if BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4:return
  if address not in (0x2ffff2,0x2ffff0,0x3c0000,0x300001):state['error']=dict(kind='unexpected-write',address=address,size=size,value=value);cpu.emu_stop();return
  ports.append((size,address,value&((1<<(8*size))-1)))
  if address==0x2ffff2:
   if size!=2 or value not in (0x1000,0x2000):state['error']=dict(kind='unsupported-bank-write',value=value);cpu.emu_stop();return
   state['bank']=0x200000 if value==0x1000 else 0x300000;cpu.mem_write(0x200000,program[state['bank']:state['bank']+0xffff0])
 def invalid(cpu,access,address,size,value,user):state['error']=dict(kind='invalid-memory',access=access,address=address,size=size);return False
 def intr(cpu,number,user):state['error']=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_INVALID,invalid);cpu.hook_add(UC_HOOK_INTR,intr)
 def save():
  report.write_text(json.dumps(dict(source=source,smoke=o.smoke,cases=len(rows),completed_cases=sum(r['returned'] for r in rows),ports=sum(r['port_count'] for r in rows),results=rows,failure=state['error'],scope='Native-only continuous standalone calls; baselinecontext restored beforecall only. Canonicalfixed pathcursors and explicitly labeled RAMsyntheticbranch streams; no natural scheduler/mapstreaming or C++ equivalence claim. CPUwindow initiallybank2, PVC1000/2000 selects original2MiB/3MiB physical payload excludingtailMMIO overlay. FullRAMdelta and deterministicinput reproducecases; all13contractregs plusremainingregs/stack recorded. RawSR is observation only.',fixed_rom_immutable=True,physical_bank_payload_immutable=True),indent=2)+'\n');return hashlib.sha256(report.read_bytes()).hexdigest()
 for index,case in enumerate(cases,start_index):
  cpu.context_restore(baseline);ram=fixture(index,case);cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,program[0x200000:0x2ffff0]);cpu.mem_write(STACK-128,b'\xa5'*128+RETURN.to_bytes(4,'big'));state.update(bank=0x200000,error=None,count=0);ports.clear();visits.clear()
  values=[0 if not case['profile'] else (0xabcd0000+i*0x111100)&0xffffffff for i in range(16)]
  if case['entry']==0x16ff8:
   values[0]=(values[0]&0xffff0000)|case['input_x'];values[1]=(values[1]&0xffff0000)|case['input_y']
  values[8]=NODE;values[9]=case.get('map_pointer',META);values[10]=case.get('column_pointer',values[10]);values[13]=0x108000;values[15]=STACK
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  cpu.reg_write(m.UC_M68K_REG_SR,0x2000)
  try:cpu.emu_start(case['entry'],0xffffff,count=2000000)
  except unicorn.UcError as error:
   if state['error'] is None:state['error']=dict(kind='emulator-error',message=str(error))
  returned=cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
  if not returned and state['error'] is None:state['error']=dict(kind='instruction-cap',cap=2000000,pc=cpu.reg_read(m.UC_M68K_REG_PC))
  output=bytes(cpu.mem_read(BASE,65536));delta=[];at=0
  while at<65536:
   if ram[at]==output[at]:at+=1;continue
   start=at
   while at<65536 and ram[at]!=output[at]:at+=1
   delta.append(dict(ram_offset=start,before_hex=ram[start:at].hex(),after_hex=output[start:at].hex()))
  packed=b''.join(struct.pack('>BII',*event) for event in ports);final=dict(zip(NAMES,(cpu.reg_read(r)&0xffffffff for r in REGS)))
  rows.append(dict(case_index=index,fixture=case,incoming=dict(zip(NAMES,values)),returned=returned,final_pc=cpu.reg_read(m.UC_M68K_REG_PC),final_registers=final,raw_sr=cpu.reg_read(m.UC_M68K_REG_SR),input_ram_sha256=hashlib.sha256(ram).hexdigest(),output_ram_sha256=hashlib.sha256(output).hexdigest(),ram_delta=delta,port_count=len(ports),ports_sha256=hashlib.sha256(packed).hexdigest(),ports_zlib_base64=base64.b64encode(zlib.compress(packed)).decode(),ports_prefix=ports[:8],boundary_pc_counts=dict(collections.Counter(visits)),instructions=state['count'],final_bank_source_rom=state['bank']))
  assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and bytes(cpu.mem_read(0x200000,0xffff0))==program[state['bank']:state['bank']+0xffff0]
  if state['error']:print(json.dumps(dict(cases=len(rows),failure=state['error'],sha256=save())));raise SystemExit(1)
  assert final['a7']==STACK+4
 print(json.dumps(dict(cases=len(rows),ports=sum(r['port_count'] for r in rows),sha256=save())))
if __name__=='__main__':main()

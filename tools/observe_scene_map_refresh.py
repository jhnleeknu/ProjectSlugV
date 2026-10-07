"""Native-only continuous map refresh observations, with reproducible host fixtures."""
import argparse,base64,collections,hashlib,itertools,json,struct,zlib
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from observe_scene_map_transfer import NAMES,REGS,BASE,NODE,STACK,RETURN

def fixture(index,case):
 ram=bytearray(hashlib.shake_256(b'scene-map-refresh-native'+struct.pack('>I',index)).digest(65536));at=NODE-BASE
 def word(offset,value):struct.pack_into('>H',ram,at+offset,value&65535)
 def long(offset,value):struct.pack_into('>I',ram,at+offset,value&0xffffffff)
 long(0x2e,case['descriptor']);long(0x36,case.get('column_pointer',0));word(0x26,case['slot']);word(0x32,case.get('origin_x',-6));word(0x34,case.get('origin_y',39))
 for offset,key in ((0x14,'current_x'),(0x18,'current_y'),(0x1c,'old_x'),(0x20,'old_y')):word(offset,case.get(key,0))
 ram[at+0x7a]=case['flags'];ram[at+0x3a:at+0x7a]=bytes((0,1,7,0xf8,0xff)[(i+case['profile'])%5] for i in range(64))
 if case.get('column_records'):ram[0x6000:0x6000+len(bytes.fromhex(case['column_records']))]=bytes.fromhex(case['column_records'])
 return ram

def build_cases(program,root):
 inventory=json.loads((root/'artifacts/scene_paths/inventory.json').read_text());descriptors={r['descriptor_cpu_address']:r for p in inventory['paths'] for r in p['rows'] if r['opcode_word']==4};assert len(descriptors)==72
 cases=[]
 def add(entry,address,**kw):
  case=dict(entry=entry,descriptor=address,slot=0,profile=0,flags=0,source_x=0,source_y=0,width=2,height=1,dest_x=0,dest_y=0,label='canonical');case.update(kw);cases.append(case)
 for address,row in sorted(descriptors.items()):
  for flags,profile,slot in itertools.product((0,8,16,24),range(2),(0,0xffff)):add(0x18702,address,flags=flags,profile=profile,slot=slot,label='all72-descriptors-four-wrapflags')
 reps=[next(a for a,r in sorted(descriptors.items()) if r['width_word']% (1 << (r['width_word'].bit_length()-1))),next(iter(sorted(descriptors)))]
 reps=list(dict.fromkeys(reps))
 for address in reps:
  r=descriptors[address];w,h=r['width_word'],r['height_word']
  for x,y,flags,profile in itertools.product((-1,0,w-1,w,w+1),(-1,0,h,h+1),(0,8,16,24),range(2)):add(0x18702,address,source_x=x,source_y=y,flags=flags,profile=profile,slot=0xffff,label='unsigned-divu-coordinate-boundaries')
  for flags,profile,slot in itertools.product((0,8,16,24),range(2),(0,0xffff)):add(0x1861a,address,flags=flags,profile=profile,slot=slot,label='literal32x32-refresh')
  for change,move,wrap,profile in itertools.product(range(7),(-512,-16,0,16,512),(0,8,16,24),range(2)):add(0x18656,address,flags=change|wrap,profile=profile,current_x=move,current_y=move,slot=0xffff,label='movement-changedbits-live-wrap')
 address=reps[0]
 for entry,profile in itertools.product((0x1861a,0x18656),range(2)):add(entry,0,profile=profile,label='null-descriptor-bypass')
 # Nonnull column cursor is a separate RAM fixture; canonical descriptors all have no column list.
 records='00000021000401ff0008020180000000'
 for pointer,source,count,profile in itertools.product((0,0xffffffff,0x106000,0x106004,0x106008),(0,3,4,7,8,10),(1,3),range(2)):
  add(0x16f0e,address,column_pointer=pointer,column_records=records,source_x=source,width=count,dest_x=31,origin_y=255,profile=profile,label='RAM-column-records-back-forward-default-sentinel')
 # D2=0 traverses the entire 16bit DBRA loop; descriptor bound skips protect reads.
 for pointer in (0,0xffffffff):add(0x16f0e,address,column_pointer=pointer,width=0,label='zero-count-DBRA-full-word-iteration')
 return cases

def extra_cases(root):
 inventory=json.loads((root/'artifacts/scene_paths/inventory.json').read_text());descriptors={r['descriptor_cpu_address']:r for p in inventory['paths'] for r in p['rows'] if r['opcode_word']==4}
 height_nonpower=next(a for a,r in sorted(descriptors.items()) if r['height_word'] & (r['height_word']-1))
 first=min(descriptors);alternate=next(a for a,r in sorted(descriptors.items()) if (r['width_word'],r['height_word'])!=(descriptors[first]['width_word'],descriptors[first]['height_word']))
 cases=[]
 for flag,profile in itertools.product((16,24),range(2)):
  cases.append(dict(entry=0x18702,descriptor=height_nonpower,slot=0xffff,profile=profile,flags=flag,source_x=0,source_y=-1,width=1,height=1,dest_x=0,dest_y=0,label='extra-unsignedDIVU-nonpower-height-ffff'))
 for flag,profile in itertools.product((8,16,24),range(2)):
  cases.append(dict(entry=0x18702,descriptor=first,prewrap_descriptor=alternate,slot=0xffff,profile=profile,flags=flag,source_x=-1,source_y=-1,width=1,height=1,dest_x=0,dest_y=0,label='extra-prewrap-A1-differs-live-node-descriptor'))
 return cases

def validate_extra_base(previous,source,cases):
 assert previous['source']==source and not previous['smoke'] and not previous['failure']
 assert previous['fixed_rom_immutable'] and previous['physical_bank_payload_immutable']
 assert previous['cases']==len(previous['results'])==previous['completed_cases']==len(cases)
 assert previous['ports']==sum(row['port_count'] for row in previous['results'])
 for index,(row,case) in enumerate(zip(previous['results'],cases)):
  assert row['case_index']==index and row['fixture']==case and row['returned']
  assert row['input_ram_sha256']==hashlib.sha256(fixture(index,case)).hexdigest()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--extra',action='store_true');o=parser.parse_args();root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);cases=build_cases(program,root)
 if o.smoke:cases=[next(c for c in cases if c['entry']==entry) for entry in (0x16f0e,0x18702,0x1861a,0x18656)]
 folder=root/'artifacts/scene_map_refresh';folder.mkdir(parents=True,exist_ok=True);report=folder/'observation.json';previous=json.loads(report.read_text()) if o.extra else None
 if not o.extra:report.unlink(missing_ok=True)
 if o.extra:
  assert not o.smoke
  validate_extra_base(previous,source,cases)
  cases=extra_cases(root)
 cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);baseline=cpu.context_save();ports=[];visits=[];rows=previous['results'] if previous else [];start_index=len(rows);state=dict(bank=0x200000,error=None,count=0)
 def code(cpu,address,size,user):
  state['count']+=1
  if address==RETURN:cpu.emu_stop();return
  if address in (0x16f0e,0x16f4e,0x16f5e,0x16f72,0x183c6,0x185f2,0x185f8,0x1861a,0x18656,0x186b2,0x18702,0x18714,0x18732):visits.append(address)
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
  report.write_text(json.dumps(dict(source=source,smoke=o.smoke,cases=len(rows),completed_cases=sum(r['returned'] for r in rows),ports=sum(r['port_count'] for r in rows),results=rows,failure=state['error'],scope='Native-only continuous standalone calls; baselinecontext restored beforecall only. Fixedcanonical descriptors plus explicitly labeled RAM column records; no natural scheduler/mapstreaming or C++ equivalence claim. CPUwindow initiallybank2, PVC1000/2000 selects original2MiB/3MiB physical payload excludingtailMMIO overlay. FullRAMdelta and deterministicinput reproducecases; all13contractregs plusremainingregs/stack recorded. RawSR is observation only.',fixed_rom_immutable=True,physical_bank_payload_immutable=True),indent=2)+'\n');return hashlib.sha256(report.read_bytes()).hexdigest()
 for index,case in enumerate(cases,start_index):
  cpu.context_restore(baseline);ram=fixture(index,case);cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,program[0x200000:0x2ffff0]);cpu.mem_write(STACK-128,b'\xa5'*128+RETURN.to_bytes(4,'big'));state.update(bank=0x200000,error=None,count=0);ports.clear();visits.clear()
  values=[0 if not case['profile'] else (0xabcd0000+i*0x111100)&0xffffffff for i in range(16)]
  for i,key in enumerate(('source_x','source_y','width','height','dest_x','dest_y')):values[i]=(values[i]&0xffff0000)|(case[key]&65535)
  values[8]=NODE;values[9]=case.get('prewrap_descriptor',case['descriptor']);values[13]=0x108000;values[15]=STACK
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

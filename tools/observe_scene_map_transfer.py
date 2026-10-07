"""Continuous native183c6 observation; no C++ comparison or ROM modification."""
import argparse,base64,collections,hashlib,itertools,json,struct,zlib
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE,NODE,STACK,RETURN,ENTRY=0x100000,0x109156,0x1feffc,0xff000,0x183c6
NAMES=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(8))
REGS=tuple(getattr(m,'UC_M68K_REG_'+name.upper()) for name in NAMES)

def fixture(index,slot,profile):
 ram=bytearray(hashlib.shake_256(b'scene-map-transfer-native'+struct.pack('>I',index)).digest(65536));at=NODE-BASE;struct.pack_into('>H',ram,at+0x26,slot)
 ram[at+0x3a:at+0x7a]=bytes((0,1,7,0xf8,0xff)[(i+profile)%5] for i in range(64));ram[at+0x7a]=(0x10,0xff)[profile]
 return ram

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');options=parser.parse_args()
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 inventory=json.loads((root/'artifacts/scene_paths/inventory.json').read_text());descriptors={r['descriptor_cpu_address']:r for p in inventory['paths'] for r in p['rows'] if r['opcode_word']==4};assert len(descriptors)==72
 secondary_root=int.from_bytes(program[0x200010:0x200014],'big');classes={};secondary=[]
 for address,row in sorted(descriptors.items()):
  descriptor=program[address:address+12];assert descriptor.hex()==row['descriptor_raw_hex'];selector=int.from_bytes(descriptor[2:4],'big');shift=(selector<<2)&65535;offset=shift if shift<32768 else shift-65536;lookup=secondary_root+offset
  pointer=None if selector==0 else int.from_bytes(program[lookup:lookup+4],'big');kind='disabled-zero-selector' if selector==0 else 'sentinel-ffffffff' if pointer==0xffffffff else 'nonzero-pointer' if pointer else 'zero-pointer'
  classes[address]=kind;secondary.append(dict(descriptor_cpu_address=address,selector_word=selector,classification=kind,lookup_cpu_address=None if selector==0 else lookup,pointer_long=pointer,raw_lookup_hex=None if selector==0 else program[lookup:lookup+4].hex()))
 cases=[]
 for address,row in sorted(descriptors.items()):
  for slot,profile in itertools.product((0,0xffff),range(2)):cases.append(dict(descriptor=address,source_column=0,source_row=0,width=1,height=1,dest_column=0,dest_row=0,slot=slot,profile=profile,label='all-canonical-descriptors-small-transfer'))
 representative=[]
 for kind in ('disabled-zero-selector','nonzero-pointer'):
  representative.append(next(a for a in sorted(descriptors) if classes[a]==kind))
 for address in representative:
  row=descriptors[address];width,height=row['width_word'],row['height_word']
  positions=((-1,0),(0,-1),(0,0),(width-1,height-1),(width,height))
  for (column,line),(w,h),slot,profile in itertools.product(positions,((1,1),(2,2),(32,1),(1,32),(32,32)),(0,0xffff),range(2)):
   cases.append(dict(descriptor=address,source_column=column,source_row=line,width=w,height=h,dest_column=(0,31,32,0xffff)[(w+profile)%4],dest_row=(0,31,32,0xffff)[(h+profile)%4],slot=slot,profile=profile,label='bounds-minus1-zero-last-outside-small-extents'))
 for slot,profile in itertools.product((0,0xffff),range(2)):
  cases.append(dict(descriptor=0x10000a,descriptor_source=representative[1],source_column=0,source_row=0,width=1,height=1,dest_column=0,dest_row=0,slot=slot,profile=profile,label='RAM-descriptor-height-alias-bankshadow'))
 if options.smoke:cases=cases[:4]
 folder=root/'artifacts/scene_map_transfer';folder.mkdir(parents=True,exist_ok=True);report=folder/'observation.json';report.unlink(missing_ok=True)
 cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);ports=[];visits=[];rows=[];state={'bank':0x300000,'error':None,'count':0}
 def code(cpu,address,size,user):
  state['count']+=1
  if address==RETURN:cpu.emu_stop();return
  if address in (0x18424,0x184d2,0x18530,0x1854a,0x18568,0x185a6,0x185d2,0x185ee,0x185f2,0x185f4,0x185f8):visits.append(address)
  word=int.from_bytes(cpu.mem_read(address,2),'big')
  if word==0x4afc or 0x4e40<=word<=0x4e4f:state['error']=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
 def write(cpu,access,address,size,value,user):
  if BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4:return
  if address not in (0x2ffff2,0x2ffff0,0x3c0000,0x300001):state['error']=dict(kind='unexpected-write',address=address,size=size,value=value);cpu.emu_stop();return
  ports.append((size,address,value&((1<<(size*8))-1)))
  if address==0x2ffff2:
   if size!=2 or value not in (0x1000,0x2000):state['error']=dict(kind='unsupported-bank-write',value=value);cpu.emu_stop();return
   state['bank']=0x200000 if value==0x1000 else 0x300000;cpu.mem_write(0x200000,program[state['bank']:state['bank']+0xffff0])
 def invalid(cpu,access,address,size,value,user):state['error']=dict(kind='invalid-memory',access=access,address=address,size=size,value=value);return False
 def interrupt(cpu,number,user):state['error']=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
 baseline=cpu.context_save()
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_INVALID,invalid);cpu.hook_add(UC_HOOK_INTR,interrupt)
 def save():
  report.write_text(json.dumps(dict(source=source,smoke=options.smoke,entry_cpu_address=ENTRY,cases=len(rows),completed_cases=sum(r['returned'] for r in rows),ports=sum(r['port_count'] for r in rows),secondary_classification=secondary,canonical_secondary_class_counts=dict(collections.Counter(classes.values())),results=rows,failure=state['error'],cpp_equivalence_claimed=False,fixed_rom_immutable=True,physical_bank_payload_immutable=True,scope='Standalone baseline CPUcontext restored only beforeeachcall; actual183c6 throughRTS uninterrupted context. Canonicalfixed op04 descriptor,A0node109156,bank3 initialwindow;PVC2000/1000 maps original3MiB/2MiB payload at200000..2fffef,tailoverlayexcluded. Host coordinates/extents/destination/node slot/scrollbytes/highregs are explicitfixtures,not naturalmapstreaming. Port9bytes(size,address,value) compressedbase64 preserveswholeorder. RAMdelta ranges plusdeterministicfixture reproducefullinput/output. Canonicalsecondary references have zero selector ornonzero pointer;noactualffffffff source found,so sentinelpathnotexecuted. RawSR/CCR andlastreturnPC areobservations,not generalflagsemantics/timingclaim.'),indent=2)+'\n');return hashlib.sha256(report.read_bytes()).hexdigest()
 for index,case in enumerate(cases):
  cpu.context_restore(baseline)
  ram=fixture(index,case['slot'],case['profile'])
  if 'descriptor_source' in case:ram[10:22]=program[case['descriptor_source']:case['descriptor_source']+12]
  initial_descriptor=bytes(ram[10:22]) if 'descriptor_source' in case else program[case['descriptor']:case['descriptor']+12]
  cpu.mem_write(BASE,bytes(ram));state.update(bank=0x300000,error=None,count=0);cpu.mem_write(0x200000,program[0x300000:0x3ffff0]);cpu.mem_write(STACK-64,b'\xa5'*64+RETURN.to_bytes(4,'big'));before_stack=bytes(cpu.mem_read(STACK-64,68))
  values=[(0 if case['profile']==0 else (0xabcd0000+i*0x111100)&0xffffffff) for i in range(16)]
  for i,key in enumerate(('source_column','source_row','width','height','dest_column','dest_row')):values[i]=(values[i]&0xffff0000)|(case[key]&65535)
  values[8]=NODE;values[9]=case['descriptor'];values[13]=0x108000;values[15]=STACK
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  cpu.reg_write(m.UC_M68K_REG_SR,0x2000);ports.clear();visits.clear()
  try:cpu.emu_start(ENTRY,0xffffff,count=1000000)
  except unicorn.UcError as error:
   if state['error'] is None:state['error']=dict(kind='emulator-error',message=str(error))
  returned=cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
  if not returned and state['error'] is None:state['error']=dict(kind='instruction-cap',cap=1000000,pc=cpu.reg_read(m.UC_M68K_REG_PC))
  output=bytes(cpu.mem_read(BASE,65536));delta=[];cursor=0
  while cursor<len(ram):
   if ram[cursor]==output[cursor]:cursor+=1;continue
   start=cursor
   while cursor<len(ram) and ram[cursor]!=output[cursor]:cursor+=1
   delta.append(dict(ram_offset=start,before_hex=ram[start:cursor].hex(),after_hex=output[start:cursor].hex()))
  packed=b''.join(struct.pack('>BII',*event) for event in ports);sr=cpu.reg_read(m.UC_M68K_REG_SR);final=dict(zip(NAMES,(cpu.reg_read(reg)&0xffffffff for reg in REGS)))
  rows.append(dict(case_index=index,fixture=case,fixture_algorithm='shake256(scene-map-transfer-native+BE32index),node slot andscroll bytes patched byfixture()',descriptor_raw_hex=initial_descriptor.hex(),secondary_class=classes[case.get('descriptor_source',case['descriptor'])],incoming=dict(zip(NAMES,values)),returned=returned,final_pc=cpu.reg_read(m.UC_M68K_REG_PC),final_registers=final,raw_sr=sr,raw_ccr=sr&31,raw_carry=bool(sr&1),copied_by_executed_return_path=0x185f2 in visits,carry_evidence='executed185f2(success) or185f8(rejected); rawSR recorded independently',return_path_pc=next((pc for pc in reversed(visits) if pc in (0x185f2,0x185f8)),None),stack_sha256_before=hashlib.sha256(before_stack).hexdigest(),stack_sha256_after=hashlib.sha256(bytes(cpu.mem_read(STACK-64,68))).hexdigest(),input_ram_sha256=hashlib.sha256(ram).hexdigest(),output_ram_sha256=hashlib.sha256(output).hexdigest(),ram_delta=delta,changed_ram_bytes=sum(len(d['after_hex'])//2 for d in delta),port_count=len(ports),ports_sha256=hashlib.sha256(packed).hexdigest(),ports_zlib_base64=base64.b64encode(zlib.compress(packed)).decode(),ports_prefix=ports[:8],boundary_pc_visits=visits.copy(),final_bank_source_rom=state['bank'],instructions=state['count']))
  assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and bytes(cpu.mem_read(0x200000,0xffff0))==program[state['bank']:state['bank']+0xffff0]
  if state['error']:print(json.dumps(dict(cases=len(rows),failure=state['error'],sha256=save())));raise SystemExit(1)
  assert final['a7']==STACK+4
 print(json.dumps(dict(cases=len(rows),ports=sum(r['port_count'] for r in rows),sha256=save())))
if __name__=='__main__':main()

"""Original whole1afda and1a7a8 observations, without callee substitution."""
import argparse,base64,collections,hashlib,itertools,json,struct,zlib
from pathlib import Path
import unicorn
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_INVALID,UC_HOOK_INTR,m68k_const as m
from disassemble_program import load_verified_program
from verify_stage_catalog import SOURCE_SHA256
from verify_object_reset import make_cpu
from observe_scene_map_transfer import NAMES,REGS,BASE,NODE,STACK,RETURN
NODES=(0x9156,0xb1d6,0xd256,0xd2d6)
METADATA=(0xd356,0xd364,0xd372,0xd380)
CAMERA=0xd38e

def put_node(ram,node,parent,variant):
 data=((0,0,0,0),(0xffff00ff,0x7fff00ff,0x10001,0x8000ffff),(0x7fffffff,0x80000001,0xffff0001,0x7fff0001),(0x8000ffff,0xffffffff,0x800000ff,0xffff00ff))[variant%4]
 struct.pack_into('>5I',ram,node,*data,parent);struct.pack_into('>4I',ram,node+0x14,0x12345678,0x87654321,0x7fffffff,0x80000000);ram[node+0x24]=0 if variant%2 else 255;ram[node+0x25]=0xa0
 factor=(0,1,0x7fff,0x8000,0xffff,0x100)[variant%6];struct.pack_into('>HH',ram,node+0x28,factor,factor);ram[node+0x2c]=ram[node+0x2d]=(0,1,255)[variant%3]
 struct.pack_into('>H',ram,node+0x26,0xffff);struct.pack_into('>I',ram,node+0x2e,0);struct.pack_into('>I',ram,node+0x36,0);struct.pack_into('>hh',ram,node+0x32,-6,39);ram[node+0x7a]=0

def fixture(index,case):
 ram=bytearray(hashlib.shake_256(b'scene-update-native'+struct.pack('>I',index)).digest(65536));variant=case.get('variant',0)
 # The two debug caches fit; no synthetic cache spans are written over small nodes3/4.
 for index_node,node in enumerate(NODES[:2]):
  for col in range(64):
   for row in range(64):
    key=col*32+row+index_node*137;tile=((key&255)-0x58)&255;upper=((key//256)&3)<<14
    if case.get('tile_index') is not None:tile=(case['tile_index']-0x58)&255;upper=(case['tile_index']&3)<<14
    struct.pack_into('>H',ram,node+0x80+col*128+row*2,upper|tile)
 if case['entry']==0x1afda:
  for i,node in enumerate(NODES[:2]):
   x,y=0x00180000,0xfff80000;oldx,oldy=x,y
   history=case.get('history','equal')
   if history=='x-borrow' and i==0:oldx=(x-1)&0xffffffff
   elif history=='x-positive-only' and i==0:oldx=(x+1)&0xffffffff
   elif history=='y-difference' and i==0:oldy=(y+1)&0xffffffff
   elif history=='second-only' and i==1:oldy=(y+1)&0xffffffff
   elif history=='sticky-Z-x-nonzero-y-equal' and i==0:oldx=(x+0x80000)&0xffffffff
   struct.pack_into('>4I',ram,node+0x14,x,y,oldx,oldy)
 else:
  put_node(ram,0x2000,0,variant)
  for i,node in enumerate((CAMERA,)+NODES):
   parent=0 if variant%4==0 else BASE+CAMERA if variant%4==1 and i else BASE+node if variant%4==2 else BASE+0x2000
   put_node(ram,node,parent,variant+i)
   struct.pack_into('>H',ram,node+0x26,case.get('slot',0xffff))
  for meta,cursor in zip(METADATA,case.get('path_cursors',(0,0,0,0))):struct.pack_into('>IhhhhH',ram,meta,cursor,-6,39,0,0,0)
  struct.pack_into('>II',ram,0xd3bc,(0,0xffff0001,0x80000000,0x7fffffff)[variant%4],(0,0x7fffffff,0xffffffff,0x80000001)[variant%4]);struct.pack_into('>H',ram,0xd404,(0,1,0x7fff,0x8000,0xffff)[variant%5]);ram[0xd40c]=case.get('mask',0);ram[0xd494]=(0,1,255)[variant%3]
 if case.get('visible_geometry'):
  for node in (CAMERA,)+NODES:
   struct.pack_into('>5I',ram,node,0,0,0,0,0);struct.pack_into('>4I',ram,node+0x14,0,0,0,0);ram[node+0x24]=ram[node+0x25]=0;struct.pack_into('>H',ram,node+0x26,0);ram[node+0x7a]=0
  selected=NODES[case['reference']['selector_word']//4];x=((-96-16*case['visible_meta_x'])&65535)<<16;y=((639-16*case['visible_meta_y'])&65535)<<16
  struct.pack_into('>II',ram,selected,x,y);struct.pack_into('>4I',ram,selected+0x14,x,y,x,y)
  struct.pack_into('>II',ram,0xd3bc,0,0);struct.pack_into('>H',ram,0xd404,0);ram[0xd40c]=0xff;ram[0xd494]=0
 ram[0xf000]=(ram[0xf000]&~24)|case['debug_bits'];ram[0xd44e]=case['oldflag'];return ram

def build_cases(program,root):
 cases=[]
 def add(entry,**kw):
  c=dict(entry=entry,profile=0,debug_bits=0,oldflag=0,label='controlled-scene-update');c.update(kw);cases.append(c)
 for bits,old,history,profile in itertools.product((0,8,16,24),(0,1,255),('equal','x-borrow','x-positive-only','y-difference','second-only','sticky-Z-x-nonzero-y-equal'),range(3)):
  add(0x1afda,debug_bits=bits,oldflag=old,history=history,profile=profile,label='debug-whole-flags-borrow-stickyZ-duplicate-firstnode')
 sentinel=next(i for i in range(256) if int.from_bytes(program[0x1af12+2*i:0x1af14+2*i],'big')==0x320)
 solid=next(i for i in range(256) if int.from_bytes(program[0x1af12+2*i:0x1af14+2*i],'big')!=0x320)
 for tile,profile,bits in itertools.product((sentinel,solid),range(3),(8,16,24)):add(0x1afda,debug_bits=bits,tile_index=tile,profile=profile,label='debug-uniform-table320-fallback-vs-non320')
 for mask,profile in itertools.product(range(256),range(2)):add(0x1a7a8,mask=mask,variant=mask%4,profile=profile,debug_bits=(0,8,16,24)[mask%4],oldflag=(0,1)[profile],label='full-coordinate-all256-mask-nullpaths')
 for mask,variant,bits,profile in itertools.product((0,0x55,0xaa,0xff),range(4),(0,8,16,24),range(2)):add(0x1a7a8,mask=mask,variant=variant,debug_bits=bits,oldflag=(0,255)[profile],profile=profile,label='full-nullpaths-debug-off-on-reset-parent-factor-fraction')
 inventory=json.loads((root/'artifacts/scene_paths/inventory.json').read_text());refs=inventory['references'];assert len(refs)==72
 for ref in refs:
  at=ref['command_cpu_address'];assert program[at:at+2]==b'\x00\x24' and program[at+2:at+8].hex()==ref['operand_raw_hex']
  assert int.from_bytes(program[at+2:at+4],'big')==ref['selector_word'] and int.from_bytes(program[at+4:at+8],'big')==ref['pointer_long']
 for ref,variant,profile in itertools.product(refs,(0,1),range(2)):
  cursors=[0]*4;cursors[ref['selector_word']//4]=ref['pointer_long'];add(0x1a7a8,path_cursors=cursors,variant=variant,profile=profile,mask=(0,0xff)[variant],debug_bits=(0,24)[profile],oldflag=0,reference=ref,label='full-canonical-path-on-original-referenced-node')
 for ref in refs:
  cursors=[0]*4;cursors[ref['selector_word']//4]=ref['pointer_long'];add(0x1a7a8,path_cursors=cursors,variant=0,profile=1,mask=0,debug_bits=0,oldflag=0,slot=0,reference=ref,label='full-canonical-path-original-node-slot-enabled-geometry-clipped')
 paths={p['root_cpu_address']:p for p in inventory['paths']}
 for ref in refs:
  initial=next(row for row in paths[ref['pointer_long']]['rows'] if row['opcode_word']==0);at=initial['cpu_address'];assert program[at:at+initial['size']].hex()==initial['raw_hex']
  x=int.from_bytes(program[at+2:at+4],'big')&0xfff;y=int.from_bytes(program[at+4:at+6],'big')&0xfff;x=x-4096 if x&0x800 else x;y=y-4096 if y&0x800 else y
  cursors=[0]*4;cursors[ref['selector_word']//4]=ref['pointer_long'];add(0x1a7a8,path_cursors=cursors,variant=0,profile=1,mask=0xff,debug_bits=0,oldflag=0,slot=0,reference=ref,visible_geometry=True,visible_meta_x=x,visible_meta_y=y,label='full-canonical-path-visible-source0-actual-map-transfer')
 grouped={}
 for ref in refs:grouped.setdefault(ref['script_cpu_address'],[]).append(ref)
 for script,group in sorted(grouped.items()):
  cursors=[0]*4
  for ref in group:cursors[ref['selector_word']//4]=ref['pointer_long']
  for profile in range(2):add(0x1a7a8,path_cursors=cursors,variant=0,mask=0,profile=profile,debug_bits=(0,24)[profile],oldflag=0,script_cpu_address=script,label='full-simultaneous-paths-grouped-original-script-references')
 for bits,profile in itertools.product((8,16,24),range(3)):
  add(0x1afda,debug_bits=bits,profile=profile,label='carry-debug-on')
  add(0x1afda,debug_bits=bits,profile=profile,carry_from=len(cases)-1,host_mutation='stable-history',label='carry-debug-stable')
  add(0x1afda,debug_bits=0,profile=profile,carry_from=len(cases)-1,host_mutation='debug-off',label='carry-debug-off-reset')
 for profile in range(2):
  add(0x1a7a8,profile=profile,mask=0,variant=0,label='carry-full-nullpaths')
  add(0x1afda,profile=profile,debug_bits=24,carry_from=len(cases)-1,host_mutation='debug-on',label='carry-debug-after-full-update')
 return cases

def mutate_host(ram,case):
 if case['host_mutation']=='stable-history':
  for node in NODES[:2]:ram[node+0x1c:node+0x24]=ram[node+0x14:node+0x1c]
 ram[0xf000]=(ram[0xf000]&~24)|case['debug_bits']
 return ram

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');o=parser.parse_args();root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256;cases=build_cases(program,root)
 if o.smoke:cases=[next(c for c in cases if c['entry']==entry) for entry in (0x1afda,0x1a7a8)]
 folder=root/'artifacts/scene_update';folder.mkdir(parents=True,exist_ok=True);report=folder/'observation.json';report.unlink(missing_ok=True)
 cpu=make_cpu(program);cpu.mem_map(0x200000,0x300000);baseline=cpu.context_save();ports=[];visits=[];rows=[];start_index=0;state=dict(bank=0x200000,error=None,count=0)
 def code(cpu,address,size,user):
  state['count']+=1
  if address==RETURN:cpu.emu_stop();return
  if address in (0x1a7a8,0x1a8ca,0x1afda,0xcaf0,0x35a2,0x19e64,0x1861a,0x18656,0x18702,0x183c6,0x185f2,0x185f8,0x1b0e0,0x1b110,0x1b122):visits.append(address)
  word=int.from_bytes(cpu.mem_read(address,2),'big')
  if word==0x4afc or 0x4e40<=word<=0x4e4f:state['error']=dict(kind='trap-or-illegal',pc=address,word=word);cpu.emu_stop()
 def write(cpu,access,address,size,value,user):
  if BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4:return
  if address not in (0x2ffff2,0x2ffff0,0x3c0000,0x3c0004,0x300001):state['error']=dict(kind='unexpected-write',address=address,size=size,value=value);cpu.emu_stop();return
  ports.append((size,address,value&((1<<(8*size))-1)))
  if address==0x2ffff2:
   if size!=2 or value not in (0x1000,0x2000):state['error']=dict(kind='unsupported-bank-write',value=value);cpu.emu_stop();return
   state['bank']=0x200000 if value==0x1000 else 0x300000;cpu.mem_write(0x200000,program[state['bank']:state['bank']+0xffff0])
 def invalid(cpu,access,address,size,value,user):state['error']=dict(kind='invalid-memory',access=access,address=address,size=size);return False
 def intr(cpu,number,user):state['error']=dict(kind='cpu-exception',number=number,pc=cpu.reg_read(m.UC_M68K_REG_PC));cpu.emu_stop()
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write);cpu.hook_add(UC_HOOK_MEM_INVALID,invalid);cpu.hook_add(UC_HOOK_INTR,intr)
 def save():
  report.write_text(json.dumps(dict(source=source,smoke=o.smoke,cases=len(rows),completed_cases=sum(r['returned'] for r in rows),ports=sum(r['port_count'] for r in rows),results=rows,failure=state['error'],scope='Native-only continuous standalone calls; baselinecontext restored beforecall only. Wholedebug andcoordinate/pathupdate onexplicitvalid node/cache/parent/globalfixtures; canonicalpathmetadataassignedaccordingtooriginalsceneopcode24references; no natural scheduler/mapstreaming or C++ equivalence claim. CPUwindow initiallybank2, PVC1000/2000 selects original2MiB/3MiB physical payload excludingtailMMIO overlay. FullRAMdelta and deterministicinput reproducecases; all13contractregs plusremainingregs/stack recorded. RawSR is observation only.',fixed_rom_immutable=True,physical_bank_payload_immutable=True),indent=2)+'\n');return hashlib.sha256(report.read_bytes()).hexdigest()
 for index,case in enumerate(cases,start_index):
  cpu.context_restore(baseline)
  if 'carry_from' in case:
   assert case['carry_from']==index-1;ram=mutate_host(bytearray(last_output),case)
  else:ram=fixture(index,case)
  cpu.mem_write(BASE,bytes(ram));cpu.mem_write(0x200000,program[0x200000:0x2ffff0]);cpu.mem_write(STACK-128,b'\xa5'*128+RETURN.to_bytes(4,'big'));state.update(bank=0x200000,error=None,count=0);ports.clear();visits.clear()
  values=[0 if not case['profile'] else 0xffffffff if case['profile']==2 else (0xabcd0000+i*0x111100)&0xffffffff for i in range(16)]
  if 'carry_from' in case:values=[last_final[k] for k in NAMES]
  values[13]=0x108000;values[15]=STACK
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
  if case.get('visible_geometry') and (0x185f2 not in visits or not any(p[1]==0x3c0000 for p in ports)):state['error']=dict(kind='visible-fixture-no-actual-successful-transfer',case_index=index)
  if state['error']:print(json.dumps(dict(cases=len(rows),failure=state['error'],sha256=save())));raise SystemExit(1)
  assert final['a7']==STACK+4
  last_output=output;last_final=final
 print(json.dumps(dict(cases=len(rows),ports=sum(r['port_count'] for r in rows),sha256=save())))
if __name__=='__main__':main()

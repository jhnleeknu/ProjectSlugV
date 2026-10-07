"""Native19e7e dispatch boundaries for syntax-inventoried canonical scene paths.

Handler bodies are deliberately not executed; this is not handler-effect or C++ equivalence.
"""
import hashlib,json,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from pack_scene_scripts import command_span
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256
BASE,STACK,RETURN,ENTRY,TABLE=0x100000,0x1feffc,0xff000,0x19e7e,0x19e8a
PAYLOAD={0:4,4:12,8:12,12:12,16:12,20:12,24:6,28:4}
HANDLERS={0:0x19eaa,4:0x19ed0,8:0x19f9e,12:0x19fc4,16:0x19ff4,20:0x1a01c,24:0x1a068,28:0x19ec2}
NAMES=tuple('d'+str(i) for i in range(8))+tuple('a'+str(i) for i in range(8))
REGS=tuple(getattr(m,'UC_M68K_REG_'+name.upper()) for name in NAMES)

def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 folder=root/'artifacts/scene_paths';inventory_path=folder/'inventory.json';inventory=json.loads(inventory_path.read_text());assert inventory['source']==source and inventory['error_count']==0
 manifest_path=root/'extracted/runtime/scene_scripts/manifest.json';manifest=json.loads(manifest_path.read_text());assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==inventory['manifest_sha256']
 # Independently rederive roots from raw opcode24 operands, then both successors from source bytes.
 references=[]
 for item in manifest['scripts']:
  end,commands,terminal=command_span(program,item['source_cpu_address'])
  assert hashlib.sha256(program[item['source_cpu_address']:end]).hexdigest()==item['payload_sha256']
  for command in commands:
   if command['opcode']==0x24:
    selector,pointer=struct.unpack('>HI',program[command['source_cpu_address']+2:command['source_cpu_address']+8]);references.append((command['source_cpu_address'],selector,pointer))
 assert sorted(references)==sorted((r['command_cpu_address'],r['selector_word'],r['pointer_long']) for r in inventory['references'])
 roots={pointer for address,selector,pointer in references if pointer};assert roots=={path['root_cpu_address'] for path in inventory['paths']}
 unique={};closure=[]
 for path in inventory['paths']:
  pending=[path['root_cpu_address']];seen={};edges=set()
  while pending:
   address=pending.pop()
   if address in seen:continue
   assert address%2==0 and 0<=address<0xfffff
   opcode=int.from_bytes(program[address:address+2],'big');terminal=bool(opcode&0x8000);assert terminal or opcode in PAYLOAD
   size=2 if terminal else 2+PAYLOAD[opcode];assert address+size<=0x100000
   seen[address]=(opcode,size,program[address:address+size].hex())
   if not terminal:
    targets=[('sequential',address+size)]
    if opcode in (8,12,16,20):targets.append(('branch',int.from_bytes(program[address+10:address+14],'big')))
    for kind,target in targets:edges.add((address,target,kind));pending.append(target)
   assert len(seen)<=32768
  expected={r['cpu_address']:(r['opcode_word'],r['size'],r['raw_hex']) for r in path['rows']};assert seen==expected
  assert edges=={(edge['from_cpu_address'],edge['to_cpu_address'],edge['kind']) for edge in path['edges']}
  closure.append(dict(root_cpu_address=path['root_cpu_address'],rows=len(seen),edges=len(edges),raw_source_closure_equal=True))
  for address,row in seen.items():
   assert address not in unique or unique[address]==row
   unique[address]=row
 assert len(unique)==inventory['unique_row_count']
 branch_evidence=[]
 for opcode,target in HANDLERS.items():
  address=TABLE+opcode;word,displacement=struct.unpack('>Hh',program[address:address+4]);assert word==0x6000 and address+2+displacement==target
  branch_evidence.append(dict(opcode=opcode,branch_cpu_address=address,target_cpu_address=target,raw_hex=program[address:address+4].hex()))
 cpu=make_cpu(program);state={'stop':RETURN};writes=[];visited=[];results=[]
 def code(cpu,address,size,user):
  visited.append(address)
  if address==state['stop']:cpu.emu_stop()
 def write(cpu,access,address,size,value,user):writes.append((size,address,value));raise AssertionError('Dispatch unexpectedly wrote memory '+repr(writes[-1]))
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 for address,(opcode,size,raw) in sorted(unique.items()):
  for initial_d7 in (0,0xabcdffff,0xffffffff):
   ram=hashlib.shake_256(b'scene-path-dispatch'+address.to_bytes(4,'big')+initial_d7.to_bytes(4,'big')).digest(65536);cpu.mem_write(BASE,ram)
   incoming=[(0x12340000+index*0x111111)&0xffffffff for index in range(16)];incoming[7]=initial_d7;incoming[10]=address;incoming[13]=0x108000;incoming[15]=STACK
   for reg,value in zip(REGS,incoming):cpu.reg_write(reg,value)
   cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK-64,b'\xa5'*64+RETURN.to_bytes(4,'big'));before_stack=bytes(cpu.mem_read(STACK-64,68));writes.clear();visited.clear()
   terminal=bool(opcode&0x8000);state['stop']=RETURN if terminal else HANDLERS[opcode];cpu.emu_start(ENTRY,0xffffff,count=32)
   expected=incoming.copy();expected[7]=(initial_d7&0xffff0000)|opcode;expected[10]=address+2;expected[15]=STACK+(4 if terminal else 0)
   actual=[cpu.reg_read(reg)&0xffffffff for reg in REGS];assert actual==expected and cpu.reg_read(m.UC_M68K_REG_PC)==state['stop'] and not writes
   assert bytes(cpu.mem_read(BASE,65536))==ram and bytes(cpu.mem_read(STACK-64,68))==before_stack and bytes(cpu.mem_read(0,0x100000))==program[:0x100000]
   assert (0x19e84 in visited) if terminal else (TABLE+opcode in visited)
   results.append(dict(command_cpu_address=address,command_rom_offset=address,opcode_word=opcode,terminal=terminal,raw_hex=raw,incoming_d7=initial_d7,result_d7=actual[7],result_a2=actual[10],stop_pc=state['stop'],result_a7=actual[15],all_registers_equal_except_d7_a2_and_terminal_sp=True,ram_sha256=hashlib.sha256(ram).hexdigest(),ram_unchanged=True,stack_unchanged=True,memory_writes=0,executed_pc_sequence=visited.copy(),handler_body_executed=False))
 report=folder/'dispatch_verification.json';report.write_text(json.dumps(dict(source=source,inventory_sha256=hashlib.sha256(inventory_path.read_bytes()).hexdigest(),entry_cpu_address=ENTRY,cases=len(results),unique_command_addresses=len(unique),positive_command_addresses=sum(not opcode&0x8000 for opcode,size,raw in unique.values()),terminal_addresses=sum(bool(opcode&0x8000) for opcode,size,raw in unique.values()),observed_nonnegative_opcodes=sorted({opcode for opcode,size,raw in unique.values() if not opcode&0x8000}),dispatch_table_source_evidence=branch_evidence,reference_root_closure=closure,results=results,original_rom_immutable=True,memory_writes=0,scope='Actual19e7e MOVE.W opcode and indexed JMP/BRA stop BEFOREcanonicalhandlerentry; negative commands execute19e84 RTS tosentinel. D7highword/A2cursor/fullRAM/stack/allregister preservation compared to instruction-level contract. Source closure independently rederived fromraw opcode24 references andsyntax successors, not branch feasibility or natural execution. Canonical data only contains00/04/18 andffff; otherfive dispatch targets checked asoriginalBRA bytes only, not executed. NoROMpatch, handler effects orC++equivalence claim.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(results),unique_addresses=len(unique),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

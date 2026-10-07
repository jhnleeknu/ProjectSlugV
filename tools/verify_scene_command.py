"""Actual supported scene commands dispatched from immutable canonical scripts."""
import hashlib,itertools,json,struct,subprocess,zlib,shutil
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from verify_object_reset import make_cpu
from verify_stage_catalog import SOURCE_SHA256,checked_resource
from pack_scene_scripts import command_span
BASE,STACK,RETURN,ENTRY=0x100000,0x1feffc,0xff000,0x1a0b6
SUPPORTED={0x04,0x00,0x10,0x24,0x0c,0x14,0x18,0x1c,0x20,0x28,0x2c,0x30,0x34,0x38,0x3c,0x40,0x44,0x48,0x4c}
REGS=(m.UC_M68K_REG_D0,m.UC_M68K_REG_D1,m.UC_M68K_REG_D2,m.UC_M68K_REG_D3,m.UC_M68K_REG_D4,m.UC_M68K_REG_D5,m.UC_M68K_REG_D6,m.UC_M68K_REG_D7,m.UC_M68K_REG_A0,m.UC_M68K_REG_A1,m.UC_M68K_REG_A2,m.UC_M68K_REG_A4);KEYS=('d0','d1','d2','d3','d4','d5','d6','d7','a0','a1','a2','a4')
def dependency_negatives(root,prepared,exe,node,folder):
 scripts=root/'extracted/runtime/scene_scripts';manifest=json.loads((scripts/'manifest.json').read_text())
 inp,out,portfile=[folder/name for name in ('dependency.input.bin','dependency.output.bin','dependency.ports.bin')]
 empty=folder/'empty-dependencies';empty.mkdir(exist_ok=True)
 copied=folder/'copied-dependencies';copied.mkdir(exist_ok=True)
 for entry in manifest['dependencies']:shutil.copyfile(scripts/entry['file'],copied/entry['file'])
 results=[];sentinel=b'prior-dependency-output\0\xff';ram=bytes(65536)
 def reject(op,script,command,directory,label,target=None):
  inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel)
  values=[0]*12;values[9]=command['source_cpu_address'];output=target or out;before=output.read_bytes()
  args=[str(exe)]+list(map(str,values))+list(map(str,(inp,output,portfile,script,node)))
  if directory is not None:args.append(str(directory))
  actual=subprocess.run(args,capture_output=True,text=True)
  assert actual.returncode and output.read_bytes()==before and portfile.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stdout,actual.stderr)
  results.append(dict(failure=label,opcode=op,outputs_preserved=True,native_executed=False,temporary_dependencies_only=True))
 for op in (0,4,0x10,0x24):
  script,command=next((p,c) for p,cs,t in prepared for c in cs if c['opcode']==op)
  if op==4:address=0x20000c
  elif op==0:address=int.from_bytes(bytes.fromhex(command['operand_hex'])[4:8],'big')
  elif op==0x10:address=int.from_bytes(bytes.fromhex(command['operand_hex']),'big')
  else:address=0x1a0a6
  entry=next(e for e in manifest['dependencies'] if e['source_cpu_address']==address);target=copied/entry['file'];good=(scripts/entry['file']).read_bytes()
  reject(op,script,command,None,'required-dependency-directory-omitted')
  reject(op,script,command,empty,'required-dependency-file-absent')
  target.write_bytes(b'bad');reject(op,script,command,copied,'required-dependency-file-malformed')
  raw=bytearray(good);struct.pack_into('<I',raw,12,address+2);struct.pack_into('<I',raw,16,address+2);target.write_bytes(raw)
  reject(op,script,command,copied,'crc-valid-dependency-wrong-cpu-window')
  target.write_bytes(good)
  if op in (0,4):reject(op,script,command,copied,'dependency-resource-output-same-path-alias',target)
 # Opcode04 resolves a root, selector lookup and binding table in order.
 script,command=next((p,c) for p,cs,t in prepared for c in cs if c['opcode']==4)
 selector=int.from_bytes(bytes.fromhex(command['operand_hex'])[:2],'big');shifted=(selector<<2)&65535;offset=shifted if shifted<32768 else shifted-65536
 program,_=load_verified_program(root);lookup=int.from_bytes(program[0x20000c:0x200010],'big')+offset;binding=int.from_bytes(program[lookup:lookup+4],'big')
 for address in (lookup,binding):
  entry=next(e for e in manifest['dependencies'] if e['source_cpu_address']==address);target=copied/entry['file'];good=(scripts/entry['file']).read_bytes()
  target.unlink();reject(4,script,command,copied,'opcode04-required-chain-file-absent')
  target.write_bytes(b'bad');reject(4,script,command,copied,'opcode04-required-chain-file-malformed')
  raw=bytearray(good);struct.pack_into('<I',raw,12,address+2);struct.pack_into('<I',raw,16,address+2);target.write_bytes(raw);reject(4,script,command,copied,'opcode04-required-chain-wrong-identity')
  target.write_bytes(good)
 return results
def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 scripts=root/'extracted/runtime/scene_scripts';manifest=json.loads((scripts/'manifest.json').read_text());assert len(manifest['scripts'])==41
 node=scripts/'node_pointers.ms5d';node_sha=checked_resource(node,program,0x1a08e,0x1a09e)
 prepared=[]
 for resource in manifest['scripts']:
  start=resource['source_cpu_address'];end,commands,terminator=command_span(program,start);path=scripts/resource['file'];checked_resource(path,program,start,end);prepared.append((path,commands,terminator))
 dependencies=[]
 for entry in manifest['dependencies']:
  path=scripts/entry['file']
  if entry['file'].startswith('palette_'):
   raw=path.read_bytes();magic,version,kind,cpu_address,rom_offset,length,crc,reserved=struct.unpack('<4s7I',raw[:32]);assert (magic,version,kind,cpu_address,rom_offset,length,reserved)==(b'MS5D',1,2,entry['source_cpu_address'],entry['source_rom_offset'],entry['payload_size'],0);assert zlib.crc32(raw[32:])&0xffffffff==crc and raw[32:]==program[rom_offset:rom_offset+length];sha=hashlib.sha256(raw).hexdigest()
  else:sha=checked_resource(path,program,entry['source_cpu_address'],entry['source_cpu_address']+entry['payload_size'])
  assert sha==entry['sha256']
  evidence=dict(file=entry['file'],source_cpu_address=entry['source_cpu_address'],payload_size=entry['payload_size'],sha256=sha)
  if entry['file'].startswith('motion_'):
   evidence['first_type_word_at_offset2']=int.from_bytes(program[entry['source_cpu_address']+2:entry['source_cpu_address']+4],'big')
  dependencies.append(evidence)
 folder=root/'artifacts/scene_command';folder.mkdir(parents=True,exist_ok=True)
 inp,out,portfile,report=[folder/n for n in ('input.bin','cpp.bin','ports.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/step_scene_command';binary=hashlib.sha256(exe.read_bytes()).hexdigest()
 cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);cpu.mem_write(0x200000,program[0x200000:0x300000]);trace,paths,rows,negatives,sequences=[],[],[],[],[];current={}
 def code(cpu,address,size,user):
  if address==RETURN:cpu.emu_stop()
  elif address in (0x16fee,0x17012,0x1701a,0x3d7e,0x1a086,0x8da2,0x8e7a):paths.append(address)
 def write(cpu,access,address,size,value,user):
  if address in (0x3c0006,0x300001,0x3c0000,0x2ffff0,0x2ffff2):
   assert size==(4 if address==0x3c0000 else 2 if address==0x3c0006 else 2 if address in (0x2ffff0,0x2ffff2) else 1);trace.append((size,address,value&((1<<(8*size))-1)))
  else:assert BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4,(hex(address),size,value,current)
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 def fixture(seed):
  cpu.mem_write(BASE,hashlib.shake_256(b'scene-command-fixture'+bytes([seed])).digest(65536));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'));cpu.emu_start(0x3ef2,0xffffff,count=100000)
  assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
  return bytearray(cpu.mem_read(BASE,65536))
 def args(values,script,nodefile=node):return [str(exe)]+list(map(str,values))+list(map(str,(inp,out,portfile,script,nodefile,scripts)))
 def compare(ram,values,script,command,label):
  current.update(command=command,label=label,pc=values[9])
  cpu.mem_write(BASE,bytes(ram));cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
  trace.clear();paths.clear();cpu.emu_start(ENTRY,0xffffff,count=100000)
  assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4
  expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result['writes']=len(trace)
  assert result['a1']==command['next_cpu_address']
  inp.write_bytes(ram);actual=subprocess.run(args(values,script),capture_output=True,text=True);assert not actual.returncode,(label,command,actual.stderr)
  parsed=json.loads(actual.stdout);actual_ram=out.read_bytes();ports=b''.join(struct.pack('>BII',*event) for event in trace)
  if actual_ram!=expected or parsed!=result or portfile.read_bytes()!=ports:
   diff=[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,actual_ram)) if a!=b];raise ValueError(repr((label,command,diff[:20],result,parsed,trace)))
  rows.append(dict(profile=label,script_file=script.name,command_cpu_address=command['source_cpu_address'],opcode=command['opcode'],operand_hex=command['operand_hex'],incoming=dict(zip(KEYS,values)),result=parsed,native_calls=paths.copy(),ports=trace.copy(),ram_sha256=hashlib.sha256(expected).hexdigest()))
  return bytearray(actual_ram),tuple(parsed[key] for key in KEYS)
 highs=((0,0,0,0,0,0,0,0,0,0,0),(0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234))
 def incoming(high,pc):return high[:9]+(pc,high[9],high[10])
 for script,commands,terminator in prepared:
  for command in commands:
   if command['opcode'] not in SUPPORTED:continue
   for seed,high in itertools.product((0,1),highs):compare(fixture(seed),incoming(high,command['source_cpu_address']),script,command,'every-supported-canonical-command-random-ram-high-registers')
 for script,commands,terminator in prepared:
  for command in commands:
   if command['opcode']==0x40:
    for shadow in (0,8,0x100,0x8000,0xffff):
     ram=fixture(2);struct.pack_into('>H',ram,0x4d90,shadow)
     compare(ram,incoming(highs[1],command['source_cpu_address']),script,command,'native-video-shadow-boundaries-canonical-operand')
 node_addresses=struct.unpack('>4I',program[0x1a08e:0x1a09e])
 for script,commands,terminator in prepared:
  for command in commands:
   if command['opcode']==0x1c and bytes.fromhex(command['operand_hex'])[2:4]==bytes(2):
    selector=int.from_bytes(bytes.fromhex(command['operand_hex'])[:2],'big');obj=node_addresses[selector//4]-BASE
    for slot in (0,1,0x7fff,0x8000,0xffff):
     ram=fixture(2);struct.pack_into('>H',ram,obj+0x26,slot)
     compare(ram,incoming(highs[1],command['source_cpu_address']),script,command,'native-clear-node-slot-positive-negative-wrap')
 # Metadata+RAM/register outputs travel through adjacent supported command runs.
 for script,commands,terminator in prepared:
  ram=fixture(2);values=incoming(highs[1],commands[0]['source_cpu_address'] if commands else terminator);run_start=None;count=0
  for command in commands:
   if command['opcode'] not in SUPPORTED:
    if count>=2:sequences.append(dict(script_file=script.name,calls=count,first_result_index=run_start,actual_cli_ram_full_exposed_registers_and_a1_carried=True,unsupported_next_opcode=command['opcode'],entry_context_reset_explicit=True))
    count=0;run_start=None;values=values[:9]+(command['next_cpu_address'],values[10],values[11]);continue
   if count==0:run_start=len(rows);values=values[:9]+(command['source_cpu_address'],values[10],values[11])
   ram,values=compare(ram,values,script,command,'actual-cli-adjacent-supported-command-carry');count+=1
  if count>=2:sequences.append(dict(script_file=script.name,calls=count,first_result_index=run_start,actual_cli_ram_full_exposed_registers_and_a1_carried=True,stopped_at_negative_terminator=True,entry_context_reset_explicit=True))
 # Reuse fixed-slot sources at bucket head, then rebind using another canonical table.
 palette_all=[(p,c) for p,cs,t in prepared for c in cs if c['opcode']==4]
 palette_commands=[palette_all[0],next(item for item in palette_all if item[1]['operand_hex']!=palette_all[0][1]['operand_hex'])]
 for seed in (0,1):
  ram=fixture(seed);values=incoming(highs[1],palette_commands[0][1]['source_cpu_address']);first=len(rows)
  for index in (0,0,1,1,0):
   script,command=palette_commands[index];values=values[:9]+(command['source_cpu_address'],values[10],values[11]);ram,values=compare(ram,values,script,command,'actual-cli-palette-already-head-and-rebinding-carry')
  sequences.append(dict(calls=5,first_result_index=first,actual_cli_ram_full_exposed_registers_and_a1_carried=True,entry_context_reset_explicit=True,palette_rebinding=True))
 sentinel=b'old-output\0\xff';script,commands,_=prepared[0];good=next((p,c) for p,cs,t in prepared for c in cs if c['opcode']==0x14);script,command=good;values=incoming(highs[1],command['source_cpu_address'])
 def reject(ram=bytes(65536),incoming=values,selected=script,nodefile=node,label='invalid',cmd=None):
  inp.write_bytes(ram);out.write_bytes(sentinel);portfile.write_bytes(sentinel);actual=subprocess.run(cmd or args(incoming,selected,nodefile),capture_output=True,text=True)
  assert actual.returncode and out.read_bytes()==sentinel and portfile.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stderr)
  negatives.append(dict(failure=label,outputs_preserved=True,native_executed=False))
 for size in (0,65535,65537):reject(bytes(size),label='invalid-ram-size')
 for index,value in itertools.product(range(12),('-1','4294967296','0x','1x','')):
  incoming=list(values);incoming[index]=value;reject(incoming=incoming,label='invalid-register-parser')
 for pc in (0,command['source_cpu_address']+1,command['source_cpu_address']+2,0xffffffff):reject(incoming=values[:9]+(pc,values[10],values[11]),label='invalid-command-boundary')
 unsupported=next((p,c) for p,cs,t in prepared for c in cs if c['opcode'] not in SUPPORTED);reject(incoming=values[:9]+(unsupported[1]['source_cpu_address'],values[10],values[11]),selected=unsupported[0],label='unsupported-canonical-opcode')
 malformed=folder/'bad.ms5d';malformed.write_bytes(b'bad');reject(selected=malformed,label='malformed-script-resource');reject(nodefile=malformed,label='malformed-node-resource')
 raw=bytearray(script.read_bytes());raw[-1]^=1;malformed.write_bytes(raw);reject(selected=malformed,label='script-crc-error')
 raw=bytearray(script.read_bytes());offset=command['source_cpu_address']-struct.unpack_from('<I',raw,12)[0]+34;struct.pack_into('>H',raw,offset,2);struct.pack_into('<I',raw,24,zlib.crc32(raw[32:])&0xffffffff);malformed.write_bytes(raw);reject(selected=malformed,label='controlled-resource-invalid-node-selector-no-native-execution')
 for kind in ('same','hardlink','symlink'):
  ram=fixture(0);inp.write_bytes(ram);portfile.write_bytes(sentinel);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True)
   if kind=='hardlink':alias.hardlink_to(inp)
   else:alias.symlink_to(inp)
  cmd=args(values,script);cmd[14]=str(alias);actual=subprocess.run(cmd,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram and portfile.read_bytes()==sentinel
  negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True,native_executed=False))
 negatives.extend(dependency_negatives(root,prepared,exe,node,folder))
 observed=set(row['opcode'] for row in rows);assert observed==SUPPORTED-{0x4c},observed # canonical catalog contains no4c command.
 assert bytes(cpu.mem_read(0x200000,0xffff0))==program[0x200000:0x2ffff0]
 assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,node_resource_sha256=node_sha,dependencies_verified_against_canonical_rom=dependencies,script_files=len(prepared),canonical_total_commands=sum(len(cs) for p,cs,t in prepared),canonical_supported_occurrences=sum(c['opcode'] in SUPPORTED for p,cs,t in prepared for c in cs),canonical_unsupported_occurrences=sum(c['opcode'] not in SUPPORTED for p,cs,t in prepared for c in cs),canonical_unsupported_opcodes=sorted({c['opcode'] for p,cs,t in prepared for c in cs if c['opcode'] not in SUPPORTED}),cases=len(rows),negative_cases=len(negatives),ports=sum(row['result']['writes'] for row in rows),canonical_supported_opcode_counts={hex(op):sum(c['opcode']==op for p,cs,t in prepared for c in cs) for op in sorted(SUPPORTED)},unreached_canonical_opcode_4c=True,full_ram_d0_to_d7_a0_a1_a2_a4_ordered_ports_equal=True,program_code_modified=False,bank_mapping_scope="Physical200000..2fffef uses original ROM2MiB source; PVC register tail excluded from immutable check.",native_a7_rts_endpoint_verified=True,carry_sequences=sequences,results=rows,negative_results=negatives,scope='Actual canonical41MS5D scripts run original1a0b6 dispatcher at each supported opcode address throughhandlerRTS. AllfixedROM bytes unchanged. RandomworkRAM then actual3ef2 palette initialization/highregisters are explicit fixtures, not naturalstageexecution. Canonical scripts contain18of19supportedopcodes;4c hasno canonical occurrence and is not claimed verified. Adjacent supportedruns carry actualCLI RAM/fullreturnedregisters/A1/A2/A4, resettingstandalone callcontext and stoppingat unsupportedopcode or negativeterminator; no fullscript/schedulerclaim. Mutated resource invalidselector negatives are C++validationonly, neverwritteninto originalROM/nativeexecuted. Otherregisters/CCR and hardwaretiming excluded.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),ports=sum(row['result']['writes'] for row in rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

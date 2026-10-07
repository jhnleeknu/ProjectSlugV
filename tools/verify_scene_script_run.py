"""Native1a26a phase-loop differential; explicit host phase updates, no frame timing claim."""
import hashlib,itertools,json,shutil,struct,subprocess
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE,m68k_const as m
from disassemble_program import load_verified_program
from pack_scene_scripts import command_span
from verify_object_reset import make_cpu
from verify_scene_command import REGS,KEYS
from verify_stage_catalog import SOURCE_SHA256,checked_resource
BASE,STACK,RETURN,ENTRY=0x100000,0x1feffc,0xff000,0x1a26a

def main():
 root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);assert source['sha256']==SOURCE_SHA256
 scripts=root/'extracted/runtime/scene_scripts';manifest=json.loads((scripts/'manifest.json').read_text());prepared=[]
 for item in manifest['scripts']:
  end,commands,terminal=command_span(program,item['source_cpu_address']);path=scripts/item['file'];checked_resource(path,program,item['source_cpu_address'],end);prepared.append((path,commands,terminal))
 dependencies=[]
 for item in manifest['dependencies']:
  raw=(scripts/item['file']).read_bytes();h=struct.unpack('<4s7I',raw[:32]);assert h[0]==b'MS5D' and h[1]==1 and h[2]==(2 if item['file'].startswith('palette_') else 1) and h[3]==item['source_cpu_address'] and h[4]==item['source_rom_offset'] and raw[32:]==program[h[4]:h[4]+h[5]];assert hashlib.sha256(raw).hexdigest()==item['sha256'];dependencies.append(item['sha256'])
 folder=root/'artifacts/scene_script_run';folder.mkdir(parents=True,exist_ok=True);inp,out,portsfile,report=[folder/name for name in ('input.bin','cpp.bin','cpp.ports.bin','verification.json')];report.unlink(missing_ok=True)
 exe=root/'build/run_scene_script';binary=hashlib.sha256(exe.read_bytes()).hexdigest();node=scripts/'node_pointers.ms5d'
 cpu=make_cpu(program);cpu.mem_map(0x200000,0x200000);bank={'source':0x200000};trace=[];commands_seen=[];boundary={'reason':None};rows=[];negatives=[];sequences=[]
 def code(cpu,address,size,user):
  if address==RETURN:cpu.emu_stop()
  elif address==0x1a0b6:commands_seen.append(cpu.reg_read(m.UC_M68K_REG_A1))
  elif address in (0x1a276,0x1a290,0x1a29c):boundary['reason']={0x1a276:'no_script',0x1a290:'terminator',0x1a29c:'waiting'}[address]
 def write(cpu,access,address,size,value,user):
  if BASE<=address and address+size<=BASE+65536 or STACK-4096<=address and address+size<=STACK+4:return
  assert address in (0x2ffff2,0x2ffff0,0x300001,0x3c0000,0x3c0006),(hex(address),size,value)
  trace.append((size,address,value&((1<<(size*8))-1)))
  if address==0x2ffff2:
   assert size==2 and value in (0x1000,0x2000);bank['source']=0x200000 if value==0x1000 else 0x300000;cpu.mem_write(0x200000,program[bank['source']:bank['source']+0xffff0])
 cpu.hook_add(UC_HOOK_CODE,code);cpu.hook_add(UC_HOOK_MEM_WRITE,write)
 def context(values):
  cpu.reg_write(m.UC_M68K_REG_A3,0);cpu.reg_write(m.UC_M68K_REG_A6,0);cpu.reg_write(m.UC_M68K_REG_A5,0x108000);cpu.reg_write(m.UC_M68K_REG_A7,STACK);cpu.reg_write(m.UC_M68K_REG_SR,0x2000);cpu.mem_write(STACK,RETURN.to_bytes(4,'big'))
  for reg,value in zip(REGS,values):cpu.reg_write(reg,value)
 def fixture(pointer,phase,threshold,seed=0):
  cpu.mem_write(BASE,hashlib.shake_256(b'scene-script-loop'+bytes([seed])).digest(65536));context((0,)*12);cpu.emu_start(0x3ef2,0xffffff,count=100000);assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN
  ram=bytearray(cpu.mem_read(BASE,65536));struct.pack_into('>IHH',ram,0xd412,pointer,threshold,phase);return ram
 def args(values,script,dir=scripts):return [str(exe)]+list(map(str,values))+list(map(str,(inp,out,portsfile,script,node,dir)))
 def compare(ram,values,script,label):
  cpu.mem_write(BASE,bytes(ram));context(values);trace.clear();commands_seen.clear();boundary['reason']=None;cpu.emu_start(ENTRY,0xffffff,count=3000000)
  assert cpu.reg_read(m.UC_M68K_REG_PC)==RETURN and cpu.reg_read(m.UC_M68K_REG_A7)==STACK+4 and boundary['reason']
  expected=bytes(cpu.mem_read(BASE,65536));result=dict(zip(KEYS,(cpu.reg_read(reg)&0xffffffff for reg in REGS)));result.update(reason=boundary['reason'],commands=len(commands_seen),writes=len(trace));packed=b''.join(struct.pack('>BII',*event) for event in trace)
  inp.write_bytes(ram);actual=subprocess.run(args(values,script),capture_output=True,text=True);assert not actual.returncode,(label,actual.stderr)
  parsed=json.loads(actual.stdout);output=out.read_bytes();actual_ports=portsfile.read_bytes()
  assert output==expected and parsed==result and actual_ports==packed,(label,[(hex(at),a,b) for at,(a,b) in enumerate(zip(expected,output)) if a!=b][:20],result,parsed,'ports',len(trace),hashlib.sha256(actual_ports).hexdigest(),hashlib.sha256(packed).hexdigest())
  name='case-%04d.ports.bin'%len(rows);(folder/name).write_bytes(packed)
  rows.append(dict(profile=label,script_file=script.name,incoming=dict(zip(KEYS,values)),pointer_in=int.from_bytes(ram[0xd412:0xd416],'big'),phase_in=int.from_bytes(ram[0xd418:0xd41a],'big'),threshold_in=int.from_bytes(ram[0xd416:0xd418],'big'),result=parsed,command_addresses=commands_seen.copy(),ports_file=name,ports_sha256=hashlib.sha256(packed).hexdigest(),ports_prefix=trace[:8],ram_sha256=hashlib.sha256(output).hexdigest()))
  assert bytes(cpu.mem_read(0,0x100000))==program[:0x100000] and bytes(cpu.mem_read(0x200000,0xffff0))==program[bank['source']:bank['source']+0xffff0]
  return bytearray(output),tuple(parsed[key] for key in KEYS)
 highs=((0,)*12,(0xabcd1234,0xfedcba98,0x98765432,0x87654321,0xbeefabcd,0x76543210,0x12345678,0xffff5678,0xdeadbeef,0xcafebabe,0xface1234,0xfeedbeef))
 for script,commands,terminal in prepared:
  for phase,threshold,profile in itertools.product((0,1,0x7fff,0x8000,0xffff),(0,1,0xffff),range(2)):
   compare(fixture(commands[0]['source_cpu_address'],phase,threshold,profile),highs[profile],script,'canonical-whole-loop-phase-threshold-high-registers')
  for command in commands:compare(fixture(command['source_cpu_address'],0xffff,0),highs[1],script,'every-canonical-command-cursor-whole-loop')
  first=len(rows);ram=fixture(commands[0]['source_cpu_address'],0,0);values=highs[1]
  for phase in (0,1,0x7fff,0xffff):
   struct.pack_into('>H',ram,0xd418,phase);ram,values=compare(ram,values,script,'actual-cli-carry-explicit-host-phase-update')
  sequences.append(dict(script_file=script.name,first_result_index=first,calls=4,cli_ram_and_full_exposed_registers_carried=True,host_phase_updates=[0,1,0x7fff,0xffff],boundary_context_reset_between_calls_only=True))
 script,commands,terminal=prepared[0]
 for pointer,phase,threshold,label in ((0,0xffff,0,'null-ignores-input-a1'),(0xffffffff,0,1,'waiting-never-dereferences-invalid-cursor'),(terminal,0xffff,0,'negative-terminator')):
  ram=fixture(pointer,phase,threshold);compare(ram,highs[1],script,label)
 sentinel=b'previous-loop-output\0\xff'
 def reject(ram,values,script,label,dir=scripts,custom=None):
  inp.write_bytes(ram);out.write_bytes(sentinel);portsfile.write_bytes(sentinel);actual=subprocess.run(custom or args(values,script,dir),capture_output=True,text=True);assert actual.returncode and out.read_bytes()==sentinel and portsfile.read_bytes()==sentinel and inp.read_bytes()==ram,(label,actual.stdout,actual.stderr);negatives.append(dict(failure=label,outputs_preserved=True,native_bad_fixture_executed=False))
  return actual.stderr
 ram=fixture(commands[0]['source_cpu_address'],0xffff,0)
 for size in (0,65535,65537):reject(bytes(size),highs[1],script,'invalid-ram-size')
 for index,text in itertools.product(range(12),('-1','4294967296','0x','1x','')):
  values=list(highs[1]);values[index]=text;reject(ram,values,script,'invalid-register-parser')
 bad_resource=folder/'bad.ms5d';bad_resource.write_bytes(b'bad')
 for index in (16,17):
  line=args(highs[1],script);line[index]=str(bad_resource);reject(ram,highs[1],script,'malformed-script-or-node-resource-shape',custom=line)
 copied=folder/'dependencies';copied.mkdir(exist_ok=True)
 for item in manifest['dependencies']:shutil.copyfile(scripts/item['file'],copied/item['file'])
 selected,cs,t=next(item for item in prepared if any(c['opcode']==8 for c in item[1]));command=next(c for c in cs if c['opcode']==8);address=int.from_bytes(bytes.fromhex(command['operand_hex']),'big');entry=next(item for item in manifest['dependencies'] if item['source_cpu_address']==address);bad=copied/entry['file'];good=bad.read_bytes();bad.write_bytes(b'bad')
 reject(fixture(cs[0]['source_cpu_address'],0xffff,0),highs[1],selected,'descriptor-preload-error-output-preserved',copied);bad.write_bytes(good)
 raw=bytearray(good);struct.pack_into('<I',raw,12,address+2);struct.pack_into('<I',raw,16,address+2);bad.write_bytes(raw)
 message=reject(fixture(cs[0]['source_cpu_address'],0xffff,0),highs[1],selected,'late-api-descriptor-identity-error-after-command48-output-preserved',copied);assert 'scene setup requires exact fixed descriptor window' in message;bad.write_bytes(good)
 for kind in ('same','hardlink','symlink'):
  inp.write_bytes(ram);portsfile.write_bytes(sentinel);alias=inp if kind=='same' else folder/('alias-'+kind)
  if kind!='same':
   alias.unlink(missing_ok=True);alias.hardlink_to(inp) if kind=='hardlink' else alias.symlink_to(inp)
  commandline=args(highs[1],script);commandline[14]=str(alias);actual=subprocess.run(commandline,capture_output=True,text=True);assert actual.returncode and inp.read_bytes()==ram and portsfile.read_bytes()==sentinel;negatives.append(dict(failure='input-output-'+kind+'-alias',outputs_preserved=True))
 assert hashlib.sha256(exe.read_bytes()).hexdigest()==binary
 report.write_text(json.dumps(dict(source=source,binary_sha256=binary,entry_cpu_address=ENTRY,cases=len(rows),negative_cases=len(negatives),ports=sum(row['result']['writes'] for row in rows),commands=sum(row['result']['commands'] for row in rows),results=rows,negative_results=negatives,carry_sequences=sequences,dependencies_sha256=dependencies,original_rom_modified=False,full_ram_12_registers_reason_command_count_ordered_ports_and_rts_equal=True,scope='Actual1a26a phase gate and all original handlers run without intra-call context reset or ROMpatch. ActualCLI RAM/fullregisters carry between calls; explicit host phase updates and boundary entry stack/SR reset are fixtures, not natural frames/IRQ timing. A3/A6 zero and A5base are explicit inputs outside exposed register contract. Bank2MiB/3MiB payload immutable excluding MMIO tail.'),indent=2)+'\n')
 print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),ports=sum(row['result']['writes'] for row in rows),sha256=hashlib.sha256(report.read_bytes()).hexdigest())))
if __name__=='__main__':main()

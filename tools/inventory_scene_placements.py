"""Fixed-ROM placement header/inline candidates; no callback execution claim."""
import hashlib
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program,disassemble_range
from pack_scene_scripts import SOURCE_SHA256,command_span


def sha(data):return hashlib.sha256(data).hexdigest()


def walk(program,root):
    cursor=root;rows=[];seen=set();errors=[];consumed=0
    while True:
        if cursor in seen:errors.append(dict(cpu_address=cursor,error='cycle'));break
        if len(rows)>=4096 or consumed>=65536:errors.append(dict(cpu_address=cursor,error='bounded_count_or_scan'));break
        if cursor&1 or cursor<0 or cursor+2>min(0x100000,len(program)):errors.append(dict(cpu_address=cursor,error='unaligned_or_outside_fixed_ROM'));break
        seen.add(cursor);gate=struct.unpack_from('>H',program,cursor)[0]
        if gate==0xffff:
            rows.append(dict(cpu_address=cursor,rom_offset=cursor,terminal=True,span_size=2,raw_hex=program[cursor:cursor+2].hex()));cursor+=2;break
        if cursor+16>min(0x100000,len(program)):errors.append(dict(cpu_address=cursor,error='truncated_header'));break
        gate,count,x,y,bounds,callback=struct.unpack_from('>4H2I',program,cursor)
        row=dict(cpu_address=cursor,rom_offset=cursor,terminal=False,gate_word=gate,inline_byte_count_word=count,word_at_4=x,word_at_6=y,bounds_pointer_long=bounds,callback_pointer_long=callback,header_raw_hex=program[cursor:cursor+16].hex(),span_size=16+count,next_cpu_address=cursor+16+count)
        rows.append(row)
        if count&1 or count>=0x8000:row['available_raw_hex']=program[cursor:min(cursor+16+count,0x100000)].hex();errors.append(dict(cpu_address=cursor,error='odd_or_signed_ambiguous_inline_count',value=count));break
        end=cursor+16+count
        if end>min(0x100000,len(program)):errors.append(dict(cpu_address=cursor,error='truncated_inline'));break
        row.update(end_cpu_address_exclusive=end,end_rom_offset_exclusive=end,raw_hex=program[cursor:end].hex(),raw_sha256=sha(program[cursor:end]),inline_raw_hex=program[cursor+16:end].hex())
        if bounds:
            if bounds&1 or bounds+8>min(0x100000,len(program)):row['bounds_status']='outside_or_unaligned_fixed_ROM';errors.append(dict(cpu_address=cursor,error='unsupported_bounds_pointer',pointer=bounds))
            else:row.update(bounds_status='raw8bytes',bounds_cpu_address=bounds,bounds_rom_offset=bounds,bounds_raw_hex=program[bounds:bounds+8].hex(),bounds_sha256=sha(program[bounds:bounds+8]))
        else:row['bounds_status']='null'
        consumed+=16+count;cursor=end
    return dict(root_cpu_address=root,root_rom_offset=root,rows=rows,errors=errors,status='raw_candidates'if not errors else'unsupported_candidates',end_cpu_address_exclusive=cursor)


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=SOURCE_SHA256 or sha(program)!=SOURCE_SHA256:raise ValueError('Unsupported source')
    mb=(root/'extracted/runtime/scene_scripts/manifest.json').read_bytes();manifest=json.loads(mb);references=[]
    for script in manifest['scripts']:
        address=script['source_cpu_address'];end,commands,terminal=command_span(program,address)
        if end!=script['end_exclusive']or sha(program[address:end])!=script['payload_sha256']:raise ValueError('Script manifest/source mismatch')
        for cmd in commands:
            if cmd['opcode']!=0xc:continue
            raw=bytes.fromhex(cmd['operand_hex']);pointer=struct.unpack('>I',raw)[0]
            references.append(dict(script_cpu_address=address,command_cpu_address=cmd['source_cpu_address'],command_rom_offset=cmd['source_cpu_address'],operand_raw_hex=raw.hex(),root_pointer_long=pointer))
    paths=[walk(program,address)for address in sorted({r['root_pointer_long']for r in references if r['root_pointer_long']})]
    record_roots={};unique={}
    for path in paths:
        path['references']=[r for r in references if r['root_pointer_long']==path['root_cpu_address']]
        for row in path['rows']:
            address=row['cpu_address'];record_roots.setdefault(address,[]).append(path['root_cpu_address'])
            if address in unique and unique[address]!=row:raise ValueError('Conflicting shared records')
            unique[address]=row
    intervals=[(a,a+r['span_size'])for a,r in unique.items()if 'raw_hex'in r];overlaps=[]
    for i,(a,b)in enumerate(intervals):
        for c,d in intervals[i+1:]:
            if a<d and b>c:overlaps.append(dict(first_cpu_address=a,second_cpu_address=c,overlap_start=max(a,c),overlap_end_exclusive=min(b,d)))
    ordinary=[r for r in unique.values()if not r['terminal']]
    report=dict(source=source,program_code_modified=False,mapping='Fixed first1MiB CPU address equals ROM offset; bounds/callback LONG values remain raw references.',scene_scripts_manifest_sha256=sha(mb),references=references,paths=paths,reference_count=len(references),unique_root_count=len(paths),unique_record_count=len(ordinary),unique_terminal_count=sum(r['terminal']for r in unique.values()),error_count=sum(len(p['errors'])for p in paths),inline_byte_count_values=sorted({r['inline_byte_count_word']for r in ordinary}),bounds_pointers=sorted({r['bounds_pointer_long']for r in ordinary if r['bounds_pointer_long']}),callback_pointers=sorted({r['callback_pointer_long']for r in ordinary}),shared_record_roots=[dict(cpu_address=a,root_cpu_addresses=rs)for a,rs in record_roots.items()if len(rs)>1],overlap_candidates=overlaps,scope='Main-confirmed raw header/inline sequential grammar only. Exactlyffff firstword terminal; other negative words remain gate fields. Optional bounds onlyfirst8bytes. No callback disassembly/execution, object placement semantics, resource extraction or natural reachability claim.')
    windows=[]
    for start,end in((0x1a414,0x1a526),(0x19802,0x19832),(0x18efa,0x18fd2)):
        instructions=disassemble_range(program,start,end-start,start)
        assert sum(r['size']for r in instructions)==end-start
        windows.append(dict(start_cpu_address=start,start_rom_offset=start,end_exclusive=end,raw_sha256=sha(program[start:end]),instructions=instructions))
    listing=dict(source=source,windows=windows,scope='Explicit bounded instruction candidates only;18efa..18fd2 dispatcher candidate window does not claim full handler completion.')
    output=root/'artifacts/scene_placements';output.mkdir(parents=True,exist_ok=True);hashes={}
    for name,data in(('inventory.json',report),('disassembly.json',listing)):
        path=output/name;path.write_text(json.dumps(data,indent=2)+'\n');hashes[name]=sha(path.read_bytes())
    print(json.dumps(dict(references=len(references),roots=len(paths),records=len(ordinary),terminals=report['unique_terminal_count'],errors=report['error_count'],overlaps=len(overlaps),shared=len(report['shared_record_roots']),hashes=hashes)))

if __name__=='__main__':main()

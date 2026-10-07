"""Raw motion record/time/type inventory; no motion behavior interpretation."""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import struct
import zlib

from disassemble_program import load_verified_program, disassemble_range
from pack_scene_scripts import SOURCE_SHA256, motion_span

WINDOWS = ((0x18c06,0x18efa),(0x18fd2,0x192c4),(0x196ac,0x19768),(0x19938,0x19978))


def inspect_resource(path, metadata, program):
    packed = path.read_bytes()
    if len(packed) < 32:
        raise ValueError('Truncated motion header')
    magic, version, kind, cpu, rom, size, crc, reserved = struct.unpack('<4s7I',packed[:32])
    payload = packed[32:]
    if (magic,version,kind,reserved) != (b'MS5D',1,1,0) or size != len(payload) or zlib.crc32(payload) != crc:
        raise ValueError('Invalid motion MS5D header/length/CRC')
    if cpu != rom or cpu != metadata['source_cpu_address'] or rom != metadata['source_rom_offset']:
        raise ValueError('Motion source addresses changed')
    if hashlib.sha256(packed).hexdigest() != metadata['sha256'] or hashlib.sha256(payload).hexdigest() != metadata['payload_sha256']:
        raise ValueError('Motion manifest hashes changed')
    if payload != program[rom:rom+size]:
        raise ValueError('Motion raw bytes differ from canonical')
    end, count, first_type, terminal = motion_span(program,cpu)
    if end != cpu + size:
        raise ValueError('Motion raw extent differs from exact extracted window')
    rows=[]
    for offset in range(0, len(payload)-4,10):
        time, kind, value4, value6, value8 = struct.unpack_from('>5H',payload,offset)
        rows.append(dict(cpu_address=cpu+offset,rom_offset=rom+offset,resource_offset=offset,
            time_word=time,type_word=kind,word_at_4=value4,word_at_6=value6,word_at_8=value8,
            raw_hex=payload[offset:offset+10].hex()))
    assert len(rows)==count
    terminal_time, terminal_type = struct.unpack_from('>2H',payload,len(payload)-4)
    assert terminal_type==0xffff
    times=[row['time_word'] for row in rows]
    all_times=times+[terminal_time]
    comparisons=[dict(previous_cpu_address=cpu+(i-1)*10,current_cpu_address=cpu+i*10,
        previous_time=all_times[i-1],current_time=all_times[i],
        relation='increase' if all_times[i]>all_times[i-1] else 'equal' if all_times[i]==all_times[i-1] else 'decrease',
        current_is_terminal=i==len(rows)) for i in range(1,len(all_times))]
    return dict(id=metadata['id'],file=metadata['file'],source_cpu_address=cpu,source_rom_offset=rom,
        payload_size=size,container_sha256=hashlib.sha256(packed).hexdigest(),payload_sha256=hashlib.sha256(payload).hexdigest(),
        references=metadata['references'],records=rows,ordinary_record_count=len(rows),first_type_word=first_type,
        terminal=dict(cpu_address=terminal,rom_offset=terminal,resource_offset=size-4,
            time_word=terminal_time,type_word=terminal_type,raw_hex=payload[-4:].hex()),
        time_comparisons=comparisons,
        ordinary_time_nondecreasing=all(a<=b for a,b in zip(times,times[1:])),
        including_terminal_time_nondecreasing=all(a<=b for a,b in zip(all_times,all_times[1:])),
        ordinary_time_strictly_increasing=all(a<b for a,b in zip(times,times[1:])),
        interpretation='Unsigned BE16 raw time ordering only; no clock/wrap/duration semantics inferred')



def dispatch_inventory(program, source):
    tables=[]
    specifications=((0x18c06,0x18c0e,0x18c9e,0x18caa),
                    (0x18caa,0x18cb2,0x18d42,0x18efa),
                    (0x18fd2,0x18fda,0x1906a,0x192b2))
    for entry,base,body_start,body_end in specifications:
        entries=[]
        for i in range(36):
            address=base+i*4
            decoded=disassemble_range(program,address,4,address)
            if len(decoded)!=1 or decoded[0]['size']!=4 or decoded[0]['mnemonic']!='bra.w':
                raise ValueError('Expected exact first four-byte BRA dispatch entry')
            match=re.fullmatch(r'\$([0-9a-f]+)',decoded[0]['op_str'])
            if match is None:raise ValueError('Dispatch BRA target not direct hexadecimal address')
            target=int(match[1],16)
            if not body_start<=target<body_end:raise ValueError('Dispatch target outside explicit body window')
            entries.append(dict(type_word=i*4,dispatch_cpu_address=address,dispatch_rom_offset=address,
                target_cpu_address=target,target_rom_offset=target,branch_instruction=decoded[0]))
        targets=sorted({item['target_cpu_address'] for item in entries})
        bodies={}
        for i,target in enumerate(targets):
            end=targets[i+1] if i+1<len(targets) else body_end
            instructions=disassemble_range(program,target,end-target,target)
            assert sum(row['size'] for row in instructions)==end-target
            bodies[target]=dict(start_cpu_address=target,start_rom_offset=target,end_exclusive=end,
                raw_sha256=hashlib.sha256(program[target:end]).hexdigest(),instructions=instructions,
                rts_candidate_addresses=[row['cpu_address']for row in instructions if row['mnemonic']=='rts'],
                scope='Full explicit target-to-next-target window; no branch following or routine completion claim.')
        for item in entries:item['handler_window']=bodies[item['target_cpu_address']]
        tables.append(dict(entry_cpu_address=entry,entry_rom_offset=entry,table_cpu_address=base,
            entry_prefix_instructions=disassemble_range(program,entry,base-entry,entry),entry_count=36,
            body_start_cpu_address=body_start,body_end_exclusive=body_end,entries=entries))
    shared=disassemble_range(program,0x192b2,0x12,0x192b2)
    return dict(source=source,program_code_modified=False,
        mapping='Explicit fixed first1MiB CPU address equals ROM offset.',tables=tables,
        shared_window=dict(start_cpu_address=0x192b2,start_rom_offset=0x192b2,end_exclusive=0x192c4,instructions=shared,
            raw_sha256=hashlib.sha256(program[0x192b2:0x192c4]).hexdigest()),
        scope='Three36-entry raw BRA dispatch tables. Only first direct BRA target confirmed from bounded row operand. '
            'Handler bodies stop at next distinct target or supplied end, not firstRTS; RTS candidates and shared192b2 window listed without execution or symbolic motion interpretation.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='artifacts/scene_motion');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    if source['sha256']!=SOURCE_SHA256:raise ValueError('Unsupported canonical source')
    folder=root/'extracted/runtime/scene_scripts';manifest_path=folder/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    if manifest['source']['sha256']!=SOURCE_SHA256:raise ValueError('Manifest source mismatch')
    metadata=[item for item in manifest['dependencies'] if item['file'].startswith('motion_')]
    paths=[inspect_resource(folder/item['file'],item,program) for item in metadata]
    for path in paths:
        for reference in path['references']:
            reference['stage_catalog_references']=[dict(group=item['group'],area=item['area'],record_cpu_address=item['record_cpu_address'])
                for item in manifest['references'] if item['script_cpu_address']==reference['script_cpu_address']]
    assert len(paths)==37 and sum(len(path['references']) for path in paths)==39
    rows=[row for path in paths for row in path['records']]
    counts=Counter(row['type_word'] for row in rows)
    weighted=Counter()
    for path in paths:
        for row in path['records']:weighted[row['type_word']]+=len(path['references'])
    report=dict(source=source,manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        program_code_modified=False,mapping='Fixed first1MiB motion CPU address equals canonical ROM offset.',
        path_count=len(paths),script_command_reference_count=sum(len(path['references'])for path in paths),
        ordinary_record_count=len(rows),terminal_record_count=len(paths),paths=paths,
        type_counts_unique_paths=[dict(type_word=kind,count=count)for kind,count in sorted(counts.items())],
        type_counts_weighted_by_script_command_references=[dict(type_word=kind,count=count)for kind,count in sorted(weighted.items())],
        ordinary_time_nondecreasing_path_count=sum(path['ordinary_time_nondecreasing']for path in paths),
        including_terminal_time_nondecreasing_path_count=sum(path['including_terminal_time_nondecreasing']for path in paths),
        limitations='Raw10-byte records+four-byte terminal and unsigned word ordering only. Each unique path counted once; separate reference-weighted counts are syntax frequency, not natural execution. '
            'Subsequent type effects, time scheduling/wrap and motion interpreter are not analyzed/executed.')
    output=Path(args.output);output=output if output.is_absolute()else root/output;output.mkdir(parents=True,exist_ok=True)
    result=output/'inventory.json';result.write_text(json.dumps(report,indent=2)+'\n')
    windows=[]
    for start,end in WINDOWS:
        instructions=disassemble_range(program,start,end-start,start)
        assert sum(row['size'] for row in instructions)==end-start
        assert all(row['rom_offset']+row['size']<=end for row in instructions)
        windows.append(dict(start_cpu_address=start,start_rom_offset=start,end_exclusive=end,
            raw_sha256=hashlib.sha256(program[start:end]).hexdigest(),instructions=instructions))
    disassembly=output/'disassembly.json'
    disassembly.write_text(json.dumps(dict(source=source,program_code_modified=False,
        mapping='Explicit first1MiB fixed-ROM CPU address equals ROM offset.',windows=windows,
        scope='Complete assigned bounded windows only. Capstone instruction candidates, not native execution, proven ownership or complete motion semantics. '
            'No stop at firstRTS. Truncated/invalid tail words preserved by disassemble_range; window endpoints not assumed whole-function boundaries.'),indent=2)+'\n')
    dispatch=output/'dispatch.json'
    dispatch.write_text(json.dumps(dispatch_inventory(program,source),indent=2)+'\n')
    print(json.dumps(dict(paths=len(paths),references=report['script_command_reference_count'],records=len(rows),
        type_counts=report['type_counts_unique_paths'],ordinary_monotone=report['ordinary_time_nondecreasing_path_count'],
        including_terminal_monotone=report['including_terminal_time_nondecreasing_path_count'],sha256=hashlib.sha256(result.read_bytes()).hexdigest(),
        disassembly_rows=sum(len(window['instructions']) for window in windows),
        disassembly_sha256=hashlib.sha256(disassembly.read_bytes()).hexdigest(),
        dispatch_sha256=hashlib.sha256(dispatch.read_bytes()).hexdigest())))


if __name__=='__main__':main()

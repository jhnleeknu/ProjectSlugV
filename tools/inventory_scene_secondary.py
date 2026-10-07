"""Bank2 secondary lookup raw references only; no data extent interpretation."""
import hashlib
import json
from pathlib import Path
import struct
from disassemble_program import load_verified_program
from pack_scene_scripts import SOURCE_SHA256


def sha(data):return hashlib.sha256(data).hexdigest()


def bank2(address,size):
    if address<0x200000 or address+size>0x2ffff0:raise ValueError('Lookup outside bank2/PVC boundary')
    return address


def column_candidates(program,pointer,width,height):
    if pointer==0xffffffff:return dict(status='sentinel',columns=[],errors=[])
    columns=[];errors=[]
    table_end=pointer+4*width
    for index in range(2*width):
        entry=pointer+2*index
        if entry&1 or entry<0x200000 or entry+2>min(0x2ffff0,len(program)):
            errors.append(dict(column_index=index,entry_cpu_address=entry,error='offset_word_outside_or_unaligned_bank2'));continue
        raw=program[entry:entry+2];word=struct.unpack('>H',raw)[0];signed=word if word<0x8000 else word-0x10000
        start=entry+signed;end=start+height*4
        valid=not start&1 and start>=0x200000 and end<=min(0x2ffff0,len(program))
        row=dict(column_index=index,offset_entry_cpu_address=entry,offset_entry_rom_offset=entry,offset_raw_hex=raw.hex(),offset_word=word,signed_offset=signed,cell_start_cpu_address=start,cell_end_cpu_address_exclusive=end,cell_byte_count=height*4,cell_row_count=height,source_row_base=0,source_column_base=0,overlaps_offset_candidate_window=start<table_end and end>pointer,bounds_valid=valid)
        if valid:row.update(cell_start_rom_offset=start,cell_end_rom_offset_exclusive=end,cell_raw_hex=program[start:end].hex(),cell_sha256=sha(program[start:end]))
        else:errors.append(dict(column_index=index,error='cell_window_outside_or_unaligned_bank2',start=start,end=end))
        columns.append(row)
    for row in columns:
        start,end=row['cell_start_cpu_address'],row['cell_end_cpu_address_exclusive']
        row['overlapping_column_indices']=[other['column_index']for other in columns if other['column_index']!=row['column_index'] and start<other['cell_end_cpu_address_exclusive'] and end>other['cell_start_cpu_address']]
        row['identical_cell_window_column_indices']=[other['column_index']for other in columns if other['column_index']!=row['column_index'] and (start,end)==(other['cell_start_cpu_address'],other['cell_end_cpu_address_exclusive'])]
    return dict(status='candidate_windows'if not errors else'unsupported_bounds',offset_candidate_start_cpu_address=pointer,offset_candidate_end_cpu_address_exclusive=table_end,offset_candidate_count=2*width,columns=columns,errors=errors,scope='Full descriptor width/height candidate reads with sourceColumn/sourceRow base0. Each signed offset is relative to its own two-byte entry address. Distinct/overlapping/aliased cell windows retained; no continuous total data extent inferred.')


def inventory(program,source,paths,input_bytes):
    if source['sha256']!=SOURCE_SHA256 or sha(program)!=SOURCE_SHA256:raise ValueError('Unsupported source')
    if paths['source']!=source:raise ValueError('Path source differs')
    slot=0x200010;rawroot=program[slot:slot+4];base=struct.unpack('>I',rawroot)[0]
    references=[];descriptors={}
    for path in paths['paths']:
        for row in path['rows']:
            if row['opcode_word']!=4 or row['terminal']:continue
            address=row['descriptor_cpu_address'];raw=bytes.fromhex(row['descriptor_raw_hex'])
            if address!=row['cpu_address']+2 or address&1 or address+12>0x100000 or len(raw)!=12 or program[address:address+12]!=raw:raise ValueError('Descriptor bytes/address differ')
            primary,secondary,width,height,column=struct.unpack('>4HI',raw)
            if (primary,secondary,width,height,column)!=(row['map_selector_word'],row['word_at_2'],row['width_word'],row['height_word'],row['column_pointer_long']):raise ValueError('Descriptor raw/metadata differ')
            if 'secondary_selector_word'in row and secondary!=row['secondary_selector_word']:raise ValueError('Secondary metadata differs')
            if secondary==0:continue
            shifted=(secondary<<2)&0xffff;offset=shifted if shifted<0x8000 else shifted-0x10000
            lookup=base+offset;bank2(lookup,4);rawlookup=program[lookup:lookup+4];pointer=struct.unpack('>I',rawlookup)[0]
            classification='sentinel_ffffffff'if pointer==0xffffffff else'bank2_pointer_candidate'if 0x200000<=pointer<0x2ffff0 and not pointer&1 else'outside_or_unaligned_pointer_candidate'
            descriptor=dict(descriptor_cpu_address=address,descriptor_rom_offset=address,descriptor_raw_hex=raw.hex(),descriptor_sha256=sha(raw),primary_selector_word=primary,secondary_selector_word=secondary,width_word=width,height_word=height,column_pointer_long=column,shifted_word=shifted,signed_lookup_offset=offset,lookup_cpu_address=lookup,lookup_rom_offset=lookup,lookup_raw_hex=rawlookup.hex(),lookup_sha256=sha(rawlookup),pointer_long=pointer,pointer_classification=classification,column_candidates=column_candidates(program,pointer,width,height))
            if address in descriptors and descriptors[address]!=descriptor:raise ValueError('Conflicting repeated descriptor')
            descriptors[address]=descriptor
            references.append(dict(path_root_cpu_address=path['root_cpu_address'],descriptor_cpu_address=address,script_references=path['references']))
    rows=[descriptors[a]for a in sorted(descriptors)]
    columns=[c for r in rows for c in r['column_candidates']['columns']]
    report=dict(source=source,program_code_modified=False,mapping='Bank2 CPU200000..2fffef equals physical ROM offsets; PVC overlay excluded.',scene_paths_inventory_sha256=sha(input_bytes),root=dict(cpu_address=slot,rom_offset=slot,raw_hex=rawroot.hex(),sha256=sha(rawroot),pointer_long=base),references=references,descriptors=rows,reference_count=len(references),unique_descriptor_count=len(rows),unique_selector_count=len({r['secondary_selector_word']for r in rows}),unique_lookup_count=len({r['lookup_cpu_address']for r in rows}),classification_counts={k:sum(r['pointer_classification']==k for r in rows)for k in sorted({r['pointer_classification']for r in rows})},unique_pointer_count=len({r['pointer_long']for r in rows}),column_candidate_count=len(columns),cell_read_candidate_count=sum(c['cell_row_count']for c in columns),aliased_column_count=sum(bool(c['identical_cell_window_column_indices'])for c in columns),column_bounds_error_count=sum(len(r['column_candidates']['errors'])for r in rows),scope='Nonzero secondary descriptor references and exact four-byte signed-offset lookups plus descriptor-width/height column candidate reads. Pointer candidates are not proven data spans; main-confirmed per-entry relative column candidate windows; no logical table extent, interpreter execution or C++ equivalence claim.')
    return report


def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root)
    input_bytes=(root/'artifacts/scene_paths/inventory.json').read_bytes()
    report=inventory(program,source,json.loads(input_bytes),input_bytes)
    output=root/'artifacts/scene_secondary';output.mkdir(parents=True,exist_ok=True);path=output/'inventory.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(root=report['root']['pointer_long'],references=report['reference_count'],descriptors=report['unique_descriptor_count'],selectors=report['unique_selector_count'],classification_counts=report['classification_counts'],column_bounds_errors=report['column_bounds_error_count'],report_sha256=sha(path.read_bytes()))))

if __name__=='__main__':main()

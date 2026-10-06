"""Inventory immediate animation-init candidates and bounded branch paths."""
import json
from pathlib import Path
from disassemble_program import load_verified_program


def main():
    root=Path(__file__).resolve().parents[1];p,source=load_verified_program(root)
    if source['sha256']!='29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f': raise ValueError('Unsupported ROM')
    records=[]
    for at in range(0,0x100000-16,2):
        if p[at:at+2]!=bytes.fromhex('227c') or p[at+6:at+8]!=bytes.fromhex('303c') or p[at+10:at+16]!=bytes.fromhex('4eb900049f8c'):continue
        base=int.from_bytes(p[at+2:at+6],'big');cursor=base;seen=set();path=[]
        while cursor not in seen and 0<=cursor<0xffff8 and len(seen)<100:
            seen.add(cursor);opcode=p[cursor]
            row={'address':cursor,'opcode':opcode};path.append(row)
            if opcode==0:cursor+=2
            elif opcode==4:cursor+=8
            elif opcode==8:cursor=int.from_bytes(p[cursor+2:cursor+6],'big')
            elif opcode==12:
                selector=int.from_bytes(p[cursor+2:cursor+4],'big')
                row.update({'desired':p[cursor+1],'selector':selector,'target':int.from_bytes(p[cursor+4:cursor+8],'big')})
                if selector<145:row['field_offset']=int.from_bytes(p[0x4a76c+selector*2:0x4a76e+selector*2],'big')
                records.append({'candidate_setup':at,'candidate_call':at+10,'script_base':base,
                                'decrement':int.from_bytes(p[at+8:at+10],'big'),'path_to_first_branch':path})
                break
            else:break
    destination=root/'artifacts/animation_references';destination.mkdir(parents=True,exist_ok=True)
    (destination/'references.json').write_text(json.dumps({'source':source,'candidate_count':len(records),
        'scope':'Aligned immediate movea/move/jsr patterns and bounded known-opcode walks. Candidates require caller validation; not exhaustive references or natural reachability proof.',
        'records':records},indent=2)+'\n')
    print('Immediate setup candidates reaching a conditional branch:',len(records))


if __name__=='__main__':main()

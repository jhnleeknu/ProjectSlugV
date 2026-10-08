"""Pinned spatial instruction windows and existing nine-byte read probes."""
import json
from pathlib import Path
from disassemble_program import load_verified_program
from inventory_stage_input_callbacks import bounded,require,sha
from inventory_object_removal import controls
from inventory_game_initialization import asm
from observe_scene_general_initialization import resources
from pack_stage_input import SOURCE_SHA256
WINDOWS=((0x46f52,0x4701e),(0x4701e,0x4706c),(0x43e38,0x43ea4))
def inventory(root):
    program,source=load_verified_program(root)
    require(sha(program)==SOURCE_SHA256,'Original source changed')
    windows=[bounded(program,a,b) for a,b in WINDOWS]
    rows={r['cpu_address']:r for w in windows for r in w['instructions']}
    literals=((0x46f76,'movem.w','(a1)+, d4-d7'),(0x46fcc,'cmp.w','d5, d1'),(0x46f6c,'exg.l','d2, d0'),(0x46f74,'exg.l','d3, d1'),(0x47064,'subq.w','#$1, $567c(a5)'),(0x47068,'bcc.b','$47040'),(0x4700c,'dbra','d2, $4700a'),(0x47018,'dbra','d3, $47016'),(0x46fac,'dbra','d6, $46faa'))
    for at,op,args in literals:require((rows[at]['mnemonic'],rows[at]['op_str'])==(op,args),'Literal changed')
    require(all(rows[a]['raw']=='20c0' for a in range(0x47024,0x47036,2)),'Nine LONG clears changed')
    items,manifests=resources(root,program);selected=[]
    require(len(items)==458,'Resource set changed')
    for role in ('fixed','bank2','bank3'):
        candidates=[r for r in items if r['size']>=9 and ((role=='fixed' and r['kind']==1 and r['cpu']==r['rom']) or (role=='bank2' and r['kind']==2 and r['cpu']==r['rom']) or (role=='bank3' and r['kind']==2 and r['rom']==r['cpu']+0x100000))]
        r=candidates[0];raw=(root/r['file']).read_bytes()[32:41]
        require(raw==program[r['rom']:r['rom']+9],'Probe differs from source')
        selected.append(dict(role=role,**r,raw_hex=raw.hex(),byte_count=9))
    return dict(source=source,windows=windows,row_count=len(rows),gap_count=0,undecoded=sum(w['undecoded_row_count'] for w in windows),controls=[c for w in windows for c in controls(w['instructions'])],literal_checks=len(literals)+9,resource_count=len(items),resource_read_fixtures=selected,manifests=manifests,source_modified=False,scope='Bounded instruction windows; CPU=ROM fixed. Nine-byte probes use existing verified MS5D; not natural records or usage claims. See docs/analysis/stage-spatial-frame.md.')
def main():
    root=Path(__file__).resolve().parents[1];r=inventory(root);p=root/'artifacts/stage_spatial_frame_inventory.json';p.write_text(json.dumps(r,indent=2)+'\n');(p.with_suffix('.asm')).write_text('\n'.join(asm(w['instructions']) for w in r['windows'])+'\n');print(json.dumps(dict(rows=r['row_count'],undecoded=r['undecoded'],sha256=sha(p.read_bytes()))))
if __name__=='__main__':main()

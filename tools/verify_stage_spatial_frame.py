"""Whole original spatial calls compared with the actual C++ CLI."""
import collections
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
from disassemble_program import load_verified_program
from inventory_stage_spatial_frame import inventory
from observe_stage_region_frame import Observer,KEYS,BASE,STACK,RETURN
from observe_scene_motion_pair import oracle_provenance
from observe_scene_frame_execution import oracle_provenance as unicorn_provenance

def sha(data):return hashlib.sha256(data).hexdigest()
def cases():
    result=[]
    def add(**kw):
        c=dict(entry=0x46f52,bank=2,carry=0,xy=[0,128,0,128],raw=[0,0,0,0],category=0,index=0,slot=0,timer=0,parent=0,stamp=0,role='RAM',all_active=False);c.update(kw);result.append(c)
    for x,y,cat in itertools.product((-32768,-97,-96,-95,0,511,512,32767),(-32768,127,128,129,511,512,32767),(0,64,128,192)):
        add(xy=[x,y,x,y],category=cat,index=cat//64)
    add(xy=[-97,128,0,800],category=64,index=7)
    add(xy=[0,128,32767,128],category=0,index=0)  # Signed SUB overflow; writes beyond logical bins.
    for reverse,raw,cat in itertools.product((False,True),([0,0,4,3],[0xffff,0xffff,4,3],[1,1,4,3]),(0,63,64,127,128,191,192,255)):
        add(xy=[100,180,-50,128] if reverse else [-50,128,100,180],raw=raw,category=cat,index=0xffff)
    for raw in ([0x8000,0x7fff,0xffff,0x8000],[0xffff,0xffff,0xffff,0xffff]):add(xy=[600,128,600,128],raw=raw,category=255,index=0x8007)
    for slot,timer,parent,stamp in itertools.product(range(8),(0,1,0xffff),(0,1),(0,1,2)):
        add(entry=0x4701e,slot=slot,timer=timer,parent=parent,stamp=stamp,category=(slot%4)*64,index=slot)
    add(entry=0x4701e,all_active=True,timer=1,parent=1)
    add(entry=0x4701e,slot=7,raw=[0,0,220,0],extra_nodes=True)
    for role in ('fixed','bank2','bank3'):
        add(role=role,bank=3 if role=='bank3' else 2,xy=[32767,128,32767,128])
    for step in range(4):add(entry=0x4701e,all_active=True,timer=3,parent=1,sequence=step)
    return result

def fixture(c,resources):
    ram=bytearray(hashlib.shake_256(b'spatial-frame').digest(65536));regs=[(0x12340000+i*0x10001)&0xffffffff for i in range(14)];regs[13]=0x106f01;regs[8]=0x102100
    def put(at,v,n=2):ram[at:at+n]=(v&((1<<(8*n))-1)).to_bytes(n,'big')
    source=0x106000;ram[0x6000:0x6009]=struct.pack('>4HB',*c['raw'],c['category'])
    if c['role']!='RAM':source=next(r['cpu'] for r in resources if r['role']==c['role'])
    ram[0x2000:0x2026]=bytes(0x26);put(0x2014,0x10001,4);put(0x2018,0x20001,4);ram[0x2025]=3
    def node(at,active):
        ram[at:at+0x2c]=bytes(0x2c)
        put(at,c['xy'][0]<<16,4);put(at+4,c['xy'][1]<<16,4)
        for off,v in zip((0x1c,0x20,0x14,0x18),c['xy']):put(at+off,v)
        put(at+0x26,source if active else 0x80000000,4);put(at+0x2a,c['timer']);put(at+0x10,0x102000 if c['parent'] else 0,4);ram[at+0x24]=c['stamp']
    node(0x2100,True)
    for slot in range(265 if c.get('extra_nodes') else 8):node(0xd61a-slot*0x2c,c['all_active'] or slot==c['slot'])
    put(0xd67c,c['index']);ram[0xd494]=1
    return ram,regs

def invoke(root,c,ram,regs,files):
    folder=root/'artifacts/stage_spatial_frame';inp,out=folder/'input.bin',folder/'cpp.bin';inp.write_bytes(ram);out.write_bytes(b'preserve-on-error')
    p=subprocess.run([str(root/'build/step_stage_spatial_frame'),str(c['entry'])]+list(map(str,regs))+[str(c['bank']),str(inp),str(out)]+[str(root/f) for f in files],capture_output=True,text=True)
    assert inp.read_bytes()==ram
    return p,out.read_bytes()

def provenance(root,resources):
    names=['build/step_stage_spatial_frame','engine/src/stage_spatial_frame.cpp','engine/include/ms5/stage_spatial_frame.h','engine/tools/step_stage_spatial_frame.cpp','engine/src/scene_node.cpp','engine/include/ms5/scene_node.h','engine/src/fixed_data_resource.cpp','engine/include/ms5/fixed_data_resource.h','tools/verify_stage_spatial_frame.py','tools/inventory_stage_spatial_frame.py','tools/observe_stage_region_frame.py','tools/disassemble_program.py','tools/inventory_stage_input_callbacks.py','tools/observe_scene_general_initialization.py','engine/include/ms5/scene_map_transfer.h','artifacts/stage_spatial_frame_inventory.json']
    names += [r['file'] for r in resources]
    return [dict(file=f,sha256=sha((root/f).read_bytes())) for f in names]

def main():
    root=Path(__file__).resolve().parents[1];program,source=load_verified_program(root);audit=inventory(root);assert audit==json.loads((root/'artifacts/stage_spatial_frame_inventory.json').read_text());resources=audit['resource_read_fixtures'];files=[r['file'] for r in resources]
    folder=root/'artifacts/stage_spatial_frame';folder.mkdir(parents=True,exist_ok=True);inputs=provenance(root,resources);primary=oracle_provenance(root);secondary=unicorn_provenance();native=Observer(program);banked=Observer(program,True);rows=[];previous=None;branches=collections.defaultdict(collections.Counter)
    branch_addresses={r['cpu_address'] for w in audit['windows'] for r in w['instructions'] if r['mnemonic'].split('.')[0] in ('ble','bge','blt','bgt','bcc','bmi','beq','bne','dbra')}
    for i,c in enumerate(cases()):
        ram,regs=fixture(c,resources) if not c.get('sequence',0) else (bytearray(previous[0]),previous[1]);cpu=banked if c['role'].startswith('bank') else native
        expected,result,info=cpu.run(c,ram,regs);result.pop('carry');p,actual=invoke(root,c,ram,regs,files)
        assert p.returncode==0 and actual==expected and json.loads(p.stdout)==result,(i,c,p.stderr,p.stdout,result)
        if c.get('extra_nodes'):
            assert info['pcs'].count(0x47040)==265 and result['a0']==0x10d61a-265*0x2c and expected[0xd67c:0xd67e]==b'\xff\xff'
        if c['role'].startswith('bank'):
            probe=next(r for r in resources if r['role']==c['role'])
            assert {r['address'] for r in info['banked_reads']}=={probe['cpu']+x for x in (0,2,4,6,8)}
        replay=ram.copy()
        for w in info['RAM_writes']:
            at=w['address']-BASE;replay[at:at+w['size']]=w['value'].to_bytes(w['size'],'big')
        assert replay==expected and result['a3']==regs[11] and result['a6']==regs[13]
        pcs=info['pcs']+[RETURN]
        for a,b in zip(pcs,pcs[1:]):
            if a in branch_addresses:branches[a][b]+=1
        name='native_%04d.bin'%i;(folder/name).write_bytes(expected)
        rows.append(dict(case=c,input_sha256=sha(ram),incoming=dict(zip(KEYS,regs)),result=result,ram_file=name,ram_sha256=sha(expected),**info))
        if 'sequence'in c:previous=(actual,[result[k] for k in KEYS])
    negatives=[]
    c=cases()[0];ram,regs=fixture(c,resources)
    for label,entry,bank,ptr in (('entry',0,2,0x106000),('bank',0x46f52,4,0x106000),('odd-source',0x46f52,2,0x106001),('late-category',0x46f52,2,0x10fff8),('missing-window',0x46f52,2,0x200000)):
        r=ram.copy();r[0x2126:0x212a]=ptr.to_bytes(4,'big');q=dict(c,entry=entry,bank=bank);p,out=invoke(root,q,r,regs,[]);assert p.returncode and not p.stdout and out==b'preserve-on-error';negatives.append(label)
    from verify_scene_motion_bounds import container
    directory_checks=[]
    for resource in resources:
        c=next(c for c in cases() if c['role']==resource['role']);r,regs=fixture(c,resources)
        expected,result,info=(banked if c['role'].startswith('bank') else native).run(c,r,regs);result.pop('carry')
        p,out=invoke(root,c,r,regs,[str(Path(resource['file']).parent)])
        assert p.returncode==0 and out==expected and json.loads(p.stdout)==result
        directory_checks.append(resource['role'])
        raw=bytes.fromhex(resource['raw_hex']);partial=folder/'partial.ms5d'
        partial.write_bytes(container(raw[:8],cpu=resource['cpu'],rom=resource['rom'],kind=resource['kind']))
        p,out=invoke(root,c,r,regs,[str(partial)]);assert p.returncode and not p.stdout and out==b'preserve-on-error';negatives.append('missing-category-'+resource['role'])
    # This branch cannot be taken after the immediately preceding D1 clamp.
    assert set(branches[0x46fde])=={0x46fe2}
    assert all(len(branches[a])==2 for a in branch_addresses if a!=0x46fde), {hex(a):dict(branches[a]) for a in branch_addresses if len(branches[a])!=2}
    assert provenance(root,resources)==inputs and oracle_provenance(root)==primary and unicorn_provenance()==secondary and sha((root/source['path']).read_bytes())==source['sha256']
    report=dict(source=source,inputs=inputs,oracle=primary,banked_oracle=secondary,cases=len(rows),negative_cases=negatives,directory_checks=directory_checks,branches={hex(a):{hex(b):n for b,n in v.items()} for a,v in branches.items()},results=rows,scope='Whole original entry4701e/46f52, no stubs or ROM patches. Existing region Observer supplies unchanged emulator plumbing; its carry field is discarded. FullRAM/14registers/bank and ordered native RAM-write replay agree. A3/A6 preserved. Four fullframe calls carry actual previous CLI output without host rewrites. No whole-game or IRQ timing claim.')
    path=folder/'verification.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(cases=len(rows),negative_cases=len(negatives),sha256=sha(path.read_bytes()))))
if __name__=='__main__':main()

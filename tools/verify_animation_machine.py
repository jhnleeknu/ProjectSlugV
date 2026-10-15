"""Actual public animation machine vs unpatched shared-stack original evidence.

Harness is test plumbing, not a production CLI. No old continuation metadata is
injected; same-chain resumes receive previous actual C++ outputs + host writes.
"""
import hashlib
import inspect
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import observe_animation_shared_stack as native
import observe_animation_machine_extended as extended
import pack_physical_program as physical
from address_map import pvc_bank_update

NATIVE_SHA = '43a6627828fa9047ba1b3a89becc0731c1f19e38aa2f1f2dd8f4f9e098cb94cc'
EXTENDED_SHA = '5ca26b65cb413860fab9fb5b488023665f2a5ec7dd27a729d6e71734c7262029'
REGS = tuple('d%d'%i for i in range(8))+tuple('a%d'%i for i in range(8))
STATE_KEYS = REGS+('pc','carry')
KEYS = set(STATE_KEYS)|{'bank_base','external_reads','status','ok'}
SOURCES = ('animation_machine.cpp','animation_machine_interpreter.cpp','animation_machine_sprite.cpp',
           'animation_machine_sound.cpp','animation_machine_readiness.cpp','animation_machine_hud.cpp','animation_machine_transition.cpp','animation_machine_exit.cpp','animation_machine_screen.cpp','animation_machine_cleanup.cpp','animation_machine_scene.cpp','animation_machine_palette_bind.cpp','animation_machine_map_transfer.cpp','animation_machine_fade_card.cpp','animation_machine_card_child.cpp','animation_machine_card_menu.cpp','animation_machine_card_menu_open.cpp','animation_machine_card_menu_input.cpp','animation_machine_card_menu_close.cpp','animation_machine_card_menu_save.cpp','animation_machine_card_menu_nested.cpp','animation_machine_frame_helpers.cpp','animation_machine_scene_core.cpp','animation_machine_motion_walk.cpp','animation_machine_scene_update.cpp','animation_machine_script_placement.cpp','animation_machine_input.cpp','animation_machine_buffer_cue.cpp','animation_machine_stage_entry.cpp','animation_machine_area_clear.cpp','animation_machine_stage_catalog.cpp','animation_machine_stage_area.cpp','animation_machine_stage_event.cpp','animation_machine_stage_event_ops.cpp','animation_machine_scheduler.cpp','animation_machine_objects_u01.cpp','animation_machine_objects_u02.cpp','animation_machine_objects_u03.cpp','animation_machine_objects_u05.cpp','animation_machine_objects_u04.cpp','animation_machine_objects_u06.cpp','animation_machine_objects_u07.cpp','animation_machine_objects_u08.cpp','animation_machine_objects_u09.cpp','animation_machine_objects_u08b.cpp','animation_machine_objects_u10.cpp','animation_machine_objects_u11.cpp','animation_machine_objects_u12.cpp','animation_machine_objects_u13.cpp','animation_machine_objects_u14.cpp','animation_machine_objects_u15.cpp','animation_machine_objects_u16.cpp','animation_machine_objects_u15b.cpp','animation_machine_objects_u15c.cpp','animation_machine_objects_u17.cpp','animation_machine_objects_u18.cpp','animation_machine_objects_u19.cpp','animation_machine_objects_u20.cpp','animation_machine_objects_u20b.cpp','animation_machine_frame_head_h8.cpp','animation_machine_objects_n34.cpp','animation_machine_objects_b1c.cpp','animation_machine_frame_head_h2.cpp','animation_machine_objects_n35.cpp','animation_machine_frame_head_h4.cpp','animation_machine_frame_head_h3.cpp','animation_machine_objects_n33.cpp','animation_machine_frame_head_h1.cpp','animation_machine_objects_n32b.cpp','animation_machine_objects_n32.cpp','animation_machine_objects_n31.cpp','animation_machine_objects_n27.cpp','animation_machine_objects_n30.cpp','animation_machine_objects_n25.cpp','animation_machine_objects_n26.cpp','animation_machine_objects_n29.cpp','animation_machine_objects_n24.cpp','animation_machine_objects_n20.cpp','animation_machine_objects_n21.cpp','animation_machine_objects_n22.cpp','animation_machine_objects_n23.cpp','animation_machine_objects_n28.cpp','animation_machine_objects_n18.cpp','animation_machine_objects_n19.cpp','animation_machine_objects_n17.cpp','animation_machine_objects_n16.cpp','animation_machine_objects_n15.cpp','animation_machine_objects_n14.cpp','animation_machine_objects_n13.cpp','animation_machine_objects_n12.cpp','animation_machine_objects_n11.cpp','animation_machine_objects_n09.cpp','animation_machine_objects_n10.cpp','animation_machine_objects_n08.cpp','animation_machine_objects_n07.cpp','animation_machine_objects_n06.cpp','animation_machine_objects_n05.cpp','animation_machine_objects_n04.cpp','animation_machine_objects_n03.cpp','animation_machine_objects_n01.cpp','palette_effect_execution.cpp','program_bus.cpp','program_stack.cpp','animation_machine_frame.cpp','animation_machine_irq_f6a.cpp','animation_machine_objects_b2b.cpp','animation_machine_controller_c3.cpp','animation_machine_objects_b1b.cpp','animation_machine_irq_f6b.cpp','animation_machine_controller_c1.cpp','animation_machine_objects_b2a.cpp','animation_machine_irq_f6c.cpp','animation_machine_objects_b1a.cpp','physical_rom_resource.cpp')
HARNESS = r'''#include "ms5/animation_machine.h"
#include "ms5/physical_rom_resource.h"
#include <fstream>
#include <iterator>
#include <iostream>
#include <cstdlib>
static std::vector<std::uint8_t> load(const char* p) {
    std::ifstream f(p,std::ios::binary);return std::vector<std::uint8_t>((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
}
static bool save(const char* p,const std::vector<std::uint8_t>& b) {
    std::ofstream f(p,std::ios::binary);if(!b.empty())f.write(reinterpret_cast<const char*>(&b[0]),b.size());f.close();return !f.fail();
}
static void u32(std::ofstream& f,std::uint32_t n){for(int i=3;i>=0;--i)f.put(static_cast<char>((n>>(i*8))&255));}
int main(int argc,char** argv) {
    if(argc<27)return 2;
    ms5::AnimationMachineState s;for(unsigned i=0;i<8;++i)s.d[i]=std::strtoul(argv[1+i],NULL,0);
    for(unsigned i=0;i<8;++i)s.a[i]=std::strtoul(argv[9+i],NULL,0);s.pc=std::strtoul(argv[17],NULL,0);
    s.carry=static_cast<ms5::AnimationCarryState>(std::strtoul(argv[18],NULL,0));
    ms5::AnimationMachineDevice device;device.bank_base=std::strtoul(argv[19],NULL,0);
    const std::uint32_t stop=std::strtoul(argv[20],NULL,0);const std::uint8_t external=std::strtoul(argv[21],NULL,0);
    std::vector<std::uint8_t> ram=load(argv[22]);device.pvc=load(argv[23]);
    std::vector<ms5::PhysicalRomResource> physical;std::string error;
    for(int i=27;i<argc;++i){ms5::PhysicalRomResource r;if(!ms5::load_physical_rom_resource(argv[i],r,error)){std::cerr<<error;return 3;}physical.push_back(r);}
    std::vector<ms5::FixedDataResource> windows;ms5::ProgramBusState bus;bus.physical_rom=&physical;
    // Explicit cart vector view, owned for this invocation. No sentinel synthesis.
    std::vector<std::uint8_t> vectors;
    for(std::size_t i=0;i<physical.size();++i)if(physical[i].source_rom_offset==0&&physical[i].data.size()>=128) vectors.assign(physical[i].data.begin(),physical[i].data.begin()+128);
    if(!vectors.empty())bus.vectors=&vectors;
    ms5::VideoPortWrite marker;marker.size=1;marker.address=0xdeadbeef;marker.value=0x87;
    std::vector<ms5::VideoPortWrite> ports(1,marker);std::uint32_t reads=0x12345678;
    ms5::AnimationMachineStatus status=ms5::AnimationMachineWaiting;
    bool ok=ms5::run_animation_machine(ram,windows,bus,s,device,stop,external,reads,status,ports,error);
    if(!save(argv[24],ram)||!save(argv[25],device.pvc))return 4;
    std::ofstream portfile(argv[26],std::ios::binary);
    for(std::size_t i=0;i<ports.size();++i){portfile.put(static_cast<char>(ports[i].size));u32(portfile,ports[i].address);u32(portfile,ports[i].value);}portfile.close();if(portfile.fail())return 4;
    if(!ok)std::cerr<<error;
    std::cout<<"{";
    for(unsigned i=0;i<8;++i)std::cout<<(i?",":"")<<"\"d"<<i<<"\":"<<s.d[i];
    for(unsigned i=0;i<8;++i)std::cout<<",\"a"<<i<<"\":"<<s.a[i];
    std::cout<<",\"pc\":"<<s.pc<<",\"carry\":"<<static_cast<unsigned>(s.carry)<<",\"bank_base\":"<<device.bank_base<<",\"external_reads\":"<<reads
        <<",\"status\":"<<static_cast<unsigned>(status)<<",\"ok\":"<<(ok?"true":"false")<<"}\n";
}
'''


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def trace_of(n):return {k:n[k] for k in ('pcs','events','boundaries','guard','invalid','interrupts','error')}


def audit_native(root,program,source):
    folder=root/'artifacts/animation_shared_stack_native';p=folder/'observation.json'
    assert digest(p)==NATIVE_SHA
    report=json.loads(p.read_text());assert report['source']==source and report['failure'] is None
    assert report['cases']==8 and not report['scratch_stack'] and not report['SR_read_at_any_phase']
    refs={str(p.relative_to(root)):NATIVE_SHA}
    for name,h in report['inputs'].items():assert digest(root/name)==h,name;refs[name]=h
    for name,h in report['artifacts'].items():
        path=folder/name;assert digest(path)==h,name;refs[str(path.relative_to(root))]=h
    oracle=report['oracle'];assert native.unicorn.__version__==oracle['version']
    for path,h in ((oracle['library'],oracle['library_sha256']),
                   (inspect.getfile(native.unicorn.Uc),oracle['wrapper_sha256'])):
        assert digest(path)==h;refs[str(Path(path).resolve())]=h
    static=json.loads((folder/'source.json').read_text())
    for row in static['instructions']:
        assert bytes.fromhex(row['raw'])==program[row['rom_offset']:row['rom_offset']+row['size']]
    fresh=[]
    for i,case in enumerate(native.cases()):
        fx,n,e=native.run_case(program,case);row=report['rows'][i]
        assert (row['incoming'],row['outgoing'],row['evidence'])==(n['incoming'],n['outgoing'],e)
        assert row['case']==case and row['fixture']==fx['details']
        stem='case_%04d'%i
        payloads={stem+'_ram_before.bin':fx['ram'],stem+'_ram_after.bin':n['ram_after'],
            stem+'_pvc_before.bin':fx['pvc'],stem+'_pvc_after.bin':n['pvc_after'],
            stem+'_ports.bin':b''.join(struct.pack('>BII',p['size'],p['address'],p['value']) for p in e['ports']),
            stem+'_trace.json':(json.dumps(trace_of(n),indent=2)+'\n').encode()}
        for name,data in payloads.items():assert (folder/name).read_bytes()==data
        fresh.append((fx,n))
    fx,phases,e=native.run_wait_chain(program);g=report['shared_stack_wait_group'];assert e==g['evidence']
    for label,n,row in zip(('begin-highwait','release-mutated-stack'),phases,g['rows']):
        assert row['incoming']==n['incoming'] and row['outgoing']==n['outgoing']
        stem='wait_'+label;assert (folder/(stem+'_trace.json')).read_bytes()==(json.dumps(trace_of(n),indent=2)+'\n').encode()
        for suffix,key in (('_ram_before.bin','ram_before'),('_ram_after.bin','ram_after'),('_pvc_before.bin','pvc_before'),('_pvc_after.bin','pvc_after')):
            assert (folder/(stem+suffix)).read_bytes()==n[key]
    return fresh,(fx,phases,e),refs


def resource_audit(root,program):
    files,m=physical.build(root);folder=root/'extracted/runtime/program_rom';paths=[];refs={}
    for name,data in files.items():
        p=folder/name;assert p.read_bytes()==data;refs[str(p.relative_to(root))]=digest(p)
        if name.endswith('.ms5d'):assert physical.validate_container(data)==program[struct.unpack_from('<I',data,16)[0]:struct.unpack_from('<I',data,16)[0]+len(data)-32];paths.append(p)
    assert len(paths)==8
    return sorted(paths),refs


def audit_extended(root,program,source):
    folder=root/'artifacts/animation_machine_extended_native';path=folder/'observation.json'
    assert EXTENDED_SHA and digest(path)==EXTENDED_SHA
    report=json.loads(path.read_text())
    assert report['source']==source and report['failure'] is None
    assert report['shared_stack'] and not report['stack_difference_mask']
    assert not report['original_program_modified'] and not report['SR_read_at_any_phase']
    assert not report['register_injection_after_begin'] and not report['Cpp_comparison_performed']
    refs={str(path.relative_to(root)):EXTENDED_SHA}
    for name,h in report['inputs'].items():assert digest(root/name)==h,name;refs[name]=h
    for name,h in report['artifacts'].items():
        p=folder/name;assert digest(p)==h,name;refs[str(p.relative_to(root))]=h
    assert extended.unicorn.__version__==report['oracle']['version']
    assert digest(report['oracle']['library'])==report['oracle']['library_sha256']
    static=json.loads((folder/'source.json').read_text())
    for instruction in static['instructions']:
        offset=instruction['rom_offset'];size=instruction['size']
        assert bytes.fromhex(instruction['raw'])==program[offset:offset+size]
    selections=extended.matrix(program)
    assert len(selections)==report['cases']==len(report['results'])
    records=[];phase_count=0
    for i,selection in enumerate(selections):
        normalized,fx,phases=extended.run_case(program,selection);row=report['results'][i]
        assert row['index']==i and row['selection']==normalized and row['reproduced_twice']
        assert row['fixture']=={k:v for k,v in fx.items() if k not in ('ram','pvc','regs')}
        assert len(phases)==len(row['phases'])
        for j,(phase,saved) in enumerate(zip(phases,row['phases'])):
            for key in ('label','incoming','outgoing','waiting','host_changes','modeled_bank'):
                assert phase[key]==saved[key],(i,j,key)
            assert saved['external_reads']==sum(e['region']=='external' for e in phase['events'])
            stem='case_%03d_phase_%02d'%(i,j)
            ports=[e for e in phase['events'] if e['region']=='pvc']
            payloads={stem+'_ram_before.bin':phase['ram_before'],stem+'_ram_after.bin':phase['ram_after'],
                stem+'_pvc_before.bin':phase['pvc_before'],stem+'_pvc_after.bin':phase['pvc_after'],
                stem+'_ports.bin':b''.join(struct.pack('>BII',e['size'],e['address'],int(e['bytes'],16)) for e in ports),
                stem+'_trace.json':(json.dumps({k:phase[k] for k in ('pcs','events','boundaries')},indent=2)+'\n').encode()}
            assert set(saved['artifacts'])==set(payloads)
            for name,data in payloads.items():
                assert (folder/name).read_bytes()==data and hashlib.sha256(data).hexdigest()==saved['artifacts'][name]
        records.append((normalized,fx,phases));phase_count+=len(phases)
    assert phase_count==report['phases'] and report['fresh_CPU_runs']==2*len(records)
    assert report['phase_executions']==2*phase_count
    return records,refs


def fold_device(pvc,bank,events):
    candidate=bytearray(pvc);ports=[]
    for e in events:
        if e['access']!='write' or not 0x2fe000<=e['address']<0x300000:continue
        assert e['address'] in (0x2ffff0,0x2ffff2) and e['size']==2
        raw=bytes.fromhex(e['bytes']);at=e['address']-0x2fe000;candidate[at:at+2]=raw
        bank,ff8,ff9=pvc_bank_update(int.from_bytes(candidate[0x1ff0:0x1ff2],'big'),int.from_bytes(candidate[0x1ff2:0x1ff4],'big'))
        candidate[0x1ff0:0x1ff2]=ff8.to_bytes(2,'big');candidate[0x1ff2:0x1ff4]=ff9.to_bytes(2,'big')
        ports.append((e['size'],e['address'],int.from_bytes(raw,'big')))
    return bytes(candidate),bank,b''.join(struct.pack('>BII',*p) for p in ports)


def parse(text,expected_invalid_carry=None):
    def unique(pairs):
        result={}
        for k,v in pairs:assert k not in result;result[k]=v
        return result
    row=json.loads(text,object_pairs_hook=unique);assert type(row) is dict and set(row)==KEYS
    assert type(row['ok']) is bool
    assert all(type(row[k]) is int and 0<=row[k]<=0xffffffff for k in KEYS-{'ok'})
    assert row['status'] in (0,1)
    assert row['carry'] in (0,1,2) or (row['ok'] is False and expected_invalid_carry is not None and row['carry']==expected_invalid_carry)
    return row


def invoke(exe,folder,label,ram,state,pvc,bank,resources,stop=native.RETURN,external=0):
    paths=[folder/(label+s) for s in ('_input.bin','_pvc_input.bin','_ram.bin','_pvc.bin','_ports.bin')]
    paths[0].write_bytes(ram);paths[1].write_bytes(pvc)
    args=[str(exe)]+[str(state[k]) for k in REGS]+[str(state['pc']),str(state['carry']),str(bank),str(stop),str(external)]+list(map(str,paths))+list(map(str,resources))
    run=subprocess.run(args,capture_output=True,text=True,timeout=10);assert run.returncode==0,(label,run.stderr)
    result=parse(run.stdout,expected_invalid_carry=state['carry'] if state['carry'] not in (0,1,2) else None)
    assert paths[0].read_bytes()==ram and paths[1].read_bytes()==pvc
    (folder/(label+'_state.json')).write_text(run.stdout)
    return result,paths[2].read_bytes(),paths[3].read_bytes(),paths[4].read_bytes(),run.stderr


def check_result(actual,n,pvc,bank,portbytes):
    result,ram,device,ports,error=actual
    assert result['ok'] and not error
    assert {k:result[k] for k in REGS+('pc',)}==n['outgoing'],{
        k:(n['outgoing'][k],result[k]) for k in REGS+('pc',) if result[k]!=n['outgoing'][k]}
    assert result['status']==(1 if n['outgoing']['pc'] in (native.WAIT,0xcda4) else 0)
    if result['status']==1:assert result['carry']==0 # API wait contract; old native does not observe C
    reads=sum(e['access']=='read' and e['address']==0xd00046 and e['size']==1 for e in n['events'])
    assert result['external_reads']==reads and result['bank_base']==bank,(reads,result['external_reads'],bank,result['bank_base'])
    assert ram==n['ram_after'],[(i,n['ram_after'][i],ram[i]) for i in range(min(len(ram),len(n['ram_after']))) if ram[i]!=n['ram_after'][i]][:20]
    assert device==pvc,'PVC mismatch'
    assert ports==portbytes,('ports',ports.hex(),portbytes.hex())


def dependencies(root):
    names={'tools/verify_animation_machine.py','tools/observe_animation_shared_stack.py','tools/pack_physical_program.py',
        'tools/address_map.py','tools/disassemble_program.py','tools/observe_animation_banked_handler.py',
        'engine/tests/animation_machine_test.cpp','tools/observe_animation_machine_extended.py'}
    pending=[root/'engine/src'/n for n in SOURCES]
    while pending:
        path=pending.pop();name=str(path.relative_to(root))
        if name in names:continue
        names.add(name)
        for inc in re.findall(r'#include "([^\"]+)"',path.read_text()):
            dep=root/'engine/include'/inc if inc.startswith('ms5/') else path.parent/inc
            if dep.is_file():pending.append(dep)
    return names


def negatives(exe,folder,fx,resources):
    state=dict(fx['regs'],a7=native.S,pc=native.ENTRY,carry=2);rows=[]
    def reject(label,ram=None,s=None,pvc=None,paths=None,stop=native.RETURN,expected_error=None):
        incoming=fx['ram'] if ram is None else bytes(ram);dev=fx['pvc'] if pvc is None else pvc;registers=state if s is None else s
        a=invoke(exe,folder,'negative_'+label,incoming,registers,dev,fx['bank_base'],resources if paths is None else paths,stop=stop,external=255)
        r,out,device,ports,error=a
        assert not r['ok'] and error.strip()
        if expected_error is not None:assert expected_error in error,(label,error)
        assert {k:r[k] for k in STATE_KEYS}==registers and r['bank_base']==fx['bank_base']
        assert r['status']==1 and r['external_reads']==0x12345678
        assert out==incoming and device==dev and ports==struct.pack('>BII',1,0xdeadbeef,0x87)
        rows.append(dict(label=label,error=error,all_outputs_preserved=True))
    reject('unsupported-PC',s=dict(state,pc=0xdeac),expected_error='unsupported animation frame head h8 PC')
    ram=bytearray(fx['ram']);native.put(ram,native.S,4,0xdeac);reject('unsupported-live-return',ram=ram,expected_error='unsupported animation frame head h8 PC')
    reject('missing-physical',paths=[])
    reject('odd-stack',s=dict(state,a7=native.S-1))
    reject('odd-stop',stop=native.RETURN+1)
    reject('short-RAM',ram=fx['ram'][:-1]);reject('short-PVC',pvc=fx['pvc'][:-1])
    ram=bytearray(fx['ram']);ram[native.SCRIPT&65535:(native.SCRIPT&65535)+6]=bytes.fromhex('080000300000');reject('late-unsupported-fetch',ram=ram)
    reject('late-publication-LONG',s=dict(state,pc=0x4a276,a0=0x1ffffe),expected_error='unsupported animation machine write device')
    return rows


def compare_extended(exe,folder,records,resources):
    rows=[];resumes=0;external_reads=0;port_count=0
    for i,(selection,fx,phases) in enumerate(records):
        ram=fx['ram'];pvc=fx['pvc'];bank=fx['bank_base']
        state=dict(fx['regs'],a7=fx['initial_a7'],pc=fx['entry_pc'],carry=0)
        expected_pvc=pvc;expected_bank=bank;results=[]
        for j,n in enumerate(phases):
            # A resumed invocation starts from actual preceding machine outputs.
            # Only recorded host writes are applied; native state is an assertion.
            if j:
                changed=bytearray(ram)
                for change in n['host_changes']:
                    at=change['address']&65535;size=change['size']
                    assert 0<=at<=65536-size
                    if 'before' in change:assert changed[at:at+size].hex()==change['before']
                    native.put(changed,change['address'],size,change['value'])
                ram=bytes(changed);resumes+=1
            else:assert not n['host_changes']
            assert {k:state[k] for k in REGS+('pc',)}==n['incoming'] and ram==n['ram_before'],(i,j,'incoming')
            expected_pvc,expected_bank,ports=fold_device(expected_pvc,expected_bank,n['events'])
            assert expected_bank==n['modeled_bank']
            actual=invoke(exe,folder,'extended_%03d_%02d'%(i,j),ram,state,pvc,bank,resources,
                          stop=fx['stop_pc'],external=fx['external'])
            check_result(actual,n,expected_pvc,expected_bank,ports)
            result,ram,pvc,_,_=actual;bank=result['bank_base'];state={k:result[k] for k in STATE_KEYS}
            external_reads+=result['external_reads'];port_count+=len(ports)//9
            results.append(dict(phase=j,label=n['label'],actual_previous_outputs_used=bool(j),
                status=result['status'],carry=result['carry'],external_reads=result['external_reads'],ports=len(ports)//9,
                full_RAM_state_PVC_ports_equal=True))
        rows.append(dict(index=i,selection=selection,phases=results))
    return dict(cases=len(records),phases=sum(len(r['phases']) for r in rows),
        previous_actual_CPP_resumes=resumes,external_reads=external_reads,ports=port_count,matches=rows)


def main():
    root=Path(__file__).resolve().parents[1];folder=root/'artifacts/animation_machine_execution';folder.mkdir(parents=True,exist_ok=True)
    report_path=folder/'verification.json';report_path.unlink(missing_ok=True)
    names=dependencies(root);inputs={name:digest(root/name) for name in sorted(names)}
    for tool in (Path(sys.executable).resolve(),Path(shutil.which('clang++')).resolve()):inputs[str(tool)]=digest(tool)
    program,source=native.load_verified_program(root);rom=root/source['path'];rom_before=(digest(rom),rom.stat().st_mtime_ns)
    resources,refs=resource_audit(root,program);fresh,chain,native_refs=audit_native(root,program,source);refs.update(native_refs)
    extended_records,extended_refs=audit_extended(root,program,source);refs.update(extended_refs)
    harness=folder/'harness.cpp';harness.write_text(HARNESS);exe=folder/'animation_machine_harness'
    command=['clang++','-std=c++11','-O2','-Wall','-Wextra','-pedantic','-I'+str(root/'engine/include')]+[str(root/'engine/src'/n) for n in SOURCES]+[str(harness),'-o',str(exe)]
    build=subprocess.run(command,capture_output=True,text=True,timeout=300);(folder/'compile.log').write_text(build.stdout+build.stderr)
    assert build.returncode==0 and not build.stdout and not build.stderr,(build.returncode,build.stderr)
    matches=[]
    for i,(fx,n) in enumerate(fresh):
        expected_pvc,bank,ports=fold_device(fx['pvc'],fx['bank_base'],n['events'])
        state=dict(fx['regs'],a7=native.S,pc=native.ENTRY,carry=0)
        actual=invoke(exe,folder,'case_%04d'%i,fx['ram'],state,fx['pvc'],fx['bank_base'],resources)
        check_result(actual,n,expected_pvc,bank,ports)
        matches.append(dict(case_index=i,registers16_PC_equal=True,full_RAM_equal=True,PVC_fold_equal=True,ports_equal=True))
    fx,phases,evidence=chain;ram=fx['ram'];pvc=fx['pvc'];bank=fx['bank_base'];state=dict(fx['regs'],a7=native.S,pc=native.ENTRY,carry=0)
    expected_pvc=pvc;expected_bank=bank;chain_rows=[]
    for i,n in enumerate(phases):
        if i:
            # Only previous actual C++ outputs plus recorded external RAM writes.
            changed=bytearray(ram)
            for change in evidence['host_changes']:
                at=change['address']&65535;assert bytes(changed[at:at+change['size']]).hex()==change['before']
                native.put(changed,change['address'],change['size'],change['value'])
            ram=bytes(changed)
        expected_pvc,expected_bank,ports=fold_device(expected_pvc,expected_bank,n['events'])
        actual=invoke(exe,folder,'wait_%d'%i,ram,state,pvc,bank,resources)
        check_result(actual,n,expected_pvc,expected_bank,ports)
        result,ram,pvc,_,_=actual;bank=result['bank_base'];state={k:result[k] for k in STATE_KEYS}
        chain_rows.append(dict(phase=i,actual_previous_outputs_used=bool(i),status=result['status'],carry=result['carry'],full_RAM_state_PVC_ports_equal=True))
    extended_matches=compare_extended(exe,folder,extended_records,resources)
    negative_rows=negatives(exe,folder,fresh[0][0],resources)
    assert all(digest(root/name)==h for name,h in inputs.items())
    assert all(digest(Path(name) if name.startswith('/') else root/name)==h for name,h in refs.items())
    assert (digest(rom),rom.stat().st_mtime_ns)==rom_before
    artifacts={str(p.relative_to(root)):digest(p) for p in folder.iterdir() if p.is_file() and p!=report_path}
    refs.update(artifacts)
    report=dict(schema_version=1,harness_JSON_keys=22,carry_native_observed=False,source=source,inputs=inputs,artifacts=refs,native_observation_sha256=NATIVE_SHA,
        native_replayed_nonwait=8,native_replayed_chain_phases=2,actual_CPP_nonwait_matches=8,actual_CPP_chain_phases=2,
        previous_actual_CPP_resumes=1,matches=matches,chain=chain_rows,
        extended_native_observation_sha256=EXTENDED_SHA,extended=extended_matches,
        negatives=negative_rows,negative_count=len(negative_rows),
        compile_command=command,failure=None,ROM_unchanged=True,
        limits=['Unpatched whole49fc6 original8controlled prefix/40 cases and1highwait/live-stack-mutation chain form a separate preserved base group.',
            'Additional controlled shared-stack draws, callbacks, fields and sound chains use imported fixtures; not natural reachability or exhaustive all-path support.',
            'Full16registers/PC/RAM/orderedports compared. Carry enum is forwarded on actual C++ resumes and waitUnknown is API-checked; immutable legacy native evidence does not observe C. No generalCCR/timing/physicalhardware claim.',
            'Original rawPVC fixture lacks read-side effects and has noPVCreads; expected C++ PVC independently folds actual native writes through pinned pvc_bank_update includingff8/ff9 masks.',
            'Generated harness is API test plumbing, not a production CLI/file-protection implementation. Checked API failures test complete output atomicity, not native fault rollback.'])
    report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(matches=8,chain_phases=2,
        extended_cases=extended_matches['cases'],extended_phases=extended_matches['phases'],
        negative_count=len(negative_rows),sha256=digest(report_path))))


if __name__=='__main__':main()

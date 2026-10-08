"""Consume complete kind3 program storage through C++ bus and original handler.

The exhaustive byte traversal proves storage/bus coverage, not natural script use.
"""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

import observe_animation_high_address as high
import pack_physical_program as physical
import verify_animation_banked_lookup as previous

HIGH_SOURCE_SHA = '7fe7e967fb8893ffcd1b3d7c2b388ffa70a37dc4d4b3451f6121407fd22b281e'
HIGH_REPORT_SHA = '0350a9da19b7b7e13b5ec82bb84dede2092b54d44b2aa6153d083e55df29bac9'
MANIFEST_SHA = '798d042a6c6bcf8f5f880608b1fdb5f02b7694d3dada9e0c7832d6b3b1824482'
HARNESS = r'''#include "ms5/program_bus.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace ms5;
static void require(bool b) { if (!b) throw std::runtime_error("harness assertion"); }
static void word(std::ofstream& f, std::uint32_t x) {
    for (int n=3;n>=0;--n) f.put(static_cast<char>((x>>(n*8))&255));
}
int main(int argc,char** argv) {
 try {
    require(argc==11);
    std::vector<PhysicalRomResource> resources(8);
    std::string error;
    for (unsigned n=0;n<8;++n) require(load_physical_rom_resource(argv[n+3],resources[n],error));
    std::vector<std::uint8_t> ram(65536,0x5a),vectors(resources[0].data.begin(),resources[0].data.begin()+128),pvc(8192,0xa5);
    std::vector<FixedDataResource> legacy;
    ProgramBusState bus;bus.physical_rom=&resources;bus.vectors=&vectors;bus.pvc=&pvc;
    std::ofstream full(argv[1],std::ios::binary),target(argv[2],std::ios::binary);
    require(full.good()&&target.good());
    std::uint32_t value=0;
    for(std::uint32_t p=0;p<0x800000;++p) {
        std::uint32_t cpu=p;
        if(p>=0x100000) {bus.bank_base=p;cpu=0x200000;}
        require(read_program_bus(ram,legacy,bus,cpu,1,value,error));full.put(static_cast<char>(value));
    }
    unsigned reads=0,failures=0;
    for(unsigned boundary=1;boundary<=8;++boundary) {
        std::uint32_t b=boundary*0x100000;
        for(unsigned size=1;size<=4;size*=2) {
            for(int delta=-4;delta<=1;++delta) {
                std::uint32_t p=b+delta;
                // First boundary is a device transition, not contiguous ROM mapping.
                if(p<0x100000 && (p+size>0x100000 || (size>1 && (p&1)))) continue;
                if(p<0x100000) bus.bank_base=0x200000;else bus.bank_base=p;
                std::uint32_t cpu=p<0x100000?p:0x200000;
                value=0xdeadbeef;
                bool ok=read_program_bus(ram,legacy,bus,cpu,size,value,error);
                if(p+size<=0x800000) { require(ok);word(target,p);word(target,size);word(target,value);++reads; }
                else {require(!ok&&value==0xdeadbeef);++failures;}
            }
        }
    }
    for(unsigned bank=1;bank<=7;++bank) for(unsigned byte=0;byte<16;++byte) {
        std::uint32_t p=(bank+1)*0x100000-16+byte;bus.bank_base=p;
        require(read_program_bus(ram,legacy,bus,0x200000,1,value,error));word(target,p);word(target,1);word(target,value);++reads;
    }
    // Explicit device views override physical storage; absent views cannot fall back.
    vectors.assign(128,0x3c);require(read_program_bus(ram,legacy,bus,0,1,value,error)&&value==0x3c);
    bus.vectors=NULL;value=0xdeadbeef;require(!read_program_bus(ram,legacy,bus,0,1,value,error)&&value==0xdeadbeef);++failures;bus.vectors=&vectors;
    require(read_program_bus(ram,legacy,bus,0x2fe000,1,value,error)&&value==0xa5);
    bus.pvc=NULL;value=0xdeadbeef;require(!read_program_bus(ram,legacy,bus,0x2fe000,1,value,error)&&value==0xdeadbeef);++failures;bus.pvc=&pvc;
    require(read_program_bus(ram,legacy,bus,0x100000,1,value,error)&&value==0x5a);
    // Adjacent physical chunks combine units; removing one side refuses whole unit.
    std::vector<PhysicalRomResource> fewer=resources;fewer.erase(fewer.begin()+2);bus.physical_rom=&fewer;bus.bank_base=0x1fffff;
    value=0xdeadbeef;require(!read_program_bus(ram,legacy,bus,0x200000,2,value,error)&&value==0xdeadbeef);++failures;
    std::vector<PhysicalRomResource> duplicate=resources;duplicate.push_back(resources[2]);bus.physical_rom=&duplicate;bus.bank_base=0x200000;
    value=0xdeadbeef;require(!read_program_bus(ram,legacy,bus,0x200000,2,value,error)&&value==0xdeadbeef);++failures;
    bus.physical_rom=&resources;
    FixedDataResource overlap;overlap.source_cpu_address=0x200000;overlap.source_rom_offset=0x200000;overlap.data.assign(2,0);
    legacy.push_back(overlap);value=0xdeadbeef;require(!read_program_bus(ram,legacy,bus,0x200000,2,value,error)&&value==0xdeadbeef);++failures;
    full.close();target.close();require(!full.fail()&&!target.fail());
    std::cout<<"{\"bus_byte_reads\":8388608,\"target_reads\":"<<reads<<",\"refusals\":"<<failures<<",\"device_override_checks\":3}\n";
 } catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
 return 0;
}
'''


def resource_audit(root, program):
    folder = root/'extracted/runtime/program_rom'
    mp = folder/'manifest.json'
    assert previous.digest(mp) == MANIFEST_SHA
    files, manifest = physical.build(root)
    assert manifest == json.loads(mp.read_text())
    paths = []
    hashes = {str(mp.relative_to(root)): MANIFEST_SHA}
    for name, data in files.items():
        path = folder/name
        assert path.read_bytes() == data
        hashes[str(path.relative_to(root))] = previous.digest(path)
        if name.endswith('.ms5d'):
            payload = physical.validate_container(data)
            offset = struct.unpack_from('<I', data, 16)[0]
            assert payload == program[offset:offset+len(payload)]
            paths.append(path)
    assert len(paths) == 8
    return sorted(paths), manifest, hashes


def harness(root, folder, resources, program):
    source = folder/'bus_coverage.cpp';source.write_text(HARNESS)
    binary = folder/'bus_coverage'
    command = ['c++', '-std=c++11', '-O2', '-Wall', '-Wextra', '-pedantic', '-I'+str(root/'engine/include'),
        str(source), str(root/'engine/src/program_bus.cpp'), str(root/'engine/src/physical_rom_resource.cpp'), '-o', str(binary)]
    run = subprocess.run(command, capture_output=True, text=True, timeout=60)
    (folder/'compile.log').write_text(run.stdout+run.stderr)
    assert run.returncode == 0 and not run.stderr, run.stderr
    output, targets = folder/'bus_all_bytes.bin', folder/'bus_target_reads.bin'
    run = subprocess.run([str(binary), str(output), str(targets)]+list(map(str, resources)), capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    counts = json.loads(run.stdout)
    assert output.read_bytes() == program and counts['bus_byte_reads'] == len(program) == 0x800000
    raw = targets.read_bytes();assert len(raw)%12 == 0
    records = []
    for p, size, value in struct.iter_unpack('>III', raw):
        assert value == int.from_bytes(program[p:p+size], 'big'), (p, size, value)
        records.append(dict(physical_offset=p, size=size, value=value))
    assert len(records) == counts['target_reads']
    (folder/'bus_coverage.json').write_text(json.dumps(dict(counts=counts, targets=records, compile_command=command), indent=2)+'\n')
    return counts


def negatives(root, exe, folder, fx, vectors, resources):
    rows = []
    with tempfile.TemporaryDirectory(dir=folder) as tmp:
        work = Path(tmp);inp=work/'input';out=work/'output';vp=work/'vectors';pvc=work/'pvc'
        inp.write_bytes(fx['ram']);vp.write_bytes(vectors);pvc.write_bytes(fx['pvc'])
        def reject(label, windows, output=None, numeric=None):
            dest = output or out
            if output is None:dest.write_bytes(b'preserve output')
            protected = {p:p.read_bytes() for p in set([inp,vp,pvc,dest]+windows)}
            result=previous.invoke(exe,fx,inp,dest,vp,pvc,windows,numeric)
            assert result.returncode and not result.stdout and result.stderr.strip(), (label,result.stdout,result.stderr)
            assert all(p.read_bytes()==data for p,data in protected.items()),label
            rows.append(dict(label=label,error=result.stderr.strip(),files_preserved=True))
        reject('missing-fixed-chunk',resources[1:])
        missing_bank=[p for p in resources if '200000' not in p.name]
        reject('missing-reached-bank-chunk',missing_bank)
        reject('missing-cross-chunk-first-LONG',missing_bank,numeric={0:0x1ffffb})
        partial_before=work/'partial_before.ms5d';partial_after=work/'partial_after.ms5d'
        payload=physical.validate_container(resources[0].read_bytes())
        partial_before.write_bytes(physical.wrap(payload[:0x4a76d],0))
        partial_after.write_bytes(physical.wrap(payload[0x4a76e:],0x4a76e))
        reject('missing-second-byte-of-reached-WORD',[partial_before,partial_after]+resources[1:])
        duplicate=work/'duplicate.ms5d';duplicate.write_bytes(resources[2].read_bytes())
        reject('duplicate-kind3-physical-coverage',resources+[duplicate])
        legacy=root/'extracted/runtime/animation_banked_reads'
        # Use an actual legacy fixed table resource, rather than synthetic success bytes.
        fixed=[]
        for path in legacy.glob('*.ms5d'):
            data=path.read_bytes();fields=struct.unpack_from('<4s7I',data)
            if fields[2]==1 and fields[4]<=0x4a76c<fields[4]+fields[5]:fixed.append(path)
        assert len(fixed)==1
        reject('mixed-legacy-kind3-physical-overlap',resources+fixed)
        bad=work/'bad.ms5d';raw=resources[0].read_bytes()
        for label, data in [('CRC',raw[:-1]+bytes([raw[-1]^1])),('truncated',raw[:-1])]:
            bad.write_bytes(data);reject(label,[bad]+resources[1:])
        data=bytearray(raw);struct.pack_into('<I',data,12,0);bad.write_bytes(data)
        reject('kind3-CPU-sentinel',[bad]+resources[1:])
        reject('resource-output-alias-copy',resources+[duplicate],duplicate)
        reject('input-output-alias',resources,inp)
    return rows


def high_address_group(root, folder, program, source, exe, resources, vp):
    """Separate declared24-bit adapter evidence; preserve old95 guard accounting."""
    native_folder=root/'artifacts/animation_high_address_native'
    report_path=native_folder/'observation.json'
    assert previous.digest(report_path)==HIGH_REPORT_SHA
    assert previous.digest(root/'tools/observe_animation_high_address.py')==HIGH_SOURCE_SHA
    report=json.loads(report_path.read_text())
    assert report['source']==source and report['failure'] is None
    assert (report['cases'],report['completed'],report['guarded'])==(3,2,1)
    assert report['reproduced_twice'] and not report['original_program_modified']
    assert not report['register_injection_after_begin'] and not report['in_hook_SR_access']
    hashes={str(report_path.relative_to(root)):HIGH_REPORT_SHA}
    for name,value in report['inputs'].items():
        assert previous.digest(root/name)==value,name
        hashes[name]=value
    for name,value in report['artifacts'].items():
        path=native_folder/name
        assert previous.digest(path)==value,name
        hashes[str(path.relative_to(root))]=value
    oracle=report['oracle']
    assert high.unicorn.__version__==oracle['version']
    assert previous.digest(oracle['library'])==oracle['library_sha256']
    matches=[];guards=[];replayed=[]
    for row in report['rows']:
        index=row['case_index'];case=previous.original.cases()[index]
        assert case==row['case'] and case['label'] in high.LABELS
        fx,native,details=high.run_case(program,case,index)
        assert native['incoming']==row['incoming'] and native['outgoing']==row['outgoing']
        assert details==row['details'] and fx['details']==row['fixture_details']
        assert all(native[k]==v for k,v in row['checks'].items())
        assert all(native['outgoing'][k]==fx['regs'][k] for k in ('a5','a6'))
        trace={k:native[k] for k in ('pcs','reads','writes','effective_addresses','guard','invalid','interrupts','error')}
        stem='case_%04d'%index
        payloads={stem+'_ram_before.bin':fx['ram'],stem+'_ram_after.bin':native['ram_after'],
            stem+'_pvc_incoming.bin':fx['pvc'],stem+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
        assert set(payloads)==set(row['artifacts'])
        for name,data in payloads.items():
            assert (native_folder/name).read_bytes()==data
            assert previous.original.sha(data)==row['artifacts'][name]==report['artifacts'][name]
        inp=folder/('high_%04d_input.bin'%index);out=folder/('high_%04d_cpp.bin'%index);pvc=folder/('high_%04d_pvc.bin'%index)
        inp.write_bytes(fx['ram']);pvc.write_bytes(fx['pvc']);out.write_bytes(b'preserve high output')
        run=previous.invoke(exe,fx,inp,out,vp,pvc,resources)
        assert inp.read_bytes()==fx['ram'] and pvc.read_bytes()==fx['pvc']
        if details['outcome']=='complete_with_declared_cart_vector_alias':
            assert run.returncode==0,(index,run.stderr)
            result=previous.parse(run.stdout)
            assert result=={k:native['outgoing'][k] for k in previous.KEYS}
            assert out.read_bytes()==native['ram_after']
            (folder/('high_%04d_state.json'%index)).write_text(run.stdout)
            matches.append(dict(case_index=index,label=case['label'],registers13=result,full_RAM_equal=True,
                raw_A2_preserved=result['a2']==0x01000000))
        else:
            assert details['outcome']=='guard_unsupported_masked_device'
            assert run.returncode and not run.stdout and run.stderr.strip(),(index,run.stderr)
            assert out.read_bytes()==b'preserve high output'
            guards.append(dict(case_index=index,label=case['label'],error=run.stderr.strip(),output_preserved=True,
                logical=details['second_read_logical'],bus=details['second_read_bus']))
        replayed.append(index)
    assert (len(matches),len(guards),len(replayed))==(2,1,3)
    return dict(native_observation_sha256=HIGH_REPORT_SHA,observer_sha256=HIGH_SOURCE_SHA,native_replayed=3,
        complete_CPP_matches=2,guard_CPP_errors=1,matches=matches,guards=guards,adapter=report['adapter'],
        limits='Separate original execution under explicitly declared host24-bit cart-vector alias. '
        'Not automatic Unicorn masking or physical hardware proof. Original95 report retains3 guarded/pending cases. '
        'No generic MMIO/BIOS-vector/full40/CCR claim.'),hashes


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'artifacts/physical_program_execution';folder.mkdir(parents=True,exist_ok=True)
    report_path=folder/'verification.json';report_path.unlink(missing_ok=True)
    exe=root/'build/execute_animation_banked_lookup'
    program,source=previous.original.load_verified_program(root)
    rom=root/source['path'];before=previous.digest(rom),rom.stat().st_mtime_ns
    resources,manifest,artifacts=resource_audit(root,program)
    native,fixtures,native_hashes=previous.native_audit(root,program,source);artifacts.update(native_hashes)
    names=previous.cpp_dependencies(root,{'engine/tools/execute_animation_banked_lookup.cpp','engine/src/animation_banked_lookup.cpp',
        'engine/src/program_bus.cpp','engine/src/physical_rom_resource.cpp','engine/src/fixed_data_resource.cpp'})
    names.update({'Makefile','docs/analysis/physical-program-resource-contract.md','tools/tests/test_physical_program.py'})
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.suffix=='.py' and root/'tools' in path.parents:names.add(str(path.relative_to(root)))
    inputs={name:previous.digest(root/name) for name in sorted(names)}
    for path in (root/'extracted/runtime/animation_banked_reads').glob('*.ms5d'):
        fields=struct.unpack_from('<4s7I',path.read_bytes())
        if fields[2]==1 and fields[4]<=0x4a76c<fields[4]+fields[5]:
            inputs[str(path.relative_to(root))]=previous.digest(path)
    static=root/'artifacts/animation_banked_handler_native/source.json'
    inputs[str(static.relative_to(root))]=previous.digest(static)
    inputs[str(exe)]=previous.digest(exe);inputs[source['path']]=before[0]
    assert exe.stat().st_mtime_ns>=max((root/n).stat().st_mtime_ns for n in names if n.endswith(('.cpp','.h'))),'Stale CLI'
    counts=harness(root,folder,resources,program)
    vp=folder/'vectors128.bin';vp.write_bytes(program[:128])
    matches=[];errors=[];pending=[]
    for index,(row,fx) in enumerate(zip(native['results'],fixtures)):
        outcome=row['outcome']
        if outcome=='unsupported_high_32bit_effective_address':
            pending.append(dict(case_index=index,label=row['label'],status='not-compared'));continue
        inp=folder/('case_%04d_input.bin'%index);out=folder/('case_%04d_cpp.bin'%index);pvc=folder/('case_%04d_pvc.bin'%index)
        inp.write_bytes(fx['ram']);pvc.write_bytes(fx['pvc']);out.write_bytes(b'preserve output')
        run=previous.invoke(exe,fx,inp,out,vp,pvc,resources)
        assert inp.read_bytes()==fx['ram'] and pvc.read_bytes()==fx['pvc']
        if outcome=='complete':
            assert run.returncode==0,(index,run.stderr)
            result=previous.parse(run.stdout);assert result=={k:row['outgoing']['registers15'][k] for k in previous.KEYS}
            assert out.read_bytes()==(root/'artifacts/animation_banked_handler_native'/('case_%04d_ram_after.bin'%index)).read_bytes()
            (folder/('case_%04d_state.json'%index)).write_text(run.stdout)
            matches.append(dict(case_index=index,label=row['label'],full_RAM_equal=True,registers13=result))
        else:
            assert run.returncode and not run.stdout and run.stderr.strip(),(index,outcome,run.stderr)
            assert out.read_bytes()==b'preserve output'
            errors.append(dict(case_index=index,label=row['label'],native_guard=outcome,error=run.stderr.strip(),output_preserved=True))
    assert (len(matches),len(errors),len(pending))==(73,19,3)
    extra=negatives(root,exe,folder,fixtures[0],program[:128],resources)
    high_group,high_hashes=high_address_group(root,folder,program,source,exe,resources,vp);artifacts.update(high_hashes)
    for path in folder.iterdir():
        if path.is_file() and path!=report_path and path.name!='run.log':artifacts[str(path.relative_to(root))]=previous.digest(path)
    for name,value in {**inputs,**artifacts}.items():
        assert previous.digest(Path(name) if name.startswith('/') else root/name)==value,name
    assert (previous.digest(rom),rom.stat().st_mtime_ns)==before
    report=dict(source=source,inputs=inputs,artifacts=artifacts,resource_manifest_sha256=MANIFEST_SHA,native_observation_sha256=previous.NATIVE_SHA,
        resources_loaded_together=8,resource_counts=manifest['counts'],bus_coverage=counts,native_replayed=95,original_complete_CPP_matches=73,
        original_guard_CPP_errors=19,high32_pending=pending,high_address_adapter=high_group,extra_negative_count=len(extra),extra_negatives=extra,matches=matches,guard_errors=errors,ROM_unchanged=True,
        limits='Exhaustive physical storage BYTE traversal is not natural script proof. Isolated original handler stops before4a276; no full40/CCR/carry/timing claim. '
        'Vectors use explicit canonical cartridge128-byte view; PVC is explicit8192-byte fixture, both override physical storage. High32 original guards are not compared with24-bit masking. '
        'First1MiB boundary is fixed-ROM/RAM transition: last fixedWORD and first bank reads are separate; later boundaries test odd physical starts across chunks. '
        'Tested validation/execution failures preserve files; OS ftruncate/write failure can mutate output and is not atomic.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(bus=counts,matches=73,guard_errors=19,pending=3,high_adapter_matches=2,high_adapter_guard=1,extra_negatives=len(extra),sha256=previous.digest(report_path))))


if __name__=='__main__':main()

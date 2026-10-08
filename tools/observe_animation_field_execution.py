"""Immutable whole49fc6 field opcodes on controlled liveRAM scripts; no C++ oracle."""
import collections
import hashlib
import itertools
import json
from pathlib import Path

import observe_animation_control_commands as native

EXTRA_RANGES=((0x4a27e,0x4a2da),(0x4a2f2,0x4a30c),(0x4a3de,0x4a408))
EXTRA_BOUNDARIES=(0x4a27e,0x4a28e,0x4a294,0x4a2a6,0x4a2ac,0x4a2be,0x4a2c4,0x4a2d4,
    0x4a2f2,0x4a2f8,0x4a300,0x4a304,0x4a3de,0x4a3f0,0x4a3f4,0x4a3f6,0x4a3fc,0x4a400,0x49ffe)
WORD_SELECTORS=(0,1,0x90,0x3fff,0x4000,0x7fff,0x8000,0xffff)
BYTE_SAMPLES=(0,1,0x1d,0x1e,0x1f,0x90,0x91,0x92,0x96,0x97,0xa7,0xac,0xff)
OPCODES=(0x18,0x1c,0x20,0x24,0x34,0x38,0x2c)

def find_word_selector(program,offset):
    at=next(at for at in range(0x4276c,0x5276c,2) if int.from_bytes(program[at:at+2],'big')==offset)
    selector=((at-0x4a76c)//2)&65535
    assert 0x4a76c+native.signed_word((selector*2)&65535)==at
    return selector

def cases(program):
    rows=[]
    def add(family,opcode,**values):
        row=dict(family=family,opcode=opcode,selector=0,value=0x80,field=0,length=8,relative=0,
            a6=0x108000,script=0x104000,timer=0,padding=0xff,alias='none')
        row.update(values);rows.append(row)
    for selector,value in itertools.product(WORD_SELECTORS,(0,0x7f,0x80,0xff)):
        add('18-WORD-selector-wrap-partial-D0-D1',0x18,selector=selector,value=value)
    for op in (0x1c,0x20):
        for selector in range(256):add('BYTE-selector-domain',op,selector=selector,value=0x8001 if op==0x1c else 0x81234567)
        for selector,value in itertools.product((0,1,0x90,0x96),(0,0x7fff,0xffff)):
            add('write-boundary-values',op,selector=selector,value=value if op==0x1c else value*0x10001)
    for selector in range(256):add('24-all-BYTE-selectors-zero-wrap',0x24,selector=selector,field=0)
    for selector,field in itertools.product(BYTE_SAMPLES,(1,0x7f,0x80,0xff)):
        add('24-BYTE-decrement-boundaries',0x24,selector=selector,field=field)
    for op,value in itertools.product((0x34,0x38),(0,0x7fff,0x8000,0xffff)):
        add('padding-skipped-register-preservation',op,value=value,padding=value&255)
    for length,field in itertools.product((0,1,2,7,8,39,40,0x7fff,0x8000,0xfff8,0xfff0,0xffff),(0,1,4,255)):
        add('2c-length-and-unsigned-compare',0x2c,selector=0x1e,length=length,field=field)
    for selector,field,length in itertools.product((0x92,0x96,0x97,0xa7,0xac),(0,4,255),(0,7,0xfff8)):
        add('2c-retained-high-BYTE-signed-selected-address',0x2c,selector=selector,field=field,length=length)
    for relative in (0,2,0x7fff,0x8000,0xfffe):
        add('2c-two-signed-additions',0x2c,selector=0x1e,length=8,field=0,relative=relative,
            script=0x10c000 if relative==0x8000 else 0x104000)
    for target in (0x26,0x2a,0x2c):
        add('18-live-object-alias',0x18,selector=find_word_selector(program,target),value=0x80,alias='object-'+hex(target))
    for op in (0x18,0x1c,0x20,0x24,0x34,0x38):
        width={0x18:4,0x1c:4,0x20:6,0x24:2,0x34:4,0x38:4}[op]
        offset=0x70 if op==0x34 else 0x20 if op==0x38 else 0x56
        add('live-next-opcode-write',op,selector=0,value=0x28 if op==0x18 else 0x28000000 if op==0x20 else 0x2800,
            field=0x29,a6=0x104000+width-offset,alias='next-opcode')
    return rows

def fixture(program,case,index):
    ram=bytearray(hashlib.shake_256(b'animation-field-'+str(index).encode()).digest(65536))
    regs={key:(0x89abcdef+i*0x1020304+index*0x101)&0xffffffff for i,key in enumerate(native.KEYS)}
    regs.update(a5=0x108000,a6=case['a6']);a6=case['a6'];script=case['script'];op=case['opcode']
    for address,size,value in ((a6+0x26,4,script),(a6+0x2a,2,case['timer']),(a6+0x2c,2,256),(a6+0x17,1,0),(0x100010,2,0xbeef)):
        native.put(ram,address,size,value)
    value=case['value'];selector=case['selector'];details={}
    if op==0x18:body=bytes((op,value))+selector.to_bytes(2,'big')
    elif op in (0x1c,0x20):body=bytes((op,selector))+value.to_bytes(2 if op==0x1c else 4,'big')
    elif op==0x24:body=bytes((op,selector))
    elif op in (0x34,0x38):body=bytes((op,case['padding']))+value.to_bytes(2,'big')
    else:body=bytes((op,selector))+case['length'].to_bytes(2,'big')
    native.put(ram,script,len(body),int.from_bytes(body,'big'))
    cursor=script+len(body)
    if op in (0x18,0x1c,0x20,0x24,0x2c):
        lookup=0x4a76c+native.signed_word((selector*2)&65535)
        offset=int.from_bytes(program[lookup:lookup+2],'big');target=a6+native.signed_word(offset)
        size=2 if op==0x1c else 4 if op==0x20 else 1
        details.update(table_address=lookup,raw_offset=offset,field_address=target,field_size=size)
        if not native.BASE<=target or target+size>native.BASE+65536:
            raise ValueError('actual reached field outside64KiBRAM')
        if size>1 and target&1:raise ValueError('actual reached WORD/LONG field is odd')
        if op in (0x24,0x2c):native.put(ram,target,1,case['field'])
    if op==0x2c:
        shaped=(((details['raw_offset']&0xff00)|ram[details['field_address']-native.BASE])*2)&65535
        choose=shaped<case['length'];selected=cursor+native.signed_word(shaped)
        end=cursor+native.signed_word(case['length'])
        if choose:
            if not native.BASE<=selected or selected+2>native.BASE+65536 or selected&1:
                raise ValueError('selected relative WORD outsideRAM or odd')
            end=cursor+native.signed_word(case['relative'])+native.signed_word(case['length'])
            if max(selected,script)<min(selected+2,script+len(body)):
                raise ValueError('controlled selected WORD overlaps header')
            native.put(ram,selected,2,case['relative'])
        if not native.BASE<=end or end+2>native.BASE+65536:raise ValueError('relative final cursor outside supportedRAM')
        if max(end,script)<min(end+2,script+len(body)) or choose and max(end,selected)<min(end+2,selected+2):
            raise ValueError('controlled terminal00 overlaps header or selected WORD')
        details.update(shaped_offset=shaped,unsigned_in_range=choose,selected_address=selected,final_cursor=end,
            requested_relative=case['relative'])
        native.put(ram,end,2,0)
        if ram[details['field_address']-native.BASE]!=case['field']:raise ValueError('controlled setup aliases live field')
    else:
        native.put(ram,cursor,2,0);details['final_cursor']=cursor
    if op==0x24 and case['alias']=='next-opcode':native.put(ram,details['field_address'],1,0x29)
    if bytes(ram[script-native.BASE:script-native.BASE+len(body)])!=body:raise ValueError('controlled field/setup overwrites header')
    return bytes(ram),regs,details

def validate(case,details,trace):
    op=case['opcode'];before=next(b for b in trace['boundaries'] if b['pc']==0x4a276)
    assert before['registers']['a1']==details['final_cursor']
    publication=next(w for w in trace['ordered_writes'] if w['pc']==0x4a278)
    assert publication['value']==details['final_cursor'] and publication['address']==case['a6']+0x26
    if op in (0x34,0x38):
        assert not any(e['address']<=case['script']+1<e['address']+e['size'] for e in trace['reads'])
    if op==0x2c:
        branch=next(b for b in trace['branches'] if b['pc']==0x4a3f8)
        assert branch['next_pc']==(0x4a3fc if details['unsigned_in_range'] else 0x4a400)
        selected=[r for r in trace['reads'] if r['pc']==0x4a3fc]
        assert bool(selected)==details['unsigned_in_range']
        if selected:assert (selected[0]['address'],selected[0]['value'])==(details['selected_address'],case['relative'])
        field=next(r for r in trace['reads'] if r['pc']==0x4a3f0)
        assert (field['address'],field['value'])==(details['field_address'],case['field'])
    if case['alias']=='next-opcode':
        fetch=next(r for r in trace['reads'] if r['pc']==0x4a000 and r['address']==details['final_cursor'])
        assert fetch['value']==0x28


def main():
    root=Path(__file__).resolve().parents[1];program,source=native.load_verified_program(root);assert native.sha(program)==native.SOURCE_SHA256
    folder=root/'artifacts/animation_field_native';folder.mkdir(parents=True,exist_ok=True);report_path=folder/'observation.json';report_path.unlink(missing_ok=True)
    saved_ranges,saved_boundaries=native.RANGES,native.BOUNDARIES
    oracle=native.oracle_provenance();results=[];excluded=[];outcomes=collections.defaultdict(collections.Counter)
    try:
        native.RANGES=saved_ranges+EXTRA_RANGES;native.BOUNDARIES=saved_boundaries+EXTRA_BOUNDARIES
        instructions=[]
        for a,b in native.RANGES:instructions.extend(native.disassemble_range(program,a,b-a,a))
        for r in instructions:assert bytes.fromhex(r['raw'])==program[r['rom_offset']:r['rom_offset']+r['size']]
        branches={r['cpu_address'] for r in instructions if r['mnemonic'].startswith('b') and not r['mnemonic'].startswith(('bra','bsr','btst','bclr'))}
        source_path=folder/'source.json';source_path.write_text(json.dumps(dict(source=source,ranges=native.RANGES,boundaries=native.BOUNDARIES,instructions=instructions,
            data_ranges=[dict(cpu_address=0x4276c,rom_offset=0x4276c,size=65536,sha256=native.sha(program[0x4276c:0x5276c]))]),indent=2)+'\n')
        names=('tools/observe_animation_field_execution.py','tools/observe_animation_control_commands.py','tools/disassemble_program.py','tools/verify_object_reset.py',
            'tools/observe_scene_frame_execution.py','tools/observe_screen_reset_full.py','tools/verify_stage_catalog.py','artifacts/animation_field_native/source.json')
        inputs={name:native.sha((root/name).read_bytes()) for name in names};observer=native.Observer(program,branches)
        for index,case in enumerate(cases(program)):
            try:ram,regs,details=fixture(program,case,index)
            except ValueError as error:
                excluded.append(dict(case_index=index,fixture=case,reason=str(error),native_executed=False,success=False));continue
            output,ports,info,trace=observer.run(ram,regs);validate(case,details,trace)
            for b in trace['branches']:outcomes[b['pc']][b['next_pc']]+=1
            prefix='case_%04d'%index;payloads={prefix+'_input.bin':ram,prefix+'_native.bin':output,prefix+'_ports.bin':ports,prefix+'_trace.json':(json.dumps(trace,indent=2)+'\n').encode()}
            for name,data in payloads.items():(folder/name).write_bytes(data)
            results.append(dict(case_index=index,fixture=case,details=details,incoming=regs,port_count=len(ports)//9,files={name:native.sha(data) for name,data in payloads.items()},
                input_ram_file=prefix+'_input.bin',ram_file=prefix+'_native.bin',ports_file=prefix+'_ports.bin',trace_file=prefix+'_trace.json',**info))
    finally:native.RANGES,native.BOUNDARIES=saved_ranges,saved_boundaries
    assert oracle==native.oracle_provenance() and native.sha((root/source['path']).read_bytes())==native.SOURCE_SHA256
    assert all(native.sha((root/name).read_bytes())==value for name,value in inputs.items())
    report=dict(source=source,oracle=oracle,inputs=inputs,cases=len(results),requested_cases=len(cases(program)),cases_by_opcode=dict(collections.Counter(hex(r['fixture']['opcode']) for r in results)),
        total_native_ports=sum(r['port_count'] for r in results),returned_carry_counts=dict(collections.Counter(str(r['carry']) for r in results)),excluded_fixtures=excluded,
        observed_branch_successors={hex(a):{hex(b):n for b,n in sorted(c.items())} for a,c in sorted(outcomes.items())},
        original_program_modified=False,in_call_SR_read=False,Cpp_comparison_performed=False,failure=None,results=results,
        scope='Originalwhole49fc6 sevenfieldopcodes on syntheticliveRAM scripts andactualfixedrawlookup. BYTEselector domainrequested for1c/20/24; '
            'unaligned/outspan fielddestinations andcontrolled invalidterminal fixtures explicitlyexcluded withoutnativeexecution. '
            'Full64KiBRAM15R/RTScarry/orderedPVC/read-write-PC-stacktrace, noROMpatch/stubs/SRhooks/C++/pending/naturalgameplay/allfieldmeanings claim.')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cases=report['cases'],requested=report['requested_cases'],by_opcode=report['cases_by_opcode'],ports=report['total_native_ports'],excluded=len(excluded),sha256=native.sha(report_path.read_bytes()))))

if __name__=='__main__':main()

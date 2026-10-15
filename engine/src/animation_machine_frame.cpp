#include "animation_machine_frame_internal.h"
namespace ms5 {
namespace {
const std::uint32_t HEAD_LONG=0x100820, CONTROLLER_LONG=0x1008e4, SPD=0x1ff000, DISPATCH_PC=0x2ac2, MAX_WAITS=16,
    CARD_BIOS=0xc00468, CARD_RETURN=0xc37c, CARD_RETURN_C310=0xc316, CARD_ANSWER=0x10fdc6,
    CREDIT_BIOS=0xc00450, CREDIT_RETURN=0x4a992, CREDIT_ANSWER=0x10fdb0, SYSTEM_RETURN_BIOS=0xc00444,
    IRQ_VECTOR=0x64, IRQ_SR=0x2000, IRQ_BIOS_IO=0xc0044a, IRQ_BIOS_INT1=0xc00438, IRQ_RESUME=0x248, IRQ_Z80=0x320000, IRQ_VIDEO=0x3c0006;
std::uint32_t ram_get(const std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size) {
    std::uint32_t v=0;
    for (unsigned int i=0;i<size;++i) v=(v<<8)|ram[((address&0xffffffU)+i)&0xffffU];
    return v;
}
void ram_put(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value) {
    for (unsigned int i=0;i<size;++i) ram[((address&0xffffffU)+i)&0xffffU]=static_cast<std::uint8_t>(value>>(8*(size-1-i)));
}
bool head_callback(std::uint32_t pc) { return pc==0xe4a||pc==0xe74; }
bool irq_wait(std::uint32_t pc) { return pc==0xef2||pc==0x16bd0||pc==0xcda4||pc==0x3aea||pc==0x47af0||pc==0x478de; }
bool valid_palette(const AnimationMachinePaletteRam& palette) {
    return palette.banks[0].size()==8192&&palette.banks[1].size()==8192&&palette.selected<=1;
}
// run_animation_machine, or run_animation_machine_with_palette when a palette RAM device is attached.
bool machine_run(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint32_t stop_pc,
    std::uint8_t external_status, std::uint32_t& reads, AnimationMachineStatus& status, std::vector<VideoPortWrite>& ports, std::string& error) {
    if (palette!=0) return run_animation_machine_with_palette(ram,windows,resources,state,device,*palette,stop_pc,external_status,reads,status,ports,error);
    return run_animation_machine(ram,windows,resources,state,device,stop_pc,external_status,reads,status,ports,error);
}
// Declared release of the Waiting block at state.pc. Records the wait.
bool release_wait(std::vector<std::uint8_t>& ram, const AnimationMachineState& state, AnimationFrameSegment segment,
    std::vector<AnimationFrameWait>& waits, std::string& error) {
    AnimationFrameWait w;
    w.segment=segment; w.pc=state.pc; w.size=2; w.address=0; w.before=0; w.released=0;
    const std::uint32_t a5=state.a[5];
    if (state.pc==0xef2) {
        w.address=(a5-0x7feaU)&0xffffffU; w.size=1; w.released=ram_get(ram,(a5-0x7fe9U)&0xffffffU,1);
    } else if (state.pc==0x16bd0) {
        w.address=(a5+0xd34U)&0xffffffU; w.released=state.d[0]&0xffffU;
    } else if (state.pc==0x3aea) {
        w.address=0x104d74; w.released=0xffff;
    } else if (state.pc==0xcda4) {
        w.address=0x108d34; w.released=state.d[4]&0xffffU;
    } else if (state.pc==0x47af0||state.pc==0x478de) {
        if (ram_get(ram,0x107dea,2)!=0) { error="animation frame gate wait not released"; return false; }
        w.address=0x107ded; w.size=1; w.released=ram_get(ram,0x107ded,1)&0x7fU;
    } else { error="animation frame undeclared wait"; return false; }
    w.before=ram_get(ram,w.address,w.size);
    ram_put(ram,w.address,w.size,w.released);
    waits.push_back(w);
    return true;
}
// Re-run from the pre-call state with the BIOS PC as the stop. Execution is deterministic and the first run failed before reaching its
// stop, so the re-run follows the same path up to the BIOS PC or fails the same way. true: Returned exactly at bios (outputs set).
// saved_palette (null: none) is the palette at the pre-call state (a failed run leaves it unchanged); palette receives the re-run's copy.
bool run_to_bios(const std::vector<std::uint8_t>& saved_ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    const AnimationMachineState& saved_state, const AnimationMachineDevice& saved_device, const AnimationMachinePaletteRam* saved_palette,
    std::uint8_t external_status, std::uint32_t bios, std::vector<std::uint8_t>& ram, AnimationMachineState& state, AnimationMachineDevice& device,
    AnimationMachinePaletteRam& palette, std::vector<VideoPortWrite>& ports, std::uint32_t& reads) {
    ram=saved_ram; state=saved_state; device=saved_device; ports.clear(); reads=0;
    if (saved_palette!=0) palette=*saved_palette;
    AnimationMachineStatus status=AnimationMachineWaiting;
    std::string error;
    return machine_run(ram,windows,resources,state,device,saved_palette!=0?&palette:0,bios,external_status,reads,status,ports,error)&&
        status==AnimationMachineReturned&&state.pc==bios;
}
// One vblank IRQ delivered at the Waiting block state.pc (scope decisions E1-E4, E7; see animation_machine_frame.h). On success the
// state is back at the wait PC (C from the popped SR) and the record / ports are appended. On failure the inputs may be partly advanced.
bool deliver_irq(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint8_t external_status,
    const AnimationFrameOptions& options, AnimationFrameSegment segment, std::vector<VideoPortWrite>& irq_ports,
    std::vector<AnimationFrameIrq>& irqs, std::string& error) {
    if (resources.vectors==0||resources.vectors->size()<IRQ_VECTOR+4) { error="animation irq vector unavailable"; return false; }
    const AnimationMachineState pre(state);
    const std::uint32_t sp=pre.a[7]&0xffffffU;
    if ((sp&1U)!=0||sp<0x100006U||sp>0x200000U) { error="animation irq stack invalid"; return false; }
    std::uint32_t entry=0;
    for (unsigned int i=0;i<4;++i) entry=(entry<<8)|(*resources.vectors)[IRQ_VECTOR+i];
    ram_put(ram,pre.a[7]-4U,4,pre.pc);
    ram_put(ram,pre.a[7]-6U,2,IRQ_SR);
    state.a[7]=pre.a[7]-6U; state.pc=entry; state.carry=AnimationCarryUnknown;
    const std::size_t queued=device.reads.size();
    AnimationMachineExternalRead z80, video;
    z80.address=IRQ_Z80; z80.size=1; z80.value=options.irq_z80_reply;
    video.address=IRQ_VIDEO; video.size=2; video.value=options.irq_video_status;
    device.reads.insert(device.reads.begin(),video);
    device.reads.insert(device.reads.begin(),z80);
    AnimationFrameIrq rec;
    rec.segment=segment; rec.wait_pc=pre.pc; rec.sequence=static_cast<std::uint32_t>(irqs.size());
    rec.ports_begin=static_cast<std::uint32_t>(irq_ports.size()); rec.ports_end=rec.ports_begin; rec.external_reads=0; rec.bios_resumes=0; rec.rte_sr=0;
    // Part 1: 20c .. JSR c0044a.
    std::vector<VideoPortWrite> phase;
    std::uint32_t reads=0;
    AnimationMachineStatus status=AnimationMachineReturned;
    if (!machine_run(ram,windows,resources,state,device,palette,IRQ_BIOS_IO,external_status,reads,status,phase,error)) {
        // The run preserved its inputs: the same run to c00438 tells the BIOS INT1 boundary (21e JMP c00438) apart.
        std::vector<std::uint8_t> xram(ram);
        AnimationMachineState xstate(state);
        AnimationMachineDevice xdevice(device);
        AnimationMachinePaletteRam xpalette;
        if (palette!=0) xpalette=*palette;
        std::vector<VideoPortWrite> xports;
        std::uint32_t xreads=0;
        AnimationMachineStatus xstatus=AnimationMachineWaiting;
        std::string xerror;
        if (machine_run(xram,windows,resources,xstate,xdevice,palette!=0?&xpalette:0,IRQ_BIOS_INT1,external_status,xreads,xstatus,xports,xerror)&&
            xstatus==AnimationMachineReturned&&xstate.pc==IRQ_BIOS_INT1) error="animation irq bios int1 boundary";
        return false;
    }
    if (status!=AnimationMachineReturned) { error="animation irq internal wait"; return false; }
    if (state.pc!=IRQ_BIOS_IO||ram_get(ram,state.a[7],4)!=IRQ_RESUME) { error="animation irq bios return mismatch"; return false; }
    irq_ports.insert(irq_ports.end(),phase.begin(),phase.end());
    rec.external_reads+=reads; ++rec.bios_resumes;
    state.pc=IRQ_RESUME; state.a[7]+=4; state.carry=AnimationCarryUnknown;
    // Part 2: 248 .. RTE back to the wait PC.
    phase.clear(); reads=0;
    if (!machine_run(ram,windows,resources,state,device,palette,pre.pc,external_status,reads,status,phase,error)) return false;
    if (status!=AnimationMachineReturned) { error="animation irq internal wait"; return false; }
    irq_ports.insert(irq_ports.end(),phase.begin(),phase.end());
    rec.external_reads+=reads;
    rec.rte_sr=static_cast<std::uint16_t>(ram_get(ram,pre.a[7]-6U,2));
    bool same=state.pc==pre.pc;
    for (unsigned int i=0;i<8;++i) same=same&&state.d[i]==pre.d[i]&&state.a[i]==pre.a[i];
    if (!same) { error="animation irq register restore mismatch"; return false; }
    if (device.reads.size()<queued) { error="animation irq external read overrun"; return false; }
    device.reads.erase(device.reads.begin(),device.reads.begin()+static_cast<std::ptrdiff_t>(device.reads.size()-queued));
    rec.ports_end=static_cast<std::uint32_t>(irq_ports.size());
    irqs.push_back(rec);
    return true;
}
}
// One segment: run_animation_machine to stop_pc, applying the declared release (or, with irq_execution, one delivered IRQ) at every
// Waiting block and the declared BIOS boundaries.
bool run_animation_frame_segment(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint8_t external_status,
    const AnimationFrameOptions& options, std::uint32_t stop_pc, AnimationFrameSegment segment, std::vector<VideoPortWrite>& ports,
    std::vector<AnimationFrameWait>& waits, std::vector<VideoPortWrite>& irq_ports, std::vector<AnimationFrameIrq>& irqs,
    std::uint32_t& external_reads, std::string& error) {
    unsigned int count=0;
    state.carry=AnimationCarryUnknown;
    for (;;) {
        std::vector<VideoPortWrite> phase;
        std::uint32_t reads=0;
        AnimationMachineStatus status=AnimationMachineReturned;
        const std::vector<std::uint8_t> saved_ram(ram);
        const AnimationMachineState saved_state(state);
        const AnimationMachineDevice saved_device(device);
        if (!machine_run(ram,windows,resources,state,device,palette,stop_pc,external_status,reads,status,phase,error)) {
            const bool controller=segment==AnimationFrameController;
            if (!options.card_resume&&!controller) return false;
            const std::string original(error);
            std::vector<std::uint8_t> bios_ram;
            AnimationMachineState bios_state;
            AnimationMachineDevice bios_device;
            AnimationMachinePaletteRam bios_palette;
            std::vector<VideoPortWrite> bios_phase;
            std::uint32_t bios_reads=0;
            AnimationFrameWait w;
            w.segment=segment; w.pc=0; w.address=0; w.size=0; w.before=0; w.released=0;
            std::uint32_t resume=0;
            if (options.card_resume&&run_to_bios(saved_ram,windows,resources,saved_state,saved_device,palette,external_status,CARD_BIOS,bios_ram,
                bios_state,bios_device,bios_palette,bios_phase,bios_reads)) {
                const std::uint32_t ret=ram_get(bios_ram,bios_state.a[7],4);
                if (ret==CARD_RETURN||(controller&&ret==CARD_RETURN_C310)) {
                    resume=ret; w.pc=CARD_BIOS; w.address=CARD_ANSWER; w.size=1; w.released=options.card_answer;
                }
            }
            if (resume==0&&controller&&options.credit_resume&&run_to_bios(saved_ram,windows,resources,saved_state,saved_device,palette,external_status,
                CREDIT_BIOS,bios_ram,bios_state,bios_device,bios_palette,bios_phase,bios_reads)&&ram_get(bios_ram,bios_state.a[7],4)==CREDIT_RETURN) {
                resume=CREDIT_RETURN; w.pc=CREDIT_BIOS; w.address=CREDIT_ANSWER; w.size=4; w.released=options.credit_answer;
            }
            if (resume==0&&controller&&run_to_bios(saved_ram,windows,resources,saved_state,saved_device,palette,external_status,SYSTEM_RETURN_BIOS,
                bios_ram,bios_state,bios_device,bios_palette,bios_phase,bios_reads)) {
                ram=saved_ram; state=saved_state; device=saved_device; error="animation frame controller system return"; return false;
            }
            if (resume==0||count>=MAX_WAITS) { ram=saved_ram; state=saved_state; device=saved_device; error=original; return false; }
            ++count;
            w.before=ram_get(bios_ram,w.address,w.size);
            ram_put(bios_ram,w.address,w.size,w.released);
            waits.push_back(w);
            bios_state.pc=resume; bios_state.a[7]+=4; bios_state.carry=AnimationCarryUnknown;
            ram.swap(bios_ram); state=bios_state; device=bios_device;
            if (palette!=0) { palette->banks[0].swap(bios_palette.banks[0]); palette->banks[1].swap(bios_palette.banks[1]); palette->selected=bios_palette.selected; }
            ports.insert(ports.end(),bios_phase.begin(),bios_phase.end());
            external_reads+=bios_reads;
            continue;
        }
        ports.insert(ports.end(),phase.begin(),phase.end());
        external_reads+=reads;
        if (status==AnimationMachineReturned) return true;
        if (options.irq_execution&&irq_wait(state.pc)) {
            if (count>=MAX_WAITS) { error="animation irq wait not released"; return false; }
            ++count;
            if (!deliver_irq(ram,windows,resources,state,device,palette,external_status,options,segment,irq_ports,irqs,error)) return false;
            continue;
        }
        if (count>=MAX_WAITS) { error="animation frame wait limit"; return false; }
        ++count;
        if (!release_wait(ram,state,segment,waits,error)) return false;
    }
}
bool run_animation_frame_segment(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, std::uint8_t external_status,
    const AnimationFrameOptions& options, std::uint32_t stop_pc, AnimationFrameSegment segment, std::vector<VideoPortWrite>& ports, std::vector<AnimationFrameWait>& waits,
    std::uint32_t& external_reads, std::string& error) {
    std::vector<VideoPortWrite> irq_ports;
    std::vector<AnimationFrameIrq> irqs;
    return run_animation_frame_segment(ram,windows,resources,state,device,0,external_status,options,stop_pc,segment,ports,waits,irq_ports,irqs,
        external_reads,error);
}
namespace {
// N segment on the working copies; entry conditions already hold.
bool run_nodes(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint8_t external_status,
    const AnimationFrameOptions& options, AnimationFrameResult& r, std::string& error) {
    if (state.pc!=DISPATCH_PC||state.a[6]!=CONTROLLER_LONG||state.a[7]!=SPD) { error="animation frame pass entry mismatch"; return false; }
    const std::uint32_t stop=ram_get(ram,HEAD_LONG,4);
    if (!head_callback(stop)) { error="animation frame head callback unsupported"; return false; }
    if (!run_animation_frame_segment(ram,windows,resources,state,device,palette,external_status,options,stop,AnimationFrameNodes,r.node_ports,r.waits,
        r.irq_ports,r.irqs,r.node_external_reads,error)) return false;
    if (state.pc!=stop||state.a[6]!=HEAD_LONG||state.a[7]!=SPD-4||ram_get(ram,SPD-4,4)!=DISPATCH_PC||
        state.a[5]!=0x108000||state.a[0]!=stop||ram_get(ram,HEAD_LONG,4)!=stop) {
        error="animation frame pass boundary mismatch"; return false;
    }
    r.pass_stop_pc=stop;
    return true;
}
// Both entry points on working copies (palette: null = no palette RAM device).
bool pass_impl(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint8_t external_status,
    const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    if (palette!=0&&!valid_palette(*palette)) { error="invalid animation machine palette RAM"; return false; }
    std::vector<std::uint8_t> wram(ram);
    AnimationMachineState wstate(state);
    AnimationMachineDevice wdevice(device);
    AnimationMachinePaletteRam wpalette;
    if (palette!=0) wpalette=*palette;
    AnimationFrameResult wresult;
    std::string werror;
    if (!run_nodes(wram,windows,resources,wstate,wdevice,palette!=0?&wpalette:0,external_status,options,wresult,werror)) { error=werror; return false; }
    ram.swap(wram); state=wstate; device=wdevice; result=wresult;
    if (palette!=0) { palette->banks[0].swap(wpalette.banks[0]); palette->banks[1].swap(wpalette.banks[1]); palette->selected=wpalette.selected; }
    return true;
}
bool frame_impl(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint8_t external_status,
    const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    if (palette!=0&&!valid_palette(*palette)) { error="invalid animation machine palette RAM"; return false; }
    std::vector<std::uint8_t> wram(ram);
    AnimationMachineState wstate(state);
    AnimationMachineDevice wdevice(device);
    AnimationMachinePaletteRam wpalette;
    if (palette!=0) wpalette=*palette;
    AnimationMachinePaletteRam* const wp=palette!=0?&wpalette:0;
    AnimationFrameResult wresult;
    std::string werror;
    const std::uint32_t head=ram_get(wram,HEAD_LONG,4);
    if (!head_callback(head)) { error="animation frame head callback unsupported"; return false; }
    if (wstate.pc!=head||wstate.a[6]!=HEAD_LONG||wstate.a[7]!=SPD-4||ram_get(wram,SPD-4,4)!=DISPATCH_PC) {
        error="animation frame head entry mismatch"; return false;
    }
    const std::uint32_t controller=ram_get(wram,CONTROLLER_LONG,4);
    if (!run_animation_frame_segment(wram,windows,resources,wstate,wdevice,wp,external_status,options,controller,AnimationFrameHead,wresult.head_ports,
        wresult.waits,wresult.irq_ports,wresult.irqs,wresult.head_external_reads,werror)) { error=werror; return false; }
    if (wstate.pc!=controller||wstate.a[6]!=CONTROLLER_LONG||wstate.a[7]!=SPD-4||ram_get(wram,SPD-4,4)!=DISPATCH_PC||
        ram_get(wram,CONTROLLER_LONG,4)!=controller||wstate.a[5]!=0x108000||wstate.a[0]!=controller) { error="animation frame head boundary mismatch"; return false; }
    if (options.controller_mode==AnimationFrameControllerExecute) {
        // C: the controller from its entry (PC = controller, A7 = SPd - 4 holding 2ac2) to the dispatcher return 2ac2. The head LONG
        // (100820) must be the one at the C start (H itself changes it, e4a -> e74 on the first frame) and a supported head callback.
        const std::uint32_t c_head=ram_get(wram,HEAD_LONG,4);
        if (!run_animation_frame_segment(wram,windows,resources,wstate,wdevice,wp,external_status,options,DISPATCH_PC,AnimationFrameController,
            wresult.controller_ports,wresult.waits,wresult.irq_ports,wresult.irqs,wresult.controller_external_reads,werror)) { error=werror; return false; }
        if (wstate.pc!=DISPATCH_PC||wstate.a[7]!=SPD||wstate.a[6]!=CONTROLLER_LONG||wstate.a[5]!=0x108000||ram_get(wram,HEAD_LONG,4)!=c_head||
            !head_callback(c_head)) {
            error="animation frame controller boundary mismatch"; return false;
        }
        wresult.controller_exit_pc=ram_get(wram,CONTROLLER_LONG,4);
        wstate.carry=AnimationCarryUnknown;
    } else {
        wstate.pc=DISPATCH_PC; wstate.a[7]=SPD; wstate.carry=AnimationCarryUnknown;
    }
    if (!run_nodes(wram,windows,resources,wstate,wdevice,wp,external_status,options,wresult,werror)) { error=werror; return false; }
    wresult.head_pc=head; wresult.controller_pc=controller;
    ram.swap(wram); state=wstate; device=wdevice; result=wresult;
    if (palette!=0) { palette->banks[0].swap(wpalette.banks[0]); palette->banks[1].swap(wpalette.banks[1]); palette->selected=wpalette.selected; }
    return true;
}
}
bool run_animation_machine_pass(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    return pass_impl(ram,windows,resources,state,device,0,external_status,options,result,error);
}
bool run_animation_machine_pass(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam& palette,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    return pass_impl(ram,windows,resources,state,device,&palette,external_status,options,result,error);
}
bool step_animation_machine_frame(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    return frame_impl(ram,windows,resources,state,device,0,external_status,options,result,error);
}
bool step_animation_machine_frame(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam& palette,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    return frame_impl(ram,windows,resources,state,device,&palette,external_status,options,result,error);
}
}

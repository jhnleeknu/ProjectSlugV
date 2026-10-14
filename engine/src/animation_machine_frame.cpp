#include "ms5/animation_machine_frame.h"
namespace ms5 {
namespace {
const std::uint32_t HEAD_LONG=0x100820, CONTROLLER_LONG=0x1008e4, SPD=0x1ff000, DISPATCH_PC=0x2ac2, MAX_WAITS=16,
    CARD_BIOS=0xc00468, CARD_RETURN=0xc37c, CARD_ANSWER=0x10fdc6;
std::uint32_t ram_get(const std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size) {
    std::uint32_t v=0;
    for (unsigned int i=0;i<size;++i) v=(v<<8)|ram[((address&0xffffffU)+i)&0xffffU];
    return v;
}
void ram_put(std::vector<std::uint8_t>& ram, std::uint32_t address, unsigned int size, std::uint32_t value) {
    for (unsigned int i=0;i<size;++i) ram[((address&0xffffffU)+i)&0xffffU]=static_cast<std::uint8_t>(value>>(8*(size-1-i)));
}
bool head_callback(std::uint32_t pc) { return pc==0xe4a||pc==0xe74; }
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
// One segment: run_animation_machine to stop_pc, applying the declared release at every Waiting block.
bool run_segment(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, std::uint8_t external_status,
    const AnimationFrameOptions& options, std::uint32_t stop_pc, AnimationFrameSegment segment, std::vector<VideoPortWrite>& ports, std::vector<AnimationFrameWait>& waits,
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
        if (!run_animation_machine(ram,windows,resources,state,device,stop_pc,external_status,reads,status,phase,error)) {
            // Execution is deterministic and the first run failed before reaching its stop, so a re-run from the same
            // state with stop c00468 follows the same path up to the BIOS card request or fails the same way.
            if (!options.card_resume) return false;
            const std::string original(error);
            std::vector<std::uint8_t> card_ram(saved_ram);
            AnimationMachineState card_state(saved_state);
            AnimationMachineDevice card_device(saved_device);
            std::vector<VideoPortWrite> card_phase;
            std::uint32_t card_reads=0;
            AnimationMachineStatus card_status=AnimationMachineWaiting;
            std::string card_error;
            if (!run_animation_machine(card_ram,windows,resources,card_state,card_device,CARD_BIOS,external_status,card_reads,
                card_status,card_phase,card_error)||card_status!=AnimationMachineReturned||card_state.pc!=CARD_BIOS||
                ram_get(card_ram,card_state.a[7],4)!=CARD_RETURN||count>=MAX_WAITS) { ram=saved_ram; state=saved_state; device=saved_device; error=original; return false; }
            ++count;
            AnimationFrameWait w;
            w.segment=segment; w.pc=CARD_BIOS; w.address=CARD_ANSWER; w.size=1;
            w.before=ram_get(card_ram,CARD_ANSWER,1); w.released=options.card_answer;
            ram_put(card_ram,CARD_ANSWER,1,options.card_answer);
            waits.push_back(w);
            card_state.pc=CARD_RETURN; card_state.a[7]+=4; card_state.carry=AnimationCarryUnknown;
            ram.swap(card_ram); state=card_state; device=card_device;
            ports.insert(ports.end(),card_phase.begin(),card_phase.end());
            external_reads+=card_reads;
            continue;
        }
        ports.insert(ports.end(),phase.begin(),phase.end());
        external_reads+=reads;
        if (status==AnimationMachineReturned) return true;
        if (count>=MAX_WAITS) { error="animation frame wait limit"; return false; }
        ++count;
        if (!release_wait(ram,state,segment,waits,error)) return false;
    }
}
// N segment on the working copies; entry conditions already hold.
bool run_nodes(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, std::uint8_t external_status,
    const AnimationFrameOptions& options, AnimationFrameResult& r, std::string& error) {
    if (state.pc!=DISPATCH_PC||state.a[6]!=CONTROLLER_LONG||state.a[7]!=SPD) { error="animation frame pass entry mismatch"; return false; }
    const std::uint32_t stop=ram_get(ram,HEAD_LONG,4);
    if (!head_callback(stop)) { error="animation frame head callback unsupported"; return false; }
    if (!run_segment(ram,windows,resources,state,device,external_status,options,stop,AnimationFrameNodes,r.node_ports,r.waits,
        r.node_external_reads,error)) return false;
    if (state.pc!=stop||state.a[6]!=HEAD_LONG||state.a[7]!=SPD-4||ram_get(ram,SPD-4,4)!=DISPATCH_PC||
        state.a[5]!=0x108000||state.a[0]!=stop||ram_get(ram,HEAD_LONG,4)!=stop) {
        error="animation frame pass boundary mismatch"; return false;
    }
    r.pass_stop_pc=stop;
    return true;
}
}
bool run_animation_machine_pass(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    std::vector<std::uint8_t> wram(ram);
    AnimationMachineState wstate(state);
    AnimationMachineDevice wdevice(device);
    AnimationFrameResult wresult;
    std::string werror;
    if (!run_nodes(wram,windows,resources,wstate,wdevice,external_status,options,wresult,werror)) { error=werror; return false; }
    ram.swap(wram); state=wstate; device=wdevice; result=wresult;
    return true;
}
bool step_animation_machine_frame(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error) {
    std::vector<std::uint8_t> wram(ram);
    AnimationMachineState wstate(state);
    AnimationMachineDevice wdevice(device);
    AnimationFrameResult wresult;
    std::string werror;
    const std::uint32_t head=ram_get(wram,HEAD_LONG,4);
    if (!head_callback(head)) { error="animation frame head callback unsupported"; return false; }
    if (wstate.pc!=head||wstate.a[6]!=HEAD_LONG||wstate.a[7]!=SPD-4||ram_get(wram,SPD-4,4)!=DISPATCH_PC) {
        error="animation frame head entry mismatch"; return false;
    }
    const std::uint32_t controller=ram_get(wram,CONTROLLER_LONG,4);
    if (!run_segment(wram,windows,resources,wstate,wdevice,external_status,options,controller,AnimationFrameHead,wresult.head_ports,
        wresult.waits,wresult.head_external_reads,werror)) { error=werror; return false; }
    if (wstate.pc!=controller||wstate.a[6]!=CONTROLLER_LONG||wstate.a[7]!=SPD-4||ram_get(wram,SPD-4,4)!=DISPATCH_PC||
        ram_get(wram,CONTROLLER_LONG,4)!=controller||wstate.a[5]!=0x108000||wstate.a[0]!=controller) { error="animation frame head boundary mismatch"; return false; }
    wstate.pc=DISPATCH_PC; wstate.a[7]=SPD; wstate.carry=AnimationCarryUnknown;
    if (!run_nodes(wram,windows,resources,wstate,wdevice,external_status,options,wresult,werror)) { error=werror; return false; }
    wresult.head_pc=head; wresult.controller_pc=controller;
    ram.swap(wram); state=wstate; device=wdevice; result=wresult;
    return true;
}
}

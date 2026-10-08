#ifndef MS5_ANIMATION_MACHINE_INTERNAL_H
#define MS5_ANIMATION_MACHINE_INTERNAL_H
#include "ms5/animation_machine.h"
#include "ms5/program_stack.h"
namespace ms5 {
struct AnimationMachineContext {
    std::vector<std::uint8_t>& ram;
    const std::vector<FixedDataResource>& windows;
    ProgramBusState bus;
    AnimationMachineState& s;
    AnimationMachineDevice& device;
    std::vector<VideoPortWrite>& ports;
    std::uint8_t external_status;
    std::uint32_t external_reads;
    bool waiting;
    std::string& error;
    AnimationMachineContext(std::vector<std::uint8_t>& r,
        const std::vector<FixedDataResource>& w,const ProgramBusState& b,
        AnimationMachineState& state,AnimationMachineDevice& dev,
        std::vector<VideoPortWrite>& p,std::uint8_t ext,std::string& e)
        : ram(r),windows(w),bus(b),s(state),device(dev),ports(p),
          external_status(ext),external_reads(0),waiting(false),error(e) {
        bus.pvc=&device.pvc;bus.bank_base=device.bank_base;
    }
};
void am_byte(std::uint32_t& r,std::uint32_t value);
void am_word(std::uint32_t& r,std::uint32_t value);
void am_swap(std::uint32_t& r);
std::uint32_t am_extend_word(std::uint32_t value);
std::uint32_t am_index(std::uint32_t base,std::uint32_t word);
bool am_read(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t& value);
bool am_write(AnimationMachineContext& c,std::uint32_t address,unsigned int size,std::uint32_t value);
bool am_fetch(AnimationMachineContext& c,unsigned int size,std::uint32_t& value);
bool am_push(AnimationMachineContext& c,unsigned int size,std::uint32_t value);
bool am_pop(AnimationMachineContext& c,unsigned int size,std::uint32_t& value);
bool am_call(AnimationMachineContext& c,std::uint32_t target,std::uint32_t return_pc);
bool am_return(AnimationMachineContext& c);
bool am_zero_bank(AnimationMachineContext& c);
bool am_error(AnimationMachineContext& c,const char* message);
bool animation_interpreter_block(AnimationMachineContext& c);
bool animation_sound_block(AnimationMachineContext& c);
bool animation_sprite_block(AnimationMachineContext& c);
bool animation_readiness_block(AnimationMachineContext& c);
bool animation_hud_block(AnimationMachineContext& c);
bool animation_transition_block(AnimationMachineContext& c);
bool animation_exit_block(AnimationMachineContext& c);
bool animation_screen_block(AnimationMachineContext& c);
}
#endif

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
bool animation_cleanup_block(AnimationMachineContext& c);
bool animation_palette_bind_block(AnimationMachineContext& c);
bool animation_map_transfer_block(AnimationMachineContext& c);
bool animation_scene_block(AnimationMachineContext& c);
bool animation_fade_card_block(AnimationMachineContext& c);
bool animation_card_child_block(AnimationMachineContext& c);
bool animation_card_menu_block(AnimationMachineContext& c);
bool animation_card_menu_open_block(AnimationMachineContext& c);
bool animation_card_menu_input_block(AnimationMachineContext& c);
bool animation_card_menu_close_block(AnimationMachineContext& c);
bool animation_card_menu_save_block(AnimationMachineContext& c);
bool animation_card_menu_nested_block(AnimationMachineContext& c);
bool animation_frame_helpers_block(AnimationMachineContext& c);
bool animation_scene_core_block(AnimationMachineContext& c);
bool animation_motion_walk_block(AnimationMachineContext& c);
bool animation_scene_update_block(AnimationMachineContext& c);
bool animation_script_placement_block(AnimationMachineContext& c);
bool animation_input_block(AnimationMachineContext& c);
bool animation_buffer_cue_block(AnimationMachineContext& c);
bool animation_stage_entry_block(AnimationMachineContext& c);
bool animation_area_clear_block(AnimationMachineContext& c);
bool animation_stage_catalog_block(AnimationMachineContext& c);
bool animation_stage_area_block(AnimationMachineContext& c);
bool animation_stage_event_block(AnimationMachineContext& c);
bool animation_stage_event_ops_block(AnimationMachineContext& c);
bool animation_scheduler_block(AnimationMachineContext& c);
bool animation_objects_u01_block(AnimationMachineContext& c);
bool animation_objects_u02_block(AnimationMachineContext& c);
bool animation_objects_u03_block(AnimationMachineContext& c);
bool animation_objects_u05_block(AnimationMachineContext& c);
bool animation_objects_u04_block(AnimationMachineContext& c);
bool animation_objects_u06_block(AnimationMachineContext& c);
bool animation_objects_u07_block(AnimationMachineContext& c);
bool animation_objects_u08_block(AnimationMachineContext& c);
bool animation_objects_u09_block(AnimationMachineContext& c);
bool animation_objects_u08b_block(AnimationMachineContext& c);
bool animation_objects_u10_block(AnimationMachineContext& c);
bool animation_objects_u11_block(AnimationMachineContext& c);
bool animation_objects_u12_block(AnimationMachineContext& c);
bool animation_objects_u13_block(AnimationMachineContext& c);
bool animation_objects_u14_block(AnimationMachineContext& c);
bool animation_objects_u15_block(AnimationMachineContext& c);
bool animation_objects_u16_block(AnimationMachineContext& c);
bool animation_objects_u15b_block(AnimationMachineContext& c);
bool animation_objects_u15c_block(AnimationMachineContext& c);
bool animation_objects_u17_block(AnimationMachineContext& c);
bool animation_objects_u18_block(AnimationMachineContext& c);
bool animation_objects_u19_block(AnimationMachineContext& c);
bool animation_objects_u20_block(AnimationMachineContext& c);
bool animation_objects_u20b_block(AnimationMachineContext& c);
bool animation_objects_n01_block(AnimationMachineContext& c);
bool animation_objects_n03_block(AnimationMachineContext& c);
bool animation_objects_n04_block(AnimationMachineContext& c);
bool animation_objects_n05_block(AnimationMachineContext& c);
bool animation_objects_n06_block(AnimationMachineContext& c);
bool animation_objects_n07_block(AnimationMachineContext& c);
bool animation_objects_n08_block(AnimationMachineContext& c);
bool animation_objects_n09_block(AnimationMachineContext& c);
bool animation_objects_n10_block(AnimationMachineContext& c);
bool animation_objects_n11_block(AnimationMachineContext& c);
bool animation_objects_n12_block(AnimationMachineContext& c);
bool animation_objects_n13_block(AnimationMachineContext& c);
bool animation_objects_n14_block(AnimationMachineContext& c);
bool animation_objects_n15_block(AnimationMachineContext& c);
bool animation_objects_n16_block(AnimationMachineContext& c);
bool animation_objects_n17_block(AnimationMachineContext& c);
bool animation_objects_n18_block(AnimationMachineContext& c);
bool animation_objects_n19_block(AnimationMachineContext& c);
bool animation_objects_n20_block(AnimationMachineContext& c);
bool animation_objects_n21_block(AnimationMachineContext& c);
bool animation_objects_n22_block(AnimationMachineContext& c);
bool animation_objects_n23_block(AnimationMachineContext& c);
bool animation_objects_n28_block(AnimationMachineContext& c);
bool animation_objects_n24_block(AnimationMachineContext& c);
bool animation_objects_n29_block(AnimationMachineContext& c);
bool animation_objects_n25_block(AnimationMachineContext& c);
bool animation_objects_n26_block(AnimationMachineContext& c);
bool animation_objects_n30_block(AnimationMachineContext& c);
bool animation_objects_n27_block(AnimationMachineContext& c);
bool animation_objects_n31_block(AnimationMachineContext& c);
bool animation_objects_n32_block(AnimationMachineContext& c);
bool animation_frame_head_h1_block(AnimationMachineContext& c);
bool animation_objects_n32b_block(AnimationMachineContext& c);
bool animation_objects_n33_block(AnimationMachineContext& c);
bool animation_frame_head_h3_block(AnimationMachineContext& c);
bool animation_frame_head_h4_block(AnimationMachineContext& c);
bool animation_objects_n35_block(AnimationMachineContext& c);
bool animation_frame_head_h2_block(AnimationMachineContext& c);
bool animation_objects_n34_block(AnimationMachineContext& c);
bool animation_frame_head_h8_block(AnimationMachineContext& c);
bool animation_objects_b1b_block(AnimationMachineContext& c);
}
#endif

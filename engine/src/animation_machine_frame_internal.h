#ifndef MS5_ANIMATION_MACHINE_FRAME_INTERNAL_H
#define MS5_ANIMATION_MACHINE_FRAME_INTERNAL_H
#include "ms5/animation_machine_frame.h"
namespace ms5 {
// One frame-driver segment (internal, exposed for unit tests): run_animation_machine from state to stop_pc with the declared releases of
// animation_machine_frame.h (at most 16 per call) and the declared BIOS boundaries of the segment (card in every segment when
// options.card_resume; card c316, credit and the system return only for AnimationFrameController). Starts with C Unknown. Appends to
// ports / waits / external_reads. On failure ram / state / device may hold a partially advanced state: callers work on copies.
bool run_animation_frame_segment(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, std::uint8_t external_status,
    const AnimationFrameOptions& options, std::uint32_t stop_pc, AnimationFrameSegment segment, std::vector<VideoPortWrite>& ports,
    std::vector<AnimationFrameWait>& waits, std::uint32_t& external_reads, std::string& error);
// The same with an optional palette RAM device (null: none) and the IRQ outputs of options.irq_execution (the overload above drops them).
bool run_animation_frame_segment(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam* palette, std::uint8_t external_status,
    const AnimationFrameOptions& options, std::uint32_t stop_pc, AnimationFrameSegment segment, std::vector<VideoPortWrite>& ports,
    std::vector<AnimationFrameWait>& waits, std::vector<VideoPortWrite>& irq_ports, std::vector<AnimationFrameIrq>& irqs,
    std::uint32_t& external_reads, std::string& error);
}
#endif

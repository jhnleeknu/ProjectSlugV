#ifndef MS5_ANIMATION_MACHINE_IRQ_H
#define MS5_ANIMATION_MACHINE_IRQ_H
#include "ms5/animation_machine.h"
namespace ms5 {
// Palette RAM device (F6 scope decision E6 as decided): two 8 KiB banks. A BYTE write to 3a000f selects bank 0, one to 3a001f bank 1
// (the address selects; the written value is ignored and the write stays an ordered port). Reads and writes of 400000..7fffff address
// the selected bank at (address & 1fff) (mirror) and are not ports. The display/CPU bank distinction is not modelled (one selection).
struct AnimationMachinePaletteRam {
    std::vector<std::uint8_t> banks[2];
    std::uint8_t selected;
    AnimationMachinePaletteRam() : selected(0) {banks[0].assign(8192,0);banks[1].assign(8192,0);}
};
// run_animation_machine with an attached palette RAM device. Same contract as run_animation_machine; additionally both banks must hold
// exactly 8192 bytes and selected must be 0 or 1 ("invalid animation machine palette RAM"). The palette is part of the transaction:
// it is committed only when the run succeeds and preserved on every failure. run_animation_machine itself has no palette RAM: its
// 400000..7fffff accesses stay the checked device errors, and 3a000f / 3a001f writes are ports only.
bool run_animation_machine_with_palette(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, const ProgramBusState& resources,
    AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam& palette,
    std::uint32_t stop_pc, std::uint8_t external_status,
    std::uint32_t& external_reads, AnimationMachineStatus& status,
    std::vector<VideoPortWrite>& ports, std::string& error);
}
#endif

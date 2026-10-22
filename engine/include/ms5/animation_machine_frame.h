#ifndef MS5_ANIMATION_MACHINE_FRAME_H
#define MS5_ANIMATION_MACHINE_FRAME_H
#include "ms5/animation_machine.h"
#include "ms5/animation_machine_irq.h"
namespace ms5 {
// Frame driver over run_animation_machine only (F5 decisions D1, D9). One frame = H + controller (declared skip or executed) + N:
//   H: the frame head from PC = LONG (100820) (e4a on the first frame, e74 later) through its RTS to 2ac2; the dispatcher
//      (2ac2..2ac6 / 2ab8, A6 = 1008e4, JSR (A0)) is where the controller LONG (1008e4), e.g. c52a, would be entered. H stops there.
//   skip (AnimationFrameControllerSkip, default): the declared controller skip (PC := 2ac2, A7 += 4 = the RTS the controller would run,
//      C Unknown). The controller is not run.
//   C (AnimationFrameControllerExecute, D9): the controller from PC = LONG (1008e4) until its RTS returns to the dispatcher 2ac2 (the
//      first 2ac2 reached; C Unknown at the start, the same declared releases and limit). It must end with A7 = 1ff000, A6 = 1008e4,
//      A5 = 108000 and LONG (100820) unchanged from the C start and e4a / e74, else "animation frame controller boundary mismatch".
//   N: the existing F2 node pass from 2ac2 until the dispatcher enters LONG (100820).
// BIOS, IRQ and (in Skip mode) the controller are not executed. Each segment starts with C Unknown. Only the head callbacks e4a / e74 are supported.
// External-read queue (device.reads): only H reads it. C and N have no declared external reads (IO scope 5.6, E1 contract decision 2): the
//   entries left after H are held back during C / N and put back unchanged, so a queue-device read there fails with "animation machine
//   external read queue empty" (the native undeclared-device-read guard). A delivered IRQ reads only the two entries it adds (below).
// Declared wait releases (one per Waiting block, recorded in AnimationFrameWait; at most 16 waits per segment):
//   ef2   BYTE (A5-7fea) := BYTE (A5-7fe9)   (vblank)          16bd0  WORD (A5+d34) := D0.W   (sprite flush)
//   3aea  WORD 104d74 := ffff                (sound ring)      cda4   WORD 108d34 := D4.W     (sprite queue)
//   47af0 / 478de  BYTE 107ded &= 7f only if WORD 107dea == 0, else a checked error (gate).
// Any other wait PC is a checked error. Addresses are 24-bit, RAM index = address & ffff.
// IRQ execution (F6 scope decisions E1-E4, E7, E10; options.irq_execution, default false = the declared releases above, unchanged):
//   at a Waiting block ef2 / 16bd0 / cda4 / 3aea / 47af0 / 478de the driver delivers ONE vblank IRQ instead of the declared release
//   and re-runs the same wait block (a declared delivery point; the real vblank timing is not modelled). Delivery: LONG (A7 - 4) :=
//   wait PC, WORD (A7 - 6) := 2000 (declared SR), A7 -= 6, PC := ROM LONG at vector 64 (resources.vectors), C Unknown; the queue gets
//   BYTE 320000 = irq_z80_reply and WORD 3c0006 = irq_video_status at its front. Part 1 runs to the BIOS SYSTEM_IO c0044a, which is
//   the declared resume (LONG (A7) must be 248: PC := 248, A7 += 4, C Unknown); part 2 runs to the wait PC (the IRQ's RTE returns
//   there). D0-D7 / A0-A7 must equal the values at delivery ("animation irq register restore mismatch"); unconsumed IRQ queue entries
//   are removed (consuming more than the two is "animation irq external read overrun"). Deliveries share the 16-per-segment limit
//   ("animation irq wait not released"). Checked IRQ errors: "animation irq vector unavailable", "animation irq stack invalid",
//   "animation irq bios int1 boundary" (BYTE 10fd80 bit 7 = 0: 21e JMP c00438), "animation irq internal wait", "animation irq bios
//   return mismatch"; any executor error inside the IRQ is returned as is. The card BIOS resume is unchanged. IRQ ports go to
//   result.irq_ports (not to head / node / controller ports), IRQ reads are counted per IRQ (not in the segment read counts).
//   The palette RAM device is attached only through the overloads taking an AnimationMachinePaletteRam (part of the driver state).
enum AnimationFrameSegment { AnimationFrameHead=0, AnimationFrameNodes=1, AnimationFrameController=2 };
enum AnimationFrameControllerMode { AnimationFrameControllerSkip=0, AnimationFrameControllerExecute=1 };
struct AnimationFrameWait {
    AnimationFrameSegment segment;
    std::uint32_t pc;       // the Waiting block
    std::uint32_t address;  // released address (24-bit)
    std::uint8_t size;      // BYTEs
    std::uint32_t before, released;
};
// card_resume: the declared BIOS card request (N reaches c376 JSR c00468; BIOS is not executed). When a run fails, it is re-run
// from the same pre-call state with stop PC c00468. If that returns at c00468 with LONG (A7) = c37c, the request is declared
// answered: BYTE 10fdc6 := card_answer, PC := c37c, A7 += 4, C Unknown, recorded as an AnimationFrameWait (pc c00468, address
// 10fdc6, size 1) and counted in the 16-wait limit. Any other outcome returns the original error. false: no card handling.
// Controller segment only (Execute), BIOS boundaries tried in this order by the same re-run from the pre-call state:
//   c00468 card     (card_resume) LONG (A7) = c37c or c316: as above, PC := that return.
//   c00450 credit   (credit_resume) LONG (A7) = 4a992: LONG 10fdb0 := credit_answer, PC := 4a992, A7 += 4, C Unknown, recorded as an
//                   AnimationFrameWait (pc c00450, address 10fdb0, size 4), counted in the limit.
//   c00444 system return (JMP, always): the frame fails with "animation frame controller system return" (everything preserved).
struct AnimationFrameOptions {
    bool card_resume;
    std::uint8_t card_answer;
    AnimationFrameControllerMode controller_mode;
    bool credit_resume;
    std::uint32_t credit_answer;
    bool irq_execution;              // false: declared releases (D1 / D9 behaviour, byte-identical)
    std::uint8_t irq_z80_reply;      // BYTE 320000 supplied per IRQ (E7)
    std::uint16_t irq_video_status;  // WORD 3c0006 supplied per IRQ (E7)
    AnimationFrameOptions() : card_resume(false), card_answer(0x80), controller_mode(AnimationFrameControllerSkip), credit_resume(false),
        credit_answer(0x01010000U), irq_execution(false), irq_z80_reply(0), irq_video_status(0) {}
};
// One delivered IRQ (options.irq_execution). sequence: index in result.irqs; ports: [ports_begin, ports_end) of result.irq_ports;
// external_reads: reads of the IRQ runs (queue + status); bios_resumes: declared c0044a resumes; rte_sr: the WORD the RTE popped.
struct AnimationFrameIrq {
    AnimationFrameSegment segment;
    std::uint32_t wait_pc, sequence, ports_begin, ports_end, external_reads, bios_resumes;
    std::uint16_t rte_sr;
};
struct AnimationFrameResult {
    std::uint32_t head_pc;        // LONG (100820) at the H start; 0 for run_animation_machine_pass
    std::uint32_t controller_pc;  // LONG (1008e4) at the H start (= H stop PC); 0 for run_animation_machine_pass
    std::uint32_t pass_stop_pc;   // LONG (100820) at the N start (= N stop PC)
    std::uint32_t controller_exit_pc;  // LONG (1008e4) at the end of an executed controller; 0 in Skip mode and for the pass
    std::vector<VideoPortWrite> head_ports, node_ports, controller_ports;  // execution order
    std::vector<AnimationFrameWait> waits;               // in order, all segments
    std::uint32_t head_external_reads, node_external_reads, controller_external_reads;
    std::vector<AnimationFrameIrq> irqs;                 // in delivery order, all segments (irq_execution only)
    std::vector<VideoPortWrite> irq_ports;               // ports written inside the delivered IRQs, execution order
    AnimationFrameResult() : head_pc(0), controller_pc(0), pass_stop_pc(0), controller_exit_pc(0), head_external_reads(0), node_external_reads(0),
        controller_external_reads(0) {}
};
// N only (frame 0 from a seed): PC 2ac2, A6 1008e4, A7 1ff000; stop = LONG (100820), which must be e4a / e74.
// Ends at PC = stop, A6 = 100820, A7 = 1feffc, LONG (1feffc) = 2ac2 (a valid H start).
// Both functions work on copies: any failure returns false with ram, state, device and result unchanged and error set.
bool run_animation_machine_pass(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error);
// H + skip (or C, options.controller_mode) + N from a valid H start (PC = LONG (100820), A6 100820, A7 1feffc, LONG (1feffc) = 2ac2).
bool step_animation_machine_frame(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error);
// The same two functions with the palette RAM device attached (run_animation_machine_with_palette for every run). The palette is part of
// the transaction (committed on success, unchanged on failure); banks must hold 8192 bytes each and selected must be 0 or 1
// ("invalid animation machine palette RAM"). The overloads above run without palette RAM.
bool run_animation_machine_pass(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam& palette,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error);
bool step_animation_machine_frame(std::vector<std::uint8_t>& ram, const std::vector<FixedDataResource>& windows,
    const ProgramBusState& resources, AnimationMachineState& state, AnimationMachineDevice& device, AnimationMachinePaletteRam& palette,
    std::uint8_t external_status, const AnimationFrameOptions& options, AnimationFrameResult& result, std::string& error);
}
#endif

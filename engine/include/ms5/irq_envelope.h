#ifndef MS5_IRQ_ENVELOPE_H
#define MS5_IRQ_ENVELOPE_H
#include "ms5/interrupt_task.h"
namespace ms5 {
struct IrqEnvelopeResult {
    std::uint32_t next_pc;
    bool bios_handoff;
    std::vector<VideoPortWrite> stack_writes;
    IrqEnvelopeResult() : next_pc(0),bios_handoff(false) {}
};
// Native20c to callback entry or BIOS c00438. No callback/BIOS execution.
// Stack is an explicit external memory span: aligned base>=110000, even size,
// ending at or below1000000. Active entry needs bytes[A7-68,A7) and A7<=fffffe.
// BIOS branch does not access or validate the unused stack span.
// MMIO and chronological stack writes are separate; stack bytes are updated.
// Failure preserves RAM/stack/registers/result/ports; SR/CCR is not represented.
bool begin_irq_envelope(std::vector<std::uint8_t>& ram,
                        std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                        InterruptRegisters& registers,IrqEnvelopeResult& result,
                        std::vector<VideoPortWrite>& ports,std::string& error);
// Native248 after BIOS call returns, stopping at29a BEFORE RTE.
// Stack[A7,A7+64) supplies saved bank, VRAM address and15 saved registers.
// Temporary MOVEM.W uses bytes[A7-2,A7+2); caller mutations of saved state are
// observed. Final A7=A7+64<=fffffe. video_status is the word read at3c0006.
bool finish_irq_envelope(std::vector<std::uint8_t>& ram,
                         std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                         InterruptRegisters& registers,std::uint16_t video_status,
                         IrqEnvelopeResult& result,std::vector<VideoPortWrite>& ports,
                         std::string& error);
// Native3dcc default callback RTS. Consume the return long from the explicit
// stack, preserve all other registers and memory, and emit no MMIO. This is
// only the known default callback, not an implementation of arbitrary targets.
bool return_default_irq_callback(const std::vector<std::uint8_t>& stack,
                                 std::uint32_t stack_base,InterruptRegisters& registers,
                                 IrqEnvelopeResult& result,
                                 std::vector<VideoPortWrite>& ports,std::string& error);

// Raster IRQ29c: inactive ->2d6 before RTE with acknowledge2; active saves
// only A5 and VRAM address, then calls RAM10000a (return2b6). Entry SP-10
// must fit the external stack. Unlike20c, this path does not save all registers.
bool begin_raster_irq(std::vector<std::uint8_t>& ram,
                      std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                      InterruptRegisters& registers,IrqEnvelopeResult& result,
                      std::vector<VideoPortWrite>& ports,std::string& error);
// Native2b6 ->2cc before RTE. InputSP follows callback RTS. Restore VRAM/A5
// from6 stack bytes, preserve all other callback register changes; no stack writes.
bool finish_raster_irq(std::vector<std::uint8_t>& ram,
                       std::vector<std::uint8_t>& stack,std::uint32_t stack_base,
                       InterruptRegisters& registers,IrqEnvelopeResult& result,
                       std::vector<VideoPortWrite>& ports,std::string& error);

}
#endif

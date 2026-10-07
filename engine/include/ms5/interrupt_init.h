#ifndef MS5_INTERRUPT_INIT_H
#define MS5_INTERRUPT_INIT_H
#include <cstdint>
#include <string>
#include <vector>
namespace ms5 {
// Native c42 with A5=108000. Initializes the frame signal/control bytes and
// empty task cursor. Does not clear saved task data or the latched video byte.
// Exact64KiB RAM; failure preserves RAM.
bool initialize_interrupt_state(std::vector<std::uint8_t>& ram,std::string& error);
// Native3dce with A5=108000. Clear4d91.bit4 and install3dcc RTS in both IRQ
// callback slots. A0 becomes3dcc; other registers/flags are outside this API.
// Failure preserves RAM and A0.
bool initialize_irq_callbacks(std::vector<std::uint8_t>& ram,std::uint32_t& a0,std::string& error);
}
#endif

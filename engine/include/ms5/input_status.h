#ifndef MS5_INPUT_STATUS_H
#define MS5_INPUT_STATUS_H
#include "ms5/input_sampler.h"
namespace ms5 {
// Native b68 status processing. Requires the full b58..c58 lookup window.
// Models RAM only. Failure preserves RAM.
bool update_input_status(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& table, std::string& error);
// Native 31d6 followed by b68, transactional across both calls.
bool step_input(std::vector<std::uint8_t>& ram, const FixedDataResource& streams,
                const FixedDataResource& table, const InputPortSamples& ports,
                std::uint8_t& read_count, std::string& error);
}
#endif

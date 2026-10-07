#ifndef MS5_INPUT_SAMPLER_H
#define MS5_INPUT_SAMPLER_H
#include "ms5/fixed_data_resource.h"
namespace ms5 {
// Raw active-low byte reads in original bus order. Mode zero reads P1/P2 twice.
struct InputPortSamples {
    std::uint8_t system, player1_raw, player2_raw, player1_game, player2_game;
};
// Native 3162 with ROM selector 000180 == 0. Selectors 0/1 start replay;
// other unsigned words select hardware input without clearing replay state.
// Failure preserves RAM; CPU register outputs are outside this API.
bool initialize_input(std::vector<std::uint8_t>& ram, const FixedDataResource& streams,
                      std::uint16_t selector, std::string& error);
// Native 31d6 with ROM selector 000180 == 0. Models RAM and consumed reads,
// optional style is incoming/outgoing D1.word, not a complete CPU register set.
// Failure preserves RAM, read_count and style.
bool sample_input(std::vector<std::uint8_t>& ram, const FixedDataResource& streams,
                  const InputPortSamples& ports, std::uint8_t& read_count,
                  std::string& error, std::uint16_t* style = NULL);
}
#endif

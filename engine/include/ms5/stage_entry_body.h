#ifndef MS5_STAGE_ENTRY_BODY_H
#define MS5_STAGE_ENTRY_BODY_H
#include "ms5/stage_frame.h"
namespace ms5 {
struct StageEntryBodyState {
    StageFrameState frame;
    std::uint32_t a5;
    unsigned int phase;
    StageEntryBodyState() : a5(0x108000), phase(0) {}
};
// Native47a94 initialization followed by the tail480bc frame. A5=108000.
// phase0 starts with canonical inactive frame state; phase1 resumes only a
// captured frame wait. phase2 is complete and rejects subsequent calls.
// Live aligned RAM/unique fixed windows supply record and indirection reads.
// A7, call-stack writes, CCR, CPU cycles and physical RAM mirroring are outside
// this API; differential fixtures use a separate oracle stack, without RAM masks.
// Failure preserves RAM/state/ports/external_reads; success replaces ports
// and external_reads with effects produced by this call alone.
bool step_stage_entry_body(std::vector<std::uint8_t>& ram,
    const FixedDataResource& tables, const std::vector<FixedDataResource>& windows,
    StageEntryBodyState& state, std::uint8_t external_status,
    std::uint8_t& external_reads, std::vector<VideoPortWrite>& ports,
    std::string& error);
}
#endif

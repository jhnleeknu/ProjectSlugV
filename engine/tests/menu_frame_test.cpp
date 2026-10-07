#include "ms5/menu_frame.h"
#include "ms5/menu_header.h"

#include <cassert>
#include <iostream>

namespace {

void put(std::vector<std::uint8_t>& data, std::size_t at, std::uint32_t value) {
    for (unsigned int index = 0U; index < 4U; ++index) {
        data[at + index] = static_cast<std::uint8_t>(value >> (24U - index * 8U));
    }
}

ms5::FixedDataResource menu_resource(std::uint32_t callback) {
    ms5::FixedDataResource menu;
    menu.source_cpu_address = menu.source_rom_offset = 0x200U;
    menu.data.assign(32U, 0U);
    put(menu.data, 0U, 0x21eU);
    put(menu.data, 6U, 0x9430U);
    put(menu.data, 16U, 0x21eU);
    put(menu.data, 20U, callback);
    put(menu.data, 26U, 0xffffffffU);
    menu.data[30U] = 'A';
    return menu;
}

std::vector<std::uint8_t> active_ram() {
    std::vector<std::uint8_t> ram(65536U, 0U);
    put(ram, 0x7f0eU, 0x107efeU);
    put(ram, 0x7f12U, 0x107efeU);
    put(ram, 0x7f16U, 0x3650U);
    put(ram, 0x7efeU, 0x200U);
    ram[0x7f02U] = 3U; // Slot height.
    ram[0x7f04U] = 1U; // Item count.
    ram[0x7f09U] = 5U; // Slot width.
    ram[0x7f0aU] = 3U; // Target height.
    ram[0x7f0cU] = 255U; // No pending event.
    return ram;
}

void fails_preserving_outputs(std::vector<std::uint8_t>& ram,
                              const ms5::FixedDataResource& menu,
                              std::uint32_t stack,
                              const std::string& expected_error) {
    const std::vector<std::uint8_t> before = ram;
    ms5::MenuFrameResult result;
    result.status = 19;
    result.external_jump = 0x123456U;
    result.line = 0x4567U;
    std::vector<ms5::VideoPortWrite> writes(1U);
    writes[0U].address = 0x3c0002U;
    writes[0U].size = 2U;
    writes[0U].value = 0x89abU;
    std::string error;
    std::uint32_t d1=0xabcd1234U, d3=0x98767123U;
    assert(!ms5::step_menu_frame(ram, menu, 0x7123U, stack, result, writes, error,
                                NULL,NULL,&d1,&d3));
    assert(d1==0xabcd1234U && d3==0x98767123U);
    assert(ram == before);
    assert(result.status == 19 && result.external_jump == 0x123456U &&
           result.line == 0x4567U);
    assert(writes.size() == 1U && writes[0U].address == 0x3c0002U &&
           writes[0U].size == 2U && writes[0U].value == 0x89abU);
    assert(!error.empty());
    if (!expected_error.empty()) {
        assert(error == expected_error);
    }
}

} // namespace

int main() {
    const ms5::FixedDataResource unsupported = menu_resource(0x1234U);
    std::vector<std::uint8_t> ram = active_ram();
    ram[0x7f0cU] = 0U;
    ram[0x7df0U] = 1U;
    ram[0x0012U] = 2U;
    ram[0xfd82U] = 0U;
    ram[0x4cb5U] = 2U;
    ram[0xfdb6U] = 1U;
    // Prove the valid header callback changes RAM before the pending row fails.
    std::vector<std::uint8_t> header_ram = ram;
    std::uint32_t a2 = 0x107efeU;
    std::string error;
    assert(ms5::update_menu_header(header_ram, a2, error));
    assert(header_ram != ram && header_ram[0x7f1bU] == 2U &&
           header_ram[0x7dfbU] == 1U);
    fails_preserving_outputs(ram, unsupported, 0x120000U,
                            "menu event callback has not been reconstructed");

    const ms5::FixedDataResource supported = menu_resource(0x9488U);
    ram = active_ram();
    put(ram, 0x7f16U, 0x9332U);
    ram[0x7f0dU] = 1U; // Active redraw clears this flag before drawing fails.
    fails_preserving_outputs(ram, supported, 0x120000U,
                            "menu renderer CPU0x009332 requires the font resource");

    ram = active_ram();
    fails_preserving_outputs(ram, supported, 0x120001U, "");
    fails_preserving_outputs(ram, supported, 0x1100feU, "");
    fails_preserving_outputs(ram, supported, 0xfffffeU, "");
    ram.resize(5U);
    fails_preserving_outputs(ram, supported, 0x120000U, "");

    ram = active_ram();
    put(ram, 0x7f0eU, 0x107f0eU);
    put(ram, 0x7f12U, 0xdeadbeefU);
    const std::vector<std::uint8_t> before = ram;
    ms5::MenuFrameResult result;
    result.status = 19;
    result.external_jump = 0x123456U;
    result.line = 0x4567U;
    std::vector<ms5::VideoPortWrite> writes(1U);
    error = "old error";
    std::uint32_t d1=0xabcd1234U, d3=0x98767123U;
    assert(ms5::step_menu_frame(ram, supported, 0x7123U, 0x120000U,
                                result, writes, error,NULL,NULL,&d1,&d3));
    assert(d1==0xabcd1234U && d3==0x98767123U);
    assert(ram == before && writes.empty() && error.empty());
    assert(result.status == -1 && result.external_jump == 0U && result.line == 0x7123U);
    // Active idle input clears D1 fully, then supplies the enabled P2 byte.
    ram=active_ram();
    ram[0x7f0bU]=2U;
    d1=0xabcd1234U;d3=0x98767123U;
    assert(ms5::step_menu_frame(ram,supported,0x7123U,0x120000U,
                                result,writes,error,NULL,NULL,&d1,&d3));
    assert(d1==0U && d3==0x98767123U && writes.empty());
    ram[0x4cc0U]=0x80U; // No menu action, but the byte remains in D1.
    d1=0xabcd1234U;
    assert(ms5::step_menu_frame(ram,supported,0x7123U,0x120000U,
                                result,writes,error,NULL,NULL,&d1,&d3));
    assert(d1==0x80U && d3==0x98767123U && writes.empty());
    const std::vector<std::uint8_t> idle_before=ram;
    const ms5::MenuFrameResult idle_result=result;
    writes.resize(1U);writes[0].value=123U;
    assert(!ms5::step_menu_frame(ram,supported,0x7124U,0x120000U,
                                 result,writes,error,NULL,NULL,&d1,&d3));
    assert(ram==idle_before && d1==0x80U && d3==0x98767123U);
    assert(result.status==idle_result.status && result.line==idle_result.line &&
           result.external_jump==idle_result.external_jump && writes.size()==1U && writes[0].value==123U);
    // Closing a zero-height head still writes the base cursor lowword.
    ram=active_ram();ram[0x7f02U]=0U;ram[0x7f1bU]=2U;
    ram[0x7f07U]=4U;ram[0x7f08U]=8U;
    d1=0xabcd1234U;d3=0x98767123U;
    assert(ms5::step_menu_frame(ram,supported,0x7123U,0x120000U,
                                result,writes,error,NULL,NULL,&d1,&d3));
    assert(d3==0x98767088U && result.line==0x7088U && result.status==-1 && writes.empty());
    std::cout << "Menu frame empty head, stack bounds and late-error rollback passed\n";
}

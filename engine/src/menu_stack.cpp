#include "ms5/menu_stack.h"
#include "ms5/menu_init.h"
#include "ms5/menu_border.h"
#include "ms5/menu_text.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_u32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at]) << 24) |
           (static_cast<std::uint32_t>(ram[at+1U]) << 16) |
           (static_cast<std::uint32_t>(ram[at+2U]) << 8) | ram[at+3U];
}
void put_u32(std::vector<std::uint8_t>& ram, std::size_t at, std::uint32_t value) {
    for (unsigned int i = 0; i < 4U; ++i) {
        ram[at+i] = static_cast<std::uint8_t>(value >> (24U-i*8U));
    }
}

}
bool push_menu(std::vector<std::uint8_t>& ram,
               const FixedDataResource& resource, std::uint32_t descriptor_address,
               std::uint16_t x, std::uint16_t y, std::uint16_t initial_line,
               std::vector<VideoPortWrite>& writes, std::string& error,
               const FixedDataResource* font,
               const StageGroupMenuContext* stage_context,
               std::uint16_t* final_line,std::uint32_t* d1,std::uint32_t* d3) {
    if((d1!=NULL && static_cast<std::uint16_t>(*d1)!=y) ||
       (d3!=NULL && static_cast<std::uint16_t>(*d3)!=initial_line)) {
        error="menu push Y/line must match D1/D3 low words";return false;
    }
    if (ram.size() != 65536U) {
        error = "menu stack requires exactly 65536 RAM bytes";
        return false;
    }
    const std::uint32_t head = read_u32(ram, 0x7f0eU);
    if (head <= 0x107e0eU || head > 0x107f0eU || (head-0x107e0eU)%16U != 0U) {
        error = "menu stack is full or its head is invalid";
        return false;
    }
    const std::uint32_t saved_current = read_u32(ram, 0x7f12U);
    const std::uint32_t new_head = head-16U;
    const std::size_t slot = new_head-0x100000U;
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        put_u32(candidate, 0x7f0eU, new_head);
        put_u32(candidate, 0x7f12U, head);
        // The original suppresses occlusion by the as-yet-uninitialized slot.
        candidate[slot+9U] = candidate[slot+10U] = 255U;
        candidate[slot+11U] = candidate[slot+12U] = 0U;
        std::uint16_t line = initial_line;
        const std::uint32_t incoming_d1=d1!=NULL?*d1:y;
        std::uint32_t pending_d1=incoming_d1;
        std::uint32_t pending_d3=d3!=NULL?*d3:initial_line;
        if (head < 0x107f0eU) {
            std::vector<FixedWrite> border;
            if (!trace_menu_border(candidate, resource, border, error, &pending_d3)) {
                return false;
            }
            for (std::size_t i = 0; i < border.size(); ++i) {
                VideoPortWrite write;
                write.address = 0x3c0000U;
                write.size = 4U;
                write.value = (static_cast<std::uint32_t>(border[i].address)<<16) | border[i].value;
                pending.push_back(write);
            }
            line=static_cast<std::uint16_t>(pending_d3);
            std::vector<VideoPortWrite> text;
            if (!draw_menu_text(candidate, resource, true, line, text, error,
                                &line, font, stage_context, 0x3650U, &pending_d1, &pending_d3)) {
                return false;
            }
            pending.insert(pending.end(), text.begin(), text.end());
        }
        put_u32(candidate, 0x7f12U, new_head);
        std::uint16_t final_style=y;
        if (!configure_menu_slot(candidate, resource, new_head, descriptor_address,
                                  x, y, line, error, &line, &final_style, &pending_d3)) {
            return false;
        }
        // a104 restores the entry D1 before child title measurement.
        pending_d1=(incoming_d1&0xffff0000U)|final_style;
        candidate[0x7f1bU] = 1U;
        put_u32(candidate, 0x7f12U, saved_current);
        ram.swap(candidate);
        writes.swap(pending);
        if (final_line != NULL) *final_line = line;
        if(d1!=NULL)*d1=pending_d1;
        if(d3!=NULL)*d3=pending_d3;
    } catch (const std::bad_alloc&) {
        error = "cannot allocate menu stack output";
        return false;
    }
    error.clear();
    return true;
}
}

#include "ms5/menu_event.h"
#include "ms5/menu_border.h"
#include "ms5/menu_descriptor.h"
#include "ms5/menu_stack.h"
#include "ms5/object_restart.h"
#include <new>
namespace ms5 {
namespace {
std::uint32_t read_u32(const std::vector<std::uint8_t>& ram, std::size_t at) {
    return (static_cast<std::uint32_t>(ram[at])<<24) |
        (static_cast<std::uint32_t>(ram[at+1U])<<16) |
        (static_cast<std::uint32_t>(ram[at+2U])<<8) | ram[at+3U];
}
bool supported(std::uint32_t callback) {
    return callback==0U || callback==0x9488U || callback==0x949aU ||
           callback==0x94b8U || callback==0x94d6U || callback==0x950cU ||
           callback==0x9532U;
}
void close_menu(std::vector<std::uint8_t>& ram, MenuEventResult& result) {
    ram[0x7f1bU]=2U;
    result.a2=read_u32(ram,0x7f0eU);
}
void mark_exit(std::vector<std::uint8_t>& ram) {
    ram[0x7dfaU]=0U;
    ram[0x7dfbU]=1U;
}
}
bool dispatch_menu_event(std::vector<std::uint8_t>& ram,
                         const FixedDataResource& resource,
                         std::uint16_t event, std::uint16_t initial_line,
                         MenuEventResult& result,
                         std::vector<VideoPortWrite>& writes, std::string& error) {
    bool covered=false;
    if (!menu_position_occluded(ram,0x7000U,covered,error)) return false;
    const std::uint32_t current=read_u32(ram,0x7f12U);
    const std::size_t slot=current-0x100000U;
    MenuDescriptor descriptor;
    if (!decode_menu_descriptor(resource,read_u32(ram,slot),descriptor,error)) return false;
    const std::uint8_t index=ram[slot+8U];
    if (index>=descriptor.items.size() || ram[slot+6U]!=descriptor.items.size()) {
        error="menu event requires a valid row and matching descriptor count";
        return false;
    }
    const std::uint32_t callback=descriptor.items[index].callback;
    if (!supported(callback)) {
        error="menu event callback has not been reconstructed";
        return false;
    }
    try {
        std::vector<std::uint8_t> candidate(ram);
        std::vector<VideoPortWrite> pending;
        MenuEventResult outcome;
        outcome.a2=current;
        if (callback!=0U) {
            if (event==7U && (callback==0x949aU || callback==0x94b8U)) {
                if (candidate[0x7dfaU]==0U && candidate[0x7dfbU]==1U) {
                    close_menu(candidate,outcome);
                }
            } else if (event==3U) {
                if (callback==0x9488U) {
                    close_menu(candidate,outcome);
                } else if (callback==0x9532U) {
                    outcome.external_jump=0xc00444U;
                } else if (callback==0x950cU) {
                    if (!restart_static_object(candidate,0x1008e4U,0xca22U,3U,pending,error)) return false;
                    mark_exit(candidate);
                    close_menu(candidate,outcome);
                } else {
                    const std::uint32_t child=callback==0x949aU ? 0x958aU :
                                              callback==0x94b8U ? 0x978aU : 0x99eeU;
                    const unsigned int padding=(descriptor.flags&14U)!=0U ? 1U : 3U;
                    const std::uint8_t x=static_cast<std::uint8_t>(candidate[slot+9U]+padding);
                    const std::uint8_t y=static_cast<std::uint8_t>(candidate[slot+10U]+1U+index);
                    if (!push_menu(candidate,resource,child,x,y,initial_line,pending,error)) return false;
                    outcome.a2=read_u32(candidate,0x7f0eU);
                }
            } else if (event==4U) {
                if (callback!=0x950cU && callback!=0x9532U) mark_exit(candidate);
                close_menu(candidate,outcome);
            }
        }
        ram.swap(candidate);
        writes.swap(pending);
        result=outcome;
    } catch (const std::bad_alloc&) {
        error="cannot allocate menu event state";
        return false;
    }
    error.clear();
    return true;
}
}

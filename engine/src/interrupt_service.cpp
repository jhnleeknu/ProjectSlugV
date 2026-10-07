#include "ms5/interrupt_service.h"
#include "ms5/credit_request.h"
#include "ms5/palette_transfer.h"
#include "ms5/column_control.h"
#include "ms5/sprite_refresh_queue.h"
namespace ms5 {
namespace {
void append(std::vector<VideoPortWrite>& target,const std::vector<VideoPortWrite>& source) {
    target.insert(target.end(),source.begin(),source.end());
}
void emit_byte(std::vector<VideoPortWrite>& ports,std::uint32_t address,std::uint32_t value) {
    VideoPortWrite write;write.size=1;write.address=address;write.value=value&255U;
    ports.push_back(write);
}
bool finish_service(std::vector<std::uint8_t>& ram,std::uint32_t d0,
                    std::uint8_t external_status,std::uint8_t sound_status,
                    InterruptServiceResult& result,std::vector<VideoPortWrite>& ports,
                    std::string& error) {
    if((ram[0xf001]&16U)!=0) emit_byte(ports,0x3a0001,d0);
    std::vector<VideoPortWrite> sound_ports;
    if(!step_sound(ram,external_status,sound_status,result.sound,result.sound_reads,sound_ports,error)) return false;
    append(ports,sound_ports);
    if(result.sound.kind!=0) result.phase=InterruptServiceSoundWait;
    else {ram[0x19]=0;result.phase=InterruptServiceComplete;}
    return true;
}
bool dispatch(std::vector<std::uint8_t>& ram,InterruptRegisters& registers,
              InterruptServiceResult& result,std::vector<VideoPortWrite>& ports,std::string& error) {
    InterruptTaskResult task;std::vector<VideoPortWrite> task_ports;
    if(!resume_interrupt_tasks(ram,registers,task,task_ports,error)) return false;
    append(ports,task_ports);
    if(task.restored) {
        result.phase=InterruptServiceTask;result.task=task;result.task_registers=registers;
    }
    return true;
}
}
bool begin_interrupt_service(std::vector<std::uint8_t>& ram,
                             std::vector<std::uint8_t>& palette0,
                             std::vector<std::uint8_t>& palette1,
                             std::uint8_t& display_bank,
                             const std::vector<CompositionResource>& resources,
                             const InterruptRegisters& registers,
                             std::uint8_t external_status,std::uint8_t sound_status,
                             InterruptServiceResult& result,
                             std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536U || registers.a[5]!=0x108000U) {
        error="interrupt service requires 64KiB RAM and A5=108000";return false;
    }
    std::vector<std::uint8_t> candidate=ram;
    InterruptServiceResult next;std::vector<VideoPortWrite> hardware;
    const bool busy=(candidate[0x19]&128U)!=0;
    candidate[0x19]|=128U;
    if(busy) {
        next.phase=InterruptServiceReentrant;
        ram.swap(candidate);result=next;ports.swap(hardware);error.clear();return true;
    }
    InterruptRegisters current=registers;
    if(candidate[0x16]!=255U) {++candidate[0x16];emit_byte(hardware,0x300001,current.d[0]);}
    if(!process_credit_request(candidate,current.d[0],error)) return false;
    const bool render=(candidate[0x1b]&128U)!=0;
    std::vector<std::uint8_t> bank0,bank1;std::uint8_t bank=display_bank;
    if(render) {
        if(&ram==&palette0 || &ram==&palette1 || &palette0==&palette1) {
            error="interrupt palette banks and RAM must be distinct";return false;
        }
        bank0=palette0;bank1=palette1;
        std::vector<VideoPortWrite> part;
        if(!transfer_palette_banks_traced(candidate,bank0,bank1,bank,current.d[0],part,error)) return false;
        append(hardware,part);
        if((candidate[0xf001]&16U)!=0) emit_byte(hardware,0x3a0011,current.d[0]);
        if(!refresh_scene_columns(candidate,current.d[0],part,error)) return false;
        append(hardware,part);
        std::vector<SpriteWrite> sprite_writes;bool processed=false;
        if(!refresh_sprite_queue(candidate,resources,sprite_writes,processed,error,&current.d[0],&part)) return false;
        append(hardware,part);
        if(!dispatch(candidate,current,next,hardware,error)) return false;
    }
    if(next.phase!=InterruptServiceTask &&
       !finish_service(candidate,current.d[0],external_status,sound_status,next,hardware,error)) return false;
    ram.swap(candidate);
    if(render) {palette0.swap(bank0);palette1.swap(bank1);display_bank=bank;}
    result=next;ports.swap(hardware);error.clear();return true;
}
bool continue_interrupt_service(std::vector<std::uint8_t>& ram,
                                const InterruptRegisters& registers,
                                std::uint8_t external_status,std::uint8_t sound_status,
                                InterruptServiceResult& result,
                                std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536U) {error="interrupt continuation requires 64KiB RAM";return false;}
    std::vector<std::uint8_t> candidate=ram;InterruptRegisters current=registers;
    InterruptServiceResult next;std::vector<VideoPortWrite> hardware;
    if(!dispatch(candidate,current,next,hardware,error)) return false;
    if(next.phase!=InterruptServiceTask &&
       !finish_service(candidate,current.d[0],external_status,sound_status,next,hardware,error)) return false;
    ram.swap(candidate);result=next;ports.swap(hardware);error.clear();return true;
}
bool resume_interrupt_service_sound(std::vector<std::uint8_t>& ram,
                                    std::uint8_t sound_status,InterruptServiceResult& result,
                                    std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536U || result.phase!=InterruptServiceSoundWait) {
        error="interrupt sound resume requires a suspended sound producer";return false;
    }
    std::vector<std::uint8_t> candidate=ram;InterruptServiceResult next;
    next.sound=result.sound;std::vector<VideoPortWrite> hardware;
    if(!resume_sound(candidate,sound_status,next.sound,next.sound_reads,hardware,error)) return false;
    if(next.sound.kind!=0) next.phase=InterruptServiceSoundWait;
    else {candidate[0x19]=0;next.phase=InterruptServiceComplete;}
    ram.swap(candidate);result=next;ports.swap(hardware);error.clear();return true;
}
}

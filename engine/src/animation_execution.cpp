#include "ms5/animation_execution.h"
#include "ms5/object_sound_lookup.h"
#include <new>
namespace ms5 {
namespace {
void byte(std::uint32_t& r,std::uint32_t value) {r=(r&0xffffff00U)|(value&255U);}
void word(std::uint32_t& r,std::uint32_t value) {r=(r&0xffff0000U)|(value&65535U);}
void swap(std::uint32_t& r) {r=(r<<16)|(r>>16);}
bool negative_word(std::uint32_t value) {return (value&0x8000U)!=0;}
std::uint32_t extend_word(std::uint32_t value) {return (value&0x8000U)?(value|0xffff0000U):(value&65535U);}
int signed_word(std::uint32_t value) {return (value&0x8000U)?static_cast<int>(value&65535U)-65536:static_cast<int>(value&65535U);}
bool valid(const AnimationExecutionState& s) {
    const bool inactive=s.callback_saved_a0==0 && s.callback_sound_phase==0 &&
        s.callback_saved_low==0 && !s.callback_waiting;
    if(s.phase==0)return s.saved_list_end==0 && inactive && !s.sprite.waiting && s.saved_a0==0 && s.saved_a1==0 && s.saved_bank==0;
    if(s.phase==1)return s.saved_list_end==0 && inactive && s.sprite.waiting;
    if(s.phase==3)return inactive && s.sprite.waiting;
    return (s.phase==2 || (s.phase==4 && s.saved_bank==0 && s.callback_saved_a0==0)) &&
        s.saved_list_end==0 && !s.sprite.waiting && s.callback_waiting &&
        (s.callback_sound_phase==1 || s.callback_sound_phase==2);
}
bool ram_span(std::uint32_t base,int displacement,unsigned int size,std::size_t& at,std::string& error) {
    const std::int64_t address=static_cast<std::int64_t>(base)+displacement;
    if(address<0x100000 || address+size>0x110000 || (size>1 && (address&1))) {
        error="animation requires aligned complete reached RAM span";return false;
    }
    at=static_cast<std::size_t>(address-0x100000);return true;
}
bool read_ram(const std::vector<std::uint8_t>& ram,std::uint32_t base,int displacement,
    unsigned int size,std::uint32_t& value,std::string& error) {
    std::size_t at=0;if(!ram_span(base,displacement,size,at,error))return false;
    value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|ram[at+i];return true;
}
bool write_ram(std::vector<std::uint8_t>& ram,std::uint32_t base,int displacement,
    unsigned int size,std::uint32_t value,std::string& error) {
    std::size_t at=0;if(!ram_span(base,displacement,size,at,error))return false;
    for(unsigned int i=0;i<size;++i)ram[at+i]=static_cast<std::uint8_t>(value>>(8*(size-i-1)));return true;
}
bool read_script(const std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    std::uint32_t address,unsigned int size,std::uint32_t& value,std::string& error) {
    if((size>1 && (address&1U)) || static_cast<std::uint64_t>(address)+size>0x100000000ULL) {
        error="unaligned or overflowing animation script read";return false;
    }
    if(address>=0x100000 && address<0x110000)return read_ram(ram,address,0,size,value,error);
    const std::vector<std::uint8_t>* data=NULL;std::size_t at=0;unsigned int matches=0;
    for(std::size_t i=0;i<scripts.size();++i) {
        const AnimationResource& w=scripts[i];const std::uint32_t start=w.source_cpu_address;
        if(start>=0x100000 || w.source_rom_offset!=start || w.data.empty() || w.data.size()>0x100000-start)continue;
        const std::uint64_t end=static_cast<std::uint64_t>(start)+w.data.size();
        if(address<end && static_cast<std::uint64_t>(address)+size>start) {
            ++matches;if(address>=start && static_cast<std::uint64_t>(address)+size<=end) {data=&w.data;at=address-start;}
        }
    }
    if(matches!=1 || data==NULL) {error="missing, ambiguous or partial fixed animation script read";return false;}
    value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|(*data)[at+i];return true;
}
bool next(const std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    SceneMapTransferState& r,unsigned int size,std::uint32_t& value,std::string& error) {
    if(!read_script(ram,scripts,r.a[1],size,value,error))return false;
    r.a[1]+=size;return true;
}
bool read_data(const std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    std::int64_t address,unsigned int size,std::uint32_t& value,std::string& error) {
    if(address<0 || address+size>0x100000000LL || (size>1 && (address&1))) {
        error="unaligned or overflowing animation data read";return false;
    }
    if(address>=0x100000 && address<0x110000)return read_ram(ram,static_cast<std::uint32_t>(address),0,size,value,error);
    const std::vector<std::uint8_t>* data=NULL;std::size_t at=0;unsigned int matches=0;
    for(std::size_t i=0;i<windows.size();++i) {
        const FixedDataResource& w=windows[i];const std::uint32_t start=w.source_cpu_address;
        if(start>=0x100000 || w.source_rom_offset!=start || w.data.empty() || w.data.size()>0x100000-start)continue;
        const std::int64_t end=static_cast<std::int64_t>(start)+w.data.size();
        if(address<end && address+size>start) {
            ++matches;if(address>=start && address+size<=end) {data=&w.data;at=static_cast<std::size_t>(address-start);}
        }
    }
    if(matches!=1 || data==NULL) {error="missing, ambiguous or partial fixed animation data read";return false;}
    value=0;for(unsigned int i=0;i<size;++i)value=(value<<8)|(*data)[at+i];return true;
}
void pvc(AnimationExecutionState& s,std::vector<VideoPortWrite>& ports,std::uint32_t value) {
    VideoPortWrite p;p.size=2;p.address=0x2ffff2;p.value=value&65535U;ports.push_back(p);
    p.address=0x2ffff0;p.value=0;ports.push_back(p);
    // The first device write masks ff9 before the second write completes the pair.
    s.current_bank_base=0x100000U+((value&0x7fffU)<<8);
}
bool zero_bank(std::vector<std::uint8_t>& ram,AnimationExecutionState& s,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if(!write_ram(ram,s.a5,-0x7ff0,2,0,error))return false;pvc(s,ports,0x1000);return true;
}
bool epilogue(std::vector<std::uint8_t>& ram,AnimationExecutionState& s,bool& carry,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if(!zero_bank(ram,s,ports,error))return false;
    std::uint32_t& d7=s.sprite.registers.d[7];carry=(d7&1U)!=0;
    word(d7,((d7&65535U)>>1)|(d7&0x8000U));return true;
}
bool draw_return(std::vector<std::uint8_t>& ram,AnimationExecutionState& s,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;
    if(!write_ram(ram,s.a5,-0x7ff0,2,s.saved_bank,error))return false;
    const std::uint32_t d0=r.d[0]&65535U,d7=r.d[7]&65535U;std::uint32_t value=0;
    if(!read_ram(ram,s.a5,-0x7ff0,2,value,error))return false;
    word(r.d[7],value);word(r.d[0],r.d[7]);word(r.d[7],r.d[7]+1U);
    word(r.d[7],r.d[7]<<8);word(r.d[7],r.d[7]<<4);pvc(s,ports,r.d[7]);
    r.d[0]=extend_word(d0);r.d[7]=extend_word(d7);
    r.a[0]=s.saved_a0;r.a[1]=s.saved_a1;
    s.phase=0;s.saved_a0=0;s.saved_a1=0;s.saved_bank=0;return true;
}
bool draw(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    AnimationExecutionState& s,std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;std::uint32_t value=0;
    r.d[0]=0;r.d[5]=0;r.d[6]=0;
    if(!next(ram,scripts,r,1,value,error))return false;r.d[5]=value;
    if(!next(ram,scripts,r,1,value,error))return false;r.d[0]=value;
    if(!next(ram,scripts,r,1,value,error))return false;r.d[6]=value;
    if(!next(ram,scripts,r,4,value,error))return false;r.d[7]=value;
    if(r.d[7]==0x7ff800)return true;
    if(!read_ram(ram,s.a6,0x20,2,value,error))return false;word(r.d[7],r.d[7]|value);
    if(!read_ram(ram,r.a[0],4,1,value,error))return false;if(value&0x80U)return true;
    if(!read_ram(ram,s.a6,0x61,1,value,error))return false;
    if(value&8U) {if(!read_ram(ram,s.a5,-0x7ff1,1,value,error))return false;if(value&1U)return true;}
    if(!read_ram(ram,s.a6,0x12,4,value,error))return false;r.d[1]=value;
    word(r.d[0],(r.d[0]&0x80U)?r.d[0]|0xff00U:r.d[0]);
    word(r.d[6],(r.d[6]&0x80U)?r.d[6]|0xff00U:r.d[6]);
    unsigned int extend=r.d[5]&1U;byte(r.d[5],(r.d[5]&255U)>>1);word(r.d[6],r.d[6]*2U+extend);
    extend=r.d[5]&1U;byte(r.d[5],(r.d[5]&255U)>>1);word(r.d[0],r.d[0]*2U+extend);
    if(r.d[1]&1U)r.d[0]=0U-r.d[0];if(r.d[1]&2U)word(r.d[6],0U-r.d[6]);
    if(!read_ram(ram,s.a6,0x42,2,value,error))return false;word(r.d[0],r.d[0]+value);
    if(!read_ram(ram,s.a6,0x46,2,value,error))return false;word(r.d[6],r.d[6]+value);
    r.d[3]=0;if(!read_ram(ram,s.a6,0x53,1,value,error))return false;byte(r.d[2],value);
    extend=r.d[2]&1U;byte(r.d[2],(r.d[2]&255U)>>1);word(r.d[0],r.d[0]-extend);
    extend=r.d[2]&1U;byte(r.d[2],(r.d[2]&255U)>>1);word(r.d[6],r.d[6]-extend);
    swap(r.d[0]);word(r.d[0],r.d[6]);byte(r.d[4],r.d[5]);byte(r.d[4],r.d[4]&3U);byte(r.d[1],r.d[1]^r.d[4]);
    word(r.d[5],(r.d[5]&65535U)>>2);
    if((r.d[5]&65535U)>=10) {word(r.d[5],r.d[5]-10U);byte(r.d[1],r.d[1]^4U);}
    bool direct=false;
    if((r.d[5]&65535U)>=5)word(r.d[5],r.d[5]-5U);
    else {
        if(!read_ram(ram,s.a6,0x16,2,value,error))return false;word(r.d[4],value);
        const bool carry=(r.d[4]&1U)!=0;byte(r.d[4],((r.d[4]&255U)>>1)|(r.d[4]&0x80U));
        if(!(r.d[4]&0x80U) && carry) {byte(r.d[4],r.d[1]);word(r.d[1],r.d[4]);direct=true;}
    }
    if(!direct && (r.d[5]&65535U)<4) {
        byte(r.d[4],r.d[1]);
        if(!read_ram(ram,s.a6,0x19+static_cast<int>(r.d[5]&65535U),1,value,error))return false;
        byte(r.d[1],value);word(r.d[1],r.d[1]<<8);byte(r.d[1],r.d[4]);
    }
    if(!read_ram(ram,s.a6,0x1e,2,value,error))return false;word(r.d[5],value);
    if(s.a5!=0x108000) {error="animation sprite submit requires canonical A5=108000";return false;}
    s.saved_a0=r.a[0];s.saved_a1=r.a[1];
    if(!read_ram(ram,s.a5,-0x7ff0,2,value,error))return false;s.saved_bank=static_cast<std::uint16_t>(value);
    if(!zero_bank(ram,s,ports,error))return false;
    SpriteSubmitStatus status=SpriteAccepted;if(!execute_sprite_submit(ram,s.sprite,status,error))return false;
    if(s.sprite.waiting) {s.phase=1;return true;}
    return draw_return(ram,s,ports,error);
}
bool field_branch(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,AnimationExecutionState& s,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;std::uint32_t value=0;
    if(!next(ram,scripts,r,1,value,error))return false;byte(r.d[1],value?255U:0U);
    if(!next(ram,scripts,r,2,value,error))return false;word(r.d[0],value);word(r.d[0],r.d[0]*2U);
    r.a[2]=0x4a76c;
    if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[2])+signed_word(r.d[0]),2,value,error))return false;
    word(r.d[0],value);
    if(!next(ram,scripts,r,4,value,error))return false;r.d[7]=value;
    if(!read_ram(ram,s.a6,signed_word(r.d[0]),1,value,error))return false;
    byte(r.d[0],value?255U:0U);
    if((r.d[0]&255U)==(r.d[1]&255U))r.a[1]=r.d[7];
    r.d[6]=r.a[1];return write_ram(ram,r.a[0],0,4,r.d[6],error);
}
bool script_address(std::uint32_t base,int displacement,std::uint32_t& address,std::string& error) {
    const std::int64_t sum=static_cast<std::int64_t>(base)+displacement;
    if(sum<0 || sum>0xffffffffLL) {error="indexed animation script address overflows";return false;}
    address=static_cast<std::uint32_t>(sum);return true;
}
bool field_command(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,AnimationExecutionState& s,
    unsigned int opcode,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;std::uint32_t value=0,address=0;
    if(opcode==0x34 || opcode==0x38) {
        if(!script_address(r.a[1],1,r.a[1],error))return false;
        if(opcode==0x34)r.d[0]=0;
        if(!next(ram,scripts,r,2,value,error))return false;
        if(!write_ram(ram,s.a6,opcode==0x34?0x70:0x20,2,value,error))return false;
    } else if(opcode==0x18) {
        if(!next(ram,scripts,r,1,value,error))return false;byte(r.d[0],value);
        if(!next(ram,scripts,r,2,value,error))return false;word(r.d[1],value);word(r.d[1],r.d[1]*2U);
        r.a[2]=0x4a76c;
        if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[2])+signed_word(r.d[1]),2,value,error))return false;
        word(r.d[1],value);
        if(!write_ram(ram,s.a6,signed_word(r.d[1]),1,r.d[0],error))return false;
    } else {
        r.d[0]=0;if(!next(ram,scripts,r,1,value,error))return false;r.d[0]=value;word(r.d[0],r.d[0]*2U);
        r.a[2]=0x4a76c;
        if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[2])+signed_word(r.d[0]),2,value,error))return false;
        word(r.d[0],value);
        if(opcode==0x1c || opcode==0x20) {
            const unsigned int size=opcode==0x1c?2:4;
            if(!next(ram,scripts,r,size,value,error))return false;
            if(size==2)word(r.d[1],value);else r.d[1]=value;
            if(!write_ram(ram,s.a6,signed_word(r.d[0]),size,r.d[1],error))return false;
        } else if(opcode==0x24) {
            if(!read_ram(ram,s.a6,signed_word(r.d[0]),1,value,error))return false;
            if(!write_ram(ram,s.a6,signed_word(r.d[0]),1,value-1U,error))return false;
        } else {
            if(!next(ram,scripts,r,2,value,error))return false;word(r.d[2],value);
            if(!read_ram(ram,s.a6,signed_word(r.d[0]),1,value,error))return false;
            byte(r.d[0],value);word(r.d[0],r.d[0]*2U);
            if((r.d[0]&65535U)<(r.d[2]&65535U)) {
                if(!script_address(r.a[1],signed_word(r.d[0]),address,error))return false;
                if(!read_script(ram,scripts,address,2,value,error))return false;
                if(!script_address(r.a[1],signed_word(value),r.a[1],error))return false;
            }
            if(!script_address(r.a[1],signed_word(r.d[2]),r.a[1],error))return false;
        }
    }
    // Original4a276 follows every field command, including relative2c.
    r.d[6]=r.a[1];return write_ram(ram,r.a[0],0,4,r.d[6],error);
}
bool indexed_draw(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,AnimationExecutionState& s,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;std::uint32_t value=0,end=0,selected=0;
    r.d[0]=0;
    if(!next(ram,scripts,r,1,value,error))return false;r.d[0]=value;word(r.d[0],r.d[0]*2U);
    r.a[2]=0x4a76c;
    if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[2])+signed_word(r.d[0]),2,value,error))return false;
    word(r.d[0],value);
    if(!next(ram,scripts,r,2,value,error))return false;word(r.d[1],value);
    if(!script_address(r.a[1],signed_word(r.d[1]),end,error))return false;
    if(!read_ram(ram,s.a6,signed_word(r.d[0]),1,value,error))return false;
    byte(r.d[0],value);word(r.d[0],r.d[0]<<3);
    if((r.d[0]&65535U)<(r.d[1]&65535U)) {
        if(!script_address(r.a[1],signed_word(r.d[0]),selected,error))return false;
        if(!read_script(ram,scripts,selected,1,value,error))return false;
        if(value!=4) {error="indexed animation selected opcode is not04";return false;}
        if(!script_address(selected,1,r.a[1],error))return false;
        if(!draw(ram,scripts,s,ports,error))return false;
        if(s.sprite.waiting) {s.phase=3;s.saved_list_end=end;return true;}
    }
    // Original4a270 restores only the PEA cursor, bypassing4a276.
    r.a[1]=end;return true;
}
bool direct_sound(std::vector<std::uint8_t>& ram,AnimationExecutionState& s,
    std::uint8_t external_status,std::uint32_t& external_reads,std::string& error) {
    if(s.a5!=0x108000) {error="direct animation sound requires canonical A5=108000";return false;}
    SoundWordExecutionState sound;sound.byte.registers=s.sprite.registers;
    if(s.phase==4) {
        sound.phase=s.callback_sound_phase;sound.saved_low=s.callback_saved_low;sound.byte.waiting=s.callback_waiting;
    }
    std::uint8_t reads=0;if(!execute_sound_word(ram,sound,external_status,reads,error))return false;
    external_reads+=reads;s.sprite.registers=sound.byte.registers;
    s.callback_sound_phase=sound.phase;s.callback_saved_low=sound.saved_low;s.callback_waiting=sound.byte.waiting;
    if(sound.phase!=0) {s.phase=4;return true;}
    // Original4a2ec restores LONG A0/A1 only; no bank or MOVEM.W path.
    SceneMapTransferState& r=s.sprite.registers;r.a[0]=s.saved_a0;r.a[1]=s.saved_a1;
    s.saved_a0=0;s.saved_a1=0;s.phase=0;r.d[6]=r.a[1];
    return write_ram(ram,r.a[0],0,4,r.d[6],error);
}
bool sound_callback(std::vector<std::uint8_t>& ram,const std::vector<FixedDataResource>& windows,
    AnimationExecutionState& s,std::uint8_t external_status,std::uint32_t& external_reads,std::string& error) {
    ObjectSoundLookupState inner;inner.sound.byte.registers=s.sprite.registers;inner.a5=s.a5;inner.a6=s.a6;
    if(s.phase==2) {
        inner.phase=1;inner.saved_a0=s.callback_saved_a0;inner.sound.phase=s.callback_sound_phase;
        inner.sound.saved_low=s.callback_saved_low;inner.sound.byte.waiting=s.callback_waiting;
    }
    std::uint8_t reads=0;
    if(!execute_object_sound_lookup(ram,windows,inner,external_status,reads,error))return false;
    external_reads+=reads;s.sprite.registers=inner.sound.byte.registers;s.a5=inner.a5;s.a6=inner.a6;
    s.callback_saved_a0=inner.saved_a0;s.callback_sound_phase=inner.sound.phase;
    s.callback_saved_low=inner.sound.saved_low;s.callback_waiting=inner.sound.byte.waiting;
    s.phase=inner.phase==1?2:0;return true;
}
bool callback_return(std::vector<std::uint8_t>& ram,AnimationExecutionState& s,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if(!draw_return(ram,s,ports,error))return false;
    s.sprite.registers.d[6]=s.sprite.registers.a[1];
    return write_ram(ram,s.sprite.registers.a[0],0,4,s.sprite.registers.d[6],error);
}
bool callback(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,AnimationExecutionState& s,
    bool word_selector,bool allow_sound,std::uint8_t external_status,std::uint32_t& external_reads,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;std::uint32_t value=0;
    s.saved_a0=r.a[0];
    if(word_selector) {
        if(!script_address(r.a[1],1,r.a[1],error))return false;
        if(!next(ram,scripts,r,2,value,error))return false;word(r.d[0],value);
    } else {
        r.d[0]=0;if(!next(ram,scripts,r,1,value,error))return false;r.d[0]=value;
    }
    const unsigned int selector=value;
    word(r.d[0],r.d[0]*2U);word(r.d[0],r.d[0]*2U);r.a[0]=0x4a500;
    if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[0])+signed_word(r.d[0]),4,value,error))return false;r.d[7]=value;
    if(word_selector) {
        if(!next(ram,scripts,r,2,value,error))return false;word(r.d[0],value);word(r.d[0],r.d[0]*2U);r.a[0]=0x4a76c;
        if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[0])+signed_word(r.d[0]),2,value,error))return false;word(r.d[1],value);
    }
    if(!next(ram,scripts,r,4,value,error))return false;r.a[0]=value;
    s.saved_a1=r.a[1];r.a[1]=r.d[7];if(word_selector)r.d[0]=r.a[0];
    if(!read_ram(ram,s.a5,-0x7ff0,2,value,error))return false;s.saved_bank=static_cast<std::uint16_t>(value);
    if(!zero_bank(ram,s,ports,error))return false;
    if((word_selector || selector==3) && r.a[1]==0x3679eU)return callback_return(ram,s,ports,error);
    if((word_selector || selector==0x1f) && r.a[1]==0x47672U) {
        if(!allow_sound) {error="animation sound callback requires external-input overload";return false;}
        if(!sound_callback(ram,windows,s,external_status,external_reads,error))return false;
        return s.phase==2 || callback_return(ram,s,ports,error);
    }
    if(word_selector ? (r.a[1]!=0x2b3e8U && r.a[1]!=0x2b3faU) :
        ((selector!=0x1d && selector!=0x1e) || r.a[1]!=(selector==0x1d?0x2b3e8U:0x2b3faU))) {
        error="unsupported animation callback selector or table target";return false;
    }
    r.d[0]=0;
    if(!read_ram(ram,s.a6,r.a[1]==0x2b3e8U?0x7c:0x7d,1,value,error))return false;r.d[0]=value;
    word(r.d[0],r.d[0]*2U);word(r.d[0],r.d[0]*2U);
    if(!read_data(ram,windows,static_cast<std::int64_t>(r.a[0])+signed_word(r.d[0]),4,value,error))return false;
    if(!write_ram(ram,s.a6,0x78,4,value,error))return false;
    return callback_return(ram,s,ports,error);
}
bool run(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,
    AnimationExecutionState& s,bool allow_sound,std::uint8_t external_status,std::uint32_t& external_reads,
    bool& carry,std::vector<VideoPortWrite>& ports,std::string& error) {
    SceneMapTransferState& r=s.sprite.registers;std::uint32_t value=0;
    if(s.phase==4) {
        if(!allow_sound) {error="direct animation sound resume requires external-input overload";return false;}
        if(!direct_sound(ram,s,external_status,external_reads,error))return false;
        if(s.phase==4)return true;
    } else if(s.phase==2) {
        if(!allow_sound) {error="animation sound resume requires external-input overload";return false;}
        if(!sound_callback(ram,windows,s,external_status,external_reads,error))return false;
        if(s.phase==2)return true;
        if(!callback_return(ram,s,ports,error))return false;
    } else if(s.phase==1 || s.phase==3) {
        const bool indexed=s.phase==3;const std::uint32_t end=s.saved_list_end;
        if(s.a5!=0x108000) {error="animation sprite resume requires canonical A5=108000";return false;}
        SpriteSubmitStatus status=SpriteWaiting;if(!execute_sprite_submit(ram,s.sprite,status,error))return false;
        if(s.sprite.waiting)return true;
        if(!draw_return(ram,s,ports,error))return false;
        if(indexed) {r.a[1]=end;s.saved_list_end=0;}
    } else {
        const std::uint64_t pointer=static_cast<std::uint64_t>(s.a6)+0x26;
        if(pointer>0xffffffffU) {error="animation object pointer overflows";return false;}r.a[0]=static_cast<std::uint32_t>(pointer);
        if(!zero_bank(ram,s,ports,error))return false;
        if(!read_ram(ram,r.a[0],0,4,value,error))return false;r.d[7]=value;
        if(value==0) {carry=true;return true;}r.a[1]=value;
        if(!write_ram(ram,s.a5,0x5742,1,0,error))return false;
        if(!read_ram(ram,s.a6,0x17,1,value,error))return false;
        if(value>0 && value<0x80U)if(!write_ram(ram,s.a6,0x17,1,value-1U,error))return false;
    }
    for(unsigned int commands=0;commands<10000;++commands) {
        r.d[7]=0;if(!next(ram,scripts,r,1,value,error))return false;r.d[7]=value;
        if(value==4) {if(!draw(ram,scripts,s,ports,error))return false;if(s.sprite.waiting)return true;continue;}
        if(value==0x0c) {if(!field_branch(ram,scripts,windows,s,error))return false;continue;}
        if(value==0x10) {if(!indexed_draw(ram,scripts,windows,s,ports,error))return false;if(s.sprite.waiting)return true;continue;}
        if(value==0x14 || value==0x3c) {if(!callback(ram,scripts,windows,s,value==0x3c,allow_sound,external_status,external_reads,ports,error))return false;if(s.phase==2)return true;continue;}
        if(value==8) {
            ++r.a[1];if(!read_script(ram,scripts,r.a[1],4,value,error))return false;r.d[7]=value;r.a[1]=value;
            r.d[6]=r.a[1];if(!write_ram(ram,r.a[0],0,4,r.d[6],error))return false;continue;
        }
        if(value==0x18 || value==0x1c || value==0x20 || value==0x24 || value==0x34 || value==0x38 || value==0x2c) {
            if(!field_command(ram,scripts,windows,s,value,error))return false;continue;
        }
        if(value==0x30) {
            if(!allow_sound) {error="direct animation sound requires external-input overload";return false;}
            if(!script_address(r.a[1],1,r.a[1],error))return false;r.d[0]=0;
            if(!next(ram,scripts,r,2,value,error))return false;r.d[0]=value;
            s.saved_a0=r.a[0];s.saved_a1=r.a[1];
            if(!direct_sound(ram,s,external_status,external_reads,error))return false;
            if(s.phase==4)return true;continue;
        }
        if(value==0x28) {
            if(!read_ram(ram,r.a[0],4,2,value,error))return false;
            if(negative_word(value)) {
                if(!write_ram(ram,r.a[0],4,2,0,error))return false;
                if(!read_ram(ram,r.a[0],0,4,value,error))return false;r.d[7]=value;r.a[1]=value;continue;
            }
            if(!write_ram(ram,r.a[0],4,1,0,error))return false;r.d[7]=0xffffffffU;return epilogue(ram,s,carry,ports,error);
        }
        if(value!=0) {error="unsupported animation opcode";return false;}
        r.d[7]=0;if(!read_ram(ram,s.a5,0x5742,1,value,error))return false;
        if(!write_ram(ram,s.a5,0x5742,1,value+1U,error))return false;
        if(!next(ram,scripts,r,1,value,error))return false;byte(r.d[1],value);
        if((r.d[1]&255U)==0) {
            if(!read_ram(ram,r.a[0],4,1,value,error))return false;byte(r.d[6],value);
            if(value&0x80U) {
                if(!write_ram(ram,r.a[0],4,2,0,error))return false;
                if(!read_ram(ram,r.a[0],0,4,value,error))return false;r.d[7]=value;r.a[1]=value;continue;
            }
            return epilogue(ram,s,carry,ports,error);
        }
        if(!read_ram(ram,r.a[0],4,2,value,error))return false;word(r.d[6],value);
        const std::uint32_t original=r.d[6]&65535U;
        if(original==0 || negative_word(original)) {
            if(!read_ram(ram,r.a[0],4,1,value,error))return false;
            if(!write_ram(ram,r.a[0],4,1,value+r.d[1],error))return false;
        }
        if(!negative_word(original)) {
            if(!read_ram(ram,r.a[0],6,2,value,error))return false;word(r.d[0],value);
            if(!read_ram(ram,r.a[0],4,2,value,error))return false;
            if(!write_ram(ram,r.a[0],4,2,value-r.d[0],error))return false;
        }
        if(!read_ram(ram,r.a[0],4,2,value,error))return false;
        if(value!=0 && !negative_word(value)) {if(!read_ram(ram,r.a[0],0,4,value,error))return false;r.d[5]=value;r.a[1]=value;}
        if(!read_script(ram,scripts,r.a[1],1,value,error))return false;
        if(value==0x28) {if(!read_ram(ram,r.a[0],0,4,value,error))return false;r.d[5]=value;r.a[1]=value;r.d[7]=0xffffffffU;}
        if(negative_word(original))continue;
        r.d[6]=r.a[1];if(!write_ram(ram,r.a[0],0,4,r.d[6],error))return false;
        return epilogue(ram,s,carry,ports,error);
    }
    error="animation exceeded10000-command execution cap";return false;
}
bool transaction(std::vector<std::uint8_t>& ram,const std::vector<AnimationResource>& scripts,
    const std::vector<FixedDataResource>& windows,AnimationExecutionState& state,bool allow_sound,
    std::uint8_t external_status,std::uint32_t& external_reads,bool& carry,
    std::vector<VideoPortWrite>& ports,std::string& error) {
    if(ram.size()!=65536 || !valid(state)) {error="invalid animation RAM or continuation";return false;}
    try {
        std::vector<std::uint8_t> candidate=ram;AnimationExecutionState next_state=state;
        bool result=carry;std::vector<VideoPortWrite> output;std::uint32_t reads=0;
        if(!run(candidate,scripts,windows,next_state,allow_sound,external_status,reads,result,output,error))return false;
        ram.swap(candidate);state=next_state;carry=result;ports.swap(output);external_reads=reads;error.clear();return true;
    } catch(const std::bad_alloc&) {error="cannot allocate animation execution transaction";return false;}
}
}
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,AnimationExecutionState& state,
    bool& carry,std::vector<VideoPortWrite>& ports,std::string& error) {
    return step_animation_execution(ram,scripts,std::vector<FixedDataResource>(),state,carry,ports,error);
}
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,const std::vector<FixedDataResource>& windows,
    AnimationExecutionState& state,bool& carry,std::vector<VideoPortWrite>& ports,std::string& error) {
    std::uint32_t reads=0;return transaction(ram,scripts,windows,state,false,0,reads,carry,ports,error);
}
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,const std::vector<FixedDataResource>& windows,
    AnimationExecutionState& state,std::uint8_t external_status,std::uint32_t& external_reads,
    bool& carry,std::vector<VideoPortWrite>& ports,std::string& error) {
    return transaction(ram,scripts,windows,state,true,external_status,external_reads,carry,ports,error);
}
}

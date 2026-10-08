#include "ms5/stage_block_draw.h"
#include <cassert>
#include <iostream>
namespace {
void put(std::vector<std::uint8_t>& r,unsigned int at,std::uint32_t v,unsigned int n=2) {
    for(unsigned int i=0;i<n;++i) r[at+i]=static_cast<std::uint8_t>(v>>(8*(n-i-1)));
}
ms5::ObjectRestartState initial() {
    ms5::ObjectRestartState s;
    for(unsigned int i=0;i<8;++i) s.d[i]=0xabcd1200U+i;
    for(unsigned int i=0;i<7;++i) s.a[i]=0x98765400U+i;
    return s;
}
bool same(const ms5::ObjectRestartState& a,const ms5::ObjectRestartState& b) {
    for(unsigned int i=0;i<8;++i) if(a.d[i]!=b.d[i]) return false;
    for(unsigned int i=0;i<7;++i) if(a.a[i]!=b.a[i]) return false;
    return true;
}
void preserved(const ms5::ObjectRestartState& s,const ms5::ObjectRestartState& old) {
    assert(s.d[4]==old.d[4]&&s.d[5]==old.d[5]);
    for(unsigned int i=1;i<7;++i) if(i!=4) assert(s.a[i]==old.a[i]);
    for(unsigned int i=0;i<2;++i) assert((s.d[i]&0xffff0000U)==(old.d[i]&0xffff0000U));
    assert((s.d[6]&0xffff0000U)==(old.d[6]&0xffff0000U));
}
ms5::FixedDataResource resource(std::uint32_t start,const std::vector<std::uint8_t>& bytes) {
    ms5::FixedDataResource w;w.source_cpu_address=w.source_rom_offset=start;w.data=bytes;return w;
}
std::vector<std::uint8_t> synthetic() {
    // Deliberately synthetic two-record stream. Original extracted table is
    // supplied only by ignored runtime resources in native/CLI validation.
    std::vector<std::uint8_t> r(14,0);
    put(r,0,0);put(r,2,0x12f8);r[4]=2;r[5]=3;
    put(r,6,0x40);put(r,8,0x2234);r[10]=1;r[11]=2;
    put(r,12,0xffff);return r;
}

void success(std::vector<std::uint8_t>& ram,std::uint32_t entry,const std::vector<ms5::FixedDataResource>& windows,
    ms5::ObjectRestartState& s,std::vector<ms5::VideoPortWrite>& ports) {
    const std::vector<std::uint8_t> before=ram;const ms5::ObjectRestartState old=s;std::string error="old";
    assert(ms5::execute_stage_block_draw(ram,entry,windows,s,ports,error));assert(ram==before&&error.empty());preserved(s,old);
}
void failure(std::vector<std::uint8_t>& ram,std::uint32_t entry,const std::vector<ms5::FixedDataResource>& windows,ms5::ObjectRestartState& s) {
    const std::vector<std::uint8_t> before=ram;const ms5::ObjectRestartState old=s;
    std::vector<ms5::VideoPortWrite> ports(1);ports[0].size=1;ports[0].address=7;ports[0].value=9;std::string error;
    assert(!ms5::execute_stage_block_draw(ram,entry,windows,s,ports,error));
    assert(ram==before&&same(s,old)&&ports.size()==1&&ports[0].size==1&&ports[0].address==7&&ports[0].value==9&&!error.empty());
}
}
int main() {
    std::vector<std::uint8_t> ram(65536,0x5a);std::vector<ms5::FixedDataResource> windows,empty;
    std::vector<ms5::VideoPortWrite> ports;ms5::ObjectRestartState s=initial();
    windows.push_back(resource(0xddfa4,synthetic()));
    success(ram,0x477a2,windows,s,ports);
    assert(s.a[0]==0xddfb2&&s.a[4]==0x3c0000&&s.d[0]==0xabcd7162&&s.d[1]==0xabcdffff&&s.d[2]==0&&s.d[3]==2&&s.d[6]==0xabcd0000&&s.d[7]==0x71a42254);
    assert(ports.size()==10&&ports[0].size==4&&ports[0].address==0x3c0000&&ports[0].value==0x716212f8&&ports.back().size==2&&ports.back().value==0x8200);
    const std::vector<ms5::VideoPortWrite> fixed_ports=ports;
    const ms5::ObjectRestartState fixed_state=s;
    s=initial();s.d[0]=0xabcd7162;success(ram,0xddf9a,windows,s,ports);assert(same(s,fixed_state));
    const std::vector<std::uint8_t> raw=synthetic();
    for(unsigned int i=0;i<raw.size();++i) ram[0x6000+i]=raw[i];
    s=initial();s.d[0]=0xabcd7162;s.a[0]=0x106000;success(ram,0x362a,empty,s,ports);
    assert(s.a[0]==0x10600e&&ports.size()==fixed_ports.size());
    for(unsigned int i=0;i<ports.size();++i) assert(ports[i].size==fixed_ports[i].size&&ports[i].address==fixed_ports[i].address&&ports[i].value==fixed_ports[i].value);
    // Empty stream does not touch any unreached35f0 registers, even with
    // otherwise invalid coordinates/zero dimensions. Sentinel at RAM end is valid.
    s=initial();s.a[0]=0x10fffe;s.d[2]=s.d[3]=0;put(ram,0xfffe,0xffff);
    ms5::ObjectRestartState expect=s;expect.a[0]=0x110000;expect.d[1]=0xabcdffff;
    ports.resize(1);success(ram,0x362a,empty,s,ports);assert(same(s,expect)&&ports.empty());
    // Native BYTE tile addition wraps without carrying into its WORD. D0/D1
    // and direct D2/D3/D6 preserve their upper words; A0 is untouched.
    s=initial();s.d[0]=0xabcd0000;s.d[1]=0xabcd12f8;s.d[2]=0x76540002;s.d[3]=0x98760003;
    const std::uint32_t old_a0=s.a[0];success(ram,0x35f0,empty,s,ports);
    const std::uint32_t expected_tiles[]={0x000012f8,0x00011208,0x00021218,0x002012f9,0x00211209,0x00221219};
    assert(ports.size()==7);for(unsigned int i=0;i<6;++i) assert(ports[i].size==4&&ports[i].value==expected_tiles[i]);
    assert(s.d[0]==0xabcd0040&&s.d[1]==0xabcd12fa&&s.d[2]==0x76540000&&s.d[3]==0x98760003&&s.d[6]==0xabcd0000&&s.d[7]==0x00231229&&s.a[0]==old_a0);
    // Widths beyond BYTE size remain supported at direct35f0, with no invented
    // small-dimension cap. Stream offsets separately wrap as native WORDs.
    s=initial();s.d[0]=0;s.d[1]=0;s.d[2]=0x9876012c;s.d[3]=1;success(ram,0x35f0,empty,s,ports);assert(ports.size()==301&&s.d[2]==0x98760000&&s.d[0]==9600);
    s=initial();s.d[0]=0;s.d[1]=0;s.d[2]=1;s.d[3]=0x9876012c;success(ram,0x35f0,empty,s,ports);assert(ports.size()==301&&s.d[3]==0x9876012c&&s.d[6]==0xabcd0000&&s.d[0]==32);
    put(ram,0x6000,1);put(ram,0x6002,0x12f8);ram[0x6004]=2;ram[0x6005]=3;put(ram,0x6006,0xffff);
    s=initial();s.a[0]=0x106000;s.d[0]=0xabcdffff;success(ram,0x362a,empty,s,ports);assert(s.d[0]==0xabcdffff&&ports[0].value==0x000012f8);
    // Errors after earlier native effects remain completely transactional.
    s=initial();s.d[0]=0x74ff;s.d[1]=0;s.d[2]=1;s.d[3]=2;failure(ram,0x35f0,empty,s);
    put(ram,0x6000,0);put(ram,0x6002,0xff);ram[0x6004]=1;ram[0x6005]=1;
    put(ram,0x6006,0x7500);put(ram,0x6008,0);ram[0x600a]=1;ram[0x600b]=1;put(ram,0x600c,0xffff);
    s=initial();s.a[0]=0x106000;s.d[0]=0;failure(ram,0x362a,empty,s);
    std::vector<std::uint8_t> one(6,0);one[4]=one[5]=1;
    windows.clear();windows.push_back(resource(0x50000,one));s=initial();s.a[0]=0x50000;s.d[0]=0;failure(ram,0x362a,windows,s); // Missing sentinel after emitted rectangle.
    windows[0].data.push_back(0xff);failure(ram,0x362a,windows,s); // Partial sentinel WORD.
    windows[0].data.push_back(0xff);windows.push_back(windows[0]);failure(ram,0x362a,windows,s);windows.pop_back();
    windows.push_back(resource(0x50006,std::vector<std::uint8_t>(1,0xff)));failure(ram,0x362a,windows,s);windows.pop_back(); // Partial overlap still ambiguous.
    // Raw MS5D windows can begin at odd addresses. WORD alignment applies
    // to the read itself; odd BYTE fragments remain valid and overlaps count.
    windows.clear();windows.push_back(resource(0x50000,std::vector<std::uint8_t>(one.begin(),one.begin()+5)));
    windows.push_back(resource(0x50005,std::vector<std::uint8_t>(1,1)));
    windows.push_back(resource(0x50006,std::vector<std::uint8_t>(2,0xff)));
    s=initial();s.a[0]=0x50000;s.d[0]=0;success(ram,0x362a,windows,s,ports);
    assert(s.a[0]==0x50008&&ports.size()==2);
    windows.push_back(resource(0x50001,std::vector<std::uint8_t>(1,0)));
    s=initial();s.a[0]=0x50000;s.d[0]=0;failure(ram,0x362a,windows,s);
    // Resource checks occur on reads: direct35f0 needs no table window.
    s=initial();s.d[0]=0;s.d[1]=0;s.d[2]=1;s.d[3]=1;success(ram,0x35f0,windows,s,ports);
    s=initial();failure(ram,0x477a2,empty,s);
    const std::uint32_t bad_pointers[]={0x106001,0x10ffff,0x200000,0xffffffff};
    for(unsigned int i=0;i<4;++i) {s=initial();s.a[0]=bad_pointers[i];failure(ram,0x362a,empty,s);}
    windows.clear();ms5::FixedDataResource banked=resource(0x200000,std::vector<std::uint8_t>(2,0xff));windows.push_back(banked);
    s=initial();s.a[0]=0x200000;failure(ram,0x362a,windows,s);
    for(unsigned int zero=0;zero<2;++zero) {s=initial();s.d[0]=0;s.d[2]=zero==0?0:1;s.d[3]=zero==0?1:0;failure(ram,0x35f0,empty,s);}
    s=initial();failure(ram,0,empty,s);ram.resize(65535);failure(ram,0x477a2,windows,s);
    std::cout<<"stage_block_draw_test passed\n";
}

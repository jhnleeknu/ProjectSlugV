#include "ms5/physical_rom_resource.h"
#include "ms5/fixed_data_resource.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <unistd.h>
namespace {
typedef std::vector<std::uint8_t> Bytes;
void le(Bytes& b,unsigned int at,std::uint32_t value) {
    assert(at+4<=b.size());for(unsigned int i=0;i<4;++i)b[at+i]=static_cast<std::uint8_t>(value>>(i*8));
}
std::uint32_t crc(const Bytes& b) {
    std::uint32_t c=0xffffffffU;for(std::size_t i=0;i<b.size();++i){c^=b[i];for(unsigned int j=0;j<8;++j)c=(c>>1)^((c&1)?0xedb88320U:0U);}return c^0xffffffffU;
}
Bytes container(std::uint32_t offset,const Bytes& payload) {
    Bytes b(32);b[0]='M';b[1]='S';b[2]='5';b[3]='D';le(b,4,1);le(b,8,3);le(b,12,0xffffffffU);
    le(b,16,offset);le(b,20,static_cast<std::uint32_t>(payload.size()));le(b,24,crc(payload));
    b.insert(b.end(),payload.begin(),payload.end());return b;
}
void save(const char* path,const Bytes& b) {
    std::ofstream f(path,std::ios::binary|std::ios::trunc);assert(f);
    if(!b.empty())f.write(reinterpret_cast<const char*>(&b[0]),b.size());f.close();assert(!f.fail());
}
void reject(const char* path,const Bytes& b,ms5::PhysicalRomResource& r) {
    const ms5::PhysicalRomResource before=r;save(path,b);std::string error;
    assert(!ms5::load_physical_rom_resource(path,r,error)&&!error.empty());
    assert(r.source_rom_offset==before.source_rom_offset&&r.data==before.data);
}
}
int main() {
    char path[]="/tmp/ms5-physical-resource-XXXXXX";const int fd=mkstemp(path);assert(fd>=0&&close(fd)==0);
    const char digits[]="123456789";Bytes payload(digits,digits+9);assert(crc(payload)==0xcbf43926U);
    const Bytes valid=container(0x7ffff7,payload);ms5::PhysicalRomResource r;
    assert(r.source_rom_offset==0&&r.data.empty());r.source_rom_offset=123;r.data.assign(2,0xaa);std::string error="dirty";
    save(path,valid);assert(ms5::load_physical_rom_resource(path,r,error)&&error.empty());assert(r.source_rom_offset==0x7ffff7&&r.data==payload);
    // Existing loaders must not consume newkind3, with their state preserved.
    ms5::FixedDataResource old;old.source_cpu_address=123;old.source_rom_offset=456;old.data.assign(1,77);
    assert(!ms5::load_fixed_data_resource(path,old,error));assert(old.source_cpu_address==123&&old.source_rom_offset==456&&old.data==Bytes(1,77));
    assert(!ms5::load_banked_data_resource(path,old,error));assert(old.source_cpu_address==123&&old.source_rom_offset==456&&old.data==Bytes(1,77));
    Bytes bad=valid;bad[0]='X';reject(path,bad,r);
    const unsigned int fields[]={4,8,12,28};const std::uint32_t wrong[]={2,2,0,1};
    for(unsigned int i=0;i<4;++i){bad=valid;le(bad,fields[i],wrong[i]);reject(path,bad,r);}
    bad=valid;le(bad,8,1);le(bad,12,0xffff7);le(bad,16,0xffff7);reject(path,bad,r); // Valid kind1 container rejected by typed loader.
    save(path,bad);assert(ms5::load_fixed_data_resource(path,old,error));
    bad=valid;le(bad,8,2);le(bad,12,0x200000);le(bad,16,0x300000);reject(path,bad,r); // Valid kind2 container likewise rejected.
    save(path,bad);assert(ms5::load_banked_data_resource(path,old,error));
    bad=valid;le(bad,8,4);reject(path,bad,r);
    bad=valid;le(bad,16,0x800000);reject(path,bad,r);
    bad=valid;le(bad,16,0xffffffff);reject(path,bad,r);
    bad=valid;le(bad,16,0x7ffff8);reject(path,bad,r);
    bad=valid;le(bad,20,0);reject(path,bad,r);
    bad=valid;le(bad,20,0x100001);reject(path,bad,r);
    bad=valid;bad.back()^=1;reject(path,bad,r);
    bad=valid;le(bad,24,0);reject(path,bad,r);
    bad=valid;bad.push_back(0);reject(path,bad,r);
    bad=valid;bad.pop_back();reject(path,bad,r);
    reject(path,Bytes(31),r);reject(path,Bytes(),r);
    // Minimum payload at both physical endpoints, including a zero-valued byte.
    for(unsigned int i=0;i<2;++i) {
        const Bytes one(1,i?255:0);save(path,container(i?0x7fffff:0,one));error="dirty";
        assert(ms5::load_physical_rom_resource(path,r,error)&&error.empty());assert(r.source_rom_offset==(i?0x7fffffU:0)&&r.data==one);
    }
    const Bytes maximum(0x100000,0);save(path,container(0x700000,maximum));
    assert(ms5::load_physical_rom_resource(path,r,error)&&r.source_rom_offset==0x700000&&r.data==maximum);
    bad=container(0,Bytes(0x100001));reject(path,bad,r);
    assert(std::remove(path)==0);const ms5::PhysicalRomResource before=r;
    assert(!ms5::load_physical_rom_resource(path,r,error)&&r.data==before.data&&r.source_rom_offset==before.source_rom_offset);
    std::cout<<"physical_rom_resource_test passed\n";
}

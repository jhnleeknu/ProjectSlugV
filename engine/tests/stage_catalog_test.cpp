#include "ms5/stage_catalog.h"
#include "ms5/stage_state.h"
#include <cassert>
#include <cstdlib>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <unistd.h>
static void be32(std::vector<std::uint8_t>& b,unsigned int at,std::uint32_t x) {
    for(unsigned int i=0;i<4;++i)b[at+i]=static_cast<std::uint8_t>(x>>(24-i*8));
}
static void le32(std::vector<std::uint8_t>& b,unsigned int at,std::uint32_t x) {
    for(unsigned int i=0;i<4;++i)b[at+i]=static_cast<std::uint8_t>(x>>(i*8));
}
static std::uint32_t crc(const std::vector<std::uint8_t>& b) {
    std::uint32_t c=0xffffffffU;
    for(std::size_t i=0;i<b.size();++i) {c^=b[i];for(unsigned int j=0;j<8;++j)c=(c>>1)^((c&1)?0xedb88320U:0);}
    return c^0xffffffffU;
}
static void file(const std::string& path,std::uint32_t address,const std::vector<std::uint8_t>& data) {
    std::vector<std::uint8_t> h(32,0);h[0]='M';h[1]='S';h[2]='5';h[3]='D';
    le32(h,4,1);le32(h,8,1);le32(h,12,address);le32(h,16,address);le32(h,20,static_cast<std::uint32_t>(data.size()));le32(h,24,crc(data));
    std::ofstream o(path.c_str(),std::ios::binary);o.write(reinterpret_cast<const char*>(&h[0]),32);
    o.write(reinterpret_cast<const char*>(&data[0]),static_cast<std::streamsize>(data.size()));o.close();assert(o);
}
int main() {
    char pattern[]="/tmp/ms5-stage-test-XXXXXX";
    char* directory=mkdtemp(pattern);assert(directory);
    const std::string root(directory);
    std::vector<std::uint8_t> index(76,0);
    std::vector<std::string> files;
    for(unsigned int i=0;i<19;++i) {
        char name[40];std::snprintf(name,sizeof(name),"/stage_group_%02u.ms5d",i);files.push_back(root+name);
        be32(index,i*4,0x60000+i*0x100);
        file(files.back(),0x60000+i*0x100,std::vector<std::uint8_t>(4,0));
    }
    file(root+"/stage_index.ms5d",0x474f4,index);
    std::vector<std::uint8_t> group(26,0);group[0]=0xab;group[1]=0xcd;group[3]=20;group[22]='A';
    file(files[0],0x60000,group);
    ms5::StageCatalog catalog;
    std::string error;
    assert(ms5::load_stage_catalog(root,catalog,error));
    assert(catalog.groups.size()==19 && catalog.groups[0].header==0xabcd && catalog.groups[0].records[0].data[18]=='A');
    std::uint16_t count=9;std::uint32_t record=10,name=11;
    assert(ms5::query_stage(catalog,65535,0,count,record,name,error));
    assert(count==1 && record==0x60004 && name==0x60016);
    assert(ms5::query_stage(catalog,0,1,count,record,name,error));assert(record==0 && name==0 && count==1);
    // Failure at the last group must not replace the already populated output catalog.
    std::vector<std::uint8_t> bad(6,0);bad[3]=2;
    file(files[18],0x61200,bad);
    assert(!ms5::load_stage_catalog(root,catalog,error));
    assert(catalog.groups.size()==19 && catalog.groups[0].records.size()==1 && catalog.groups[0].header==0xabcd);
    file(files[18],0x61200,std::vector<std::uint8_t>(4,0));
    for(unsigned int mode=0;mode<5;++mode) {
        bad=group;
        if(mode==0)bad[2]=0x80;
        if(mode==1)bad[3]=21;
        if(mode==2)bad.resize(25);
        if(mode==3)bad[23]='B';
        if(mode==4)bad.push_back(0);
        file(files[0],0x60000,bad);
        assert(!ms5::load_stage_catalog(root,catalog,error));
        assert(catalog.groups[0].records[0].data[18]=='A');
    }
    catalog.groups[0].records[0].source_cpu_address=0x60006;
    count=9;record=10;name=11;
    assert(!ms5::query_stage(catalog,0,0,count,record,name,error));
    assert(count==9 && record==10 && name==11);
    for(std::size_t i=0;i<files.size();++i)std::remove(files[i].c_str());
    std::remove((root+"/stage_index.ms5d").c_str());rmdir(directory);
    std::vector<std::uint8_t> ram(65536,0xa5);
    std::vector<std::uint8_t> saved=ram;
    assert(!ms5::set_stage_state(ram,static_cast<ms5::StageStateAction>(3),0,error));assert(ram==saved);
    assert(ms5::set_stage_state(ram,ms5::SelectStage,0x100,error));
    assert(ram[0xd680]==0 && ram[0xd681]==0);
    ram[0x0bad]=255;assert(ms5::set_stage_state(ram,ms5::SelectNextStageArea,0,error));assert(ram[0xd681]==0);
    ram.resize(65535);saved=ram;assert(!ms5::set_stage_state(ram,ms5::SelectStage,0,error));assert(ram==saved);
    std::cout << "Stage catalog lengths, source addresses and rollback passed\n";
}

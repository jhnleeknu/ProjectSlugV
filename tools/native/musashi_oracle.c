/* Single-context synthetic/native oracle bridge; original ROM is never edited. */
#include <stdint.h>
#include <string.h>
#include "m68k.h"

#define ORACLE_MEMORY_SIZE 0x200000U
static unsigned char oracle_memory[ORACLE_MEMORY_SIZE];
static unsigned int oracle_fault;
static unsigned int oracle_fault_address;
static unsigned int oracle_instructions;
static unsigned int oracle_inside_hook;
static unsigned int oracle_observer_failed;
static int (*oracle_observer)(unsigned int pc);
static int (*oracle_write_observer)(unsigned int pc, unsigned int address, unsigned int size, unsigned int value);
static unsigned int oracle_current_pc;
static unsigned int oracle_write_count;

static int observe_write(unsigned int address, unsigned int size, unsigned int value)
{
    ++oracle_write_count;
    if (oracle_write_observer) {
        oracle_inside_hook = 1;
        if (oracle_write_observer(oracle_current_pc, address, size, value)) {
            oracle_observer_failed = 1;
            m68k_end_timeslice();
        }
        oracle_inside_hook = 0;
    }
    return !oracle_observer_failed;
}

static int valid_span(unsigned int address, unsigned int size)
{
    if (address > ORACLE_MEMORY_SIZE || size > ORACLE_MEMORY_SIZE - address) {
        if (!oracle_fault) oracle_fault_address = address;
        oracle_fault = 1;
        m68k_end_timeslice();
        return 0;
    }
    return 1;
}

unsigned int m68k_read_memory_8(unsigned int address)
{
    address &= 0xffffffU;
    return valid_span(address, 1) ? oracle_memory[address] : 0;
}
unsigned int m68k_read_memory_16(unsigned int address)
{
    address &= 0xffffffU;
    if (!valid_span(address, 2)) return 0;
    return ((unsigned int)oracle_memory[address] << 8) | oracle_memory[address+1];
}
unsigned int m68k_read_memory_32(unsigned int address)
{
    address &= 0xffffffU;
    if (!valid_span(address, 4)) return 0;
    return ((unsigned int)oracle_memory[address] << 24) | ((unsigned int)oracle_memory[address+1] << 16) |
           ((unsigned int)oracle_memory[address+2] << 8) | oracle_memory[address+3];
}
void m68k_write_memory_8(unsigned int address, unsigned int value)
{
    address &= 0xffffffU;
    if (!observe_write(address, 1, value & 0xffU)) return;
    if (valid_span(address, 1)) oracle_memory[address] = (unsigned char)value;
}
void m68k_write_memory_16(unsigned int address, unsigned int value)
{
    address &= 0xffffffU;
    if (!observe_write(address, 2, value & 0xffffU)) return;
    if (valid_span(address, 2)) {
        oracle_memory[address] = (unsigned char)(value >> 8);
        oracle_memory[address+1] = (unsigned char)value;
    }
}
void m68k_write_memory_32(unsigned int address, unsigned int value)
{
    address &= 0xffffffU;
    if (!observe_write(address, 4, value)) return;
    if (valid_span(address, 4)) {
        oracle_memory[address] = (unsigned char)(value >> 24);
        oracle_memory[address+1] = (unsigned char)(value >> 16);
        oracle_memory[address+2] = (unsigned char)(value >> 8);
        oracle_memory[address+3] = (unsigned char)value;
    }
}
void m68k_write_memory_32_pd(unsigned int address, unsigned int value)
{
    m68k_write_memory_16(address+2, value);
    m68k_write_memory_16(address, value >> 16);
}
static void instruction_hook(unsigned int pc)
{
    oracle_current_pc = pc;
    ++oracle_instructions;
    if (oracle_observer) {
        oracle_inside_hook = 1;
        if (oracle_observer(pc)) {
            oracle_observer_failed = 1;
            m68k_end_timeslice();
        }
        oracle_inside_hook = 0;
    }
}

void oracle_set_observer(int (*callback)(unsigned int pc))
{
    if (!oracle_inside_hook) oracle_observer = callback;
}
void oracle_set_write_observer(int (*callback)(unsigned int pc, unsigned int address, unsigned int size, unsigned int value))
{
    if (!oracle_inside_hook) oracle_write_observer = callback;
}

static void clear_fixture_registers(void)
{
    unsigned int reg;
    for (reg = M68K_REG_D0; reg <= M68K_REG_A6; ++reg)
        m68k_set_reg((m68k_register_t)reg, 0);
}

void oracle_init(void)
{
    if (oracle_inside_hook) return;
    memset(oracle_memory, 0, sizeof(oracle_memory));
    oracle_fault = oracle_fault_address = oracle_instructions = 0;
    oracle_observer_failed = 0;
    oracle_observer = NULL;
    oracle_write_observer = NULL;
    oracle_current_pc = oracle_write_count = 0;
    m68k_init();
    m68k_set_cpu_type(M68K_CPU_TYPE_68000);
    m68k_set_instr_hook_callback(instruction_hook);
    m68k_pulse_reset();
    clear_fixture_registers();
}
void oracle_reset(void)
{
    if (oracle_inside_hook) return;
    oracle_fault = oracle_fault_address = oracle_instructions = 0;
    m68k_set_cpu_type(M68K_CPU_TYPE_68000);
    m68k_set_irq(0);
    m68k_pulse_reset();
    clear_fixture_registers();
}
int oracle_load(unsigned int address, const unsigned char* data, unsigned int size)
{
    if (oracle_inside_hook) return 0;
    if (address > ORACLE_MEMORY_SIZE || size > ORACLE_MEMORY_SIZE-address) return 0;
    if (size) memcpy(oracle_memory+address, data, size);
    return 1;
}
int oracle_read(unsigned int address, unsigned char* data, unsigned int size)
{
    if (address > ORACLE_MEMORY_SIZE || size > ORACLE_MEMORY_SIZE-address) return 0;
    if (size) memcpy(data, oracle_memory+address, size);
    return 1;
}
int oracle_set_register(unsigned int reg, unsigned int value)
{
    if (oracle_inside_hook) return 0;
    if (reg > M68K_REG_SR) return 0;
    m68k_set_reg((m68k_register_t)reg, value);
    return 1;
}
unsigned int oracle_get_register(unsigned int reg)
{
    return reg <= M68K_REG_SR ? m68k_get_reg(NULL, (m68k_register_t)reg) : 0;
}
/* 0 sentinel, 1 budget exhausted, 2 memory fault, 3 stopped, 4 observer error. */
int oracle_run(unsigned int budget, unsigned int sentinel)
{
    unsigned int previous;
    unsigned int empty_calls = 0;
    if (oracle_inside_hook) return 4;
    oracle_instructions = oracle_fault = oracle_fault_address = 0;
    oracle_observer_failed = 0;
    oracle_write_count = 0;
    while (oracle_instructions < budget) {
        if (m68k_get_reg(NULL, M68K_REG_PC) == sentinel) return 0;
        previous = oracle_instructions;
        m68k_execute(1); /* One instruction may exceed this cycle slice. */
        if (oracle_observer_failed) return 4;
        if (oracle_fault) return 2;
        if (oracle_instructions == previous) {
            /* Reset cycle accounting can consume the first slice alone. */
            if (++empty_calls > 1) return 3;
        } else empty_calls = 0;
    }
    return m68k_get_reg(NULL, M68K_REG_PC) == sentinel ? 0 : 1;
}
unsigned int oracle_instruction_count(void) { return oracle_instructions; }
unsigned int oracle_last_fault_address(void) { return oracle_fault_address; }
unsigned int oracle_cpu_write_count(void) { return oracle_write_count; }

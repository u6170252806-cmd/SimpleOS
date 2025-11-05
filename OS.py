#!/usr/bin/env python3
"""
simple_os_emulator.py
A single-file, self-contained "simple OS" built on top of a toy 32-bit CPU emulator.
Features:
- 32-bit little-endian architecture (word = 4 bytes)
- Extended instruction set including MUL, DIV, MOD, SYSCALL, FPU instructions
- CPU supports a kernel/OS layer via SYSCALL instruction
- Memory supports registering/expanding regions at runtime
- A tiny in-memory filesystem (files stored in kernel)
- A host-side shell (terminal) with commands: ls, cat, whoami, echo, write, loadasm, run, memmap, regs, help, exit, ps, kill, chmod, mkdir, rm, cp, mv, stat, time, debug, trace, reboot, bootload, bios, clear, history, set, get, sleep, ping, uptime, df, top, find, cls, ver, calc, date, time, type, curl, wget, grep, wc
- Assembler for the toy ISA (labels, .org, .word, .float, .double)
- Sample programs and utilities
- Floating Point Unit (FPU) support
- Process management and multitasking simulation
- Memory protection and virtual memory concepts
- BIOS and bootloader support
- Enhanced error handling and recovery
"""
from __future__ import annotations
import sys
import shlex
import argparse
import logging
import time
import textwrap
import struct
import math
import os
import random
from typing import Dict, List, Tuple, Optional, Callable, Any
from enum import IntEnum
# Basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("SimpleOS")

# ---------------------------
# Architecture constants
# ---------------------------
WORD_SIZE = 4  # bytes per word
DEFAULT_MEMORY_BYTES = 32 * 1024 * 1024  # 32 MiB default (increased)
NUM_REGS = 16
NUM_FPU_REGS = 8  # Floating point registers
# Registers indices
REG_SP = 14
REG_KERNEL = 13  # reserved for kernel use in syscalls (optional)
REG_PC = 15  # not in regs array; CPU stores pc separately
# Flags
FLAG_ZERO = 1 << 0
FLAG_NEG = 1 << 1
FLAG_CARRY = 1 << 2
FLAG_OVERFLOW = 1 << 3
FLAG_INTERRUPT = 1 << 4
FLAG_TRAP = 1 << 5
# --- Additional Flags ---
FLAG_AUX = 1 << 6  # Auxiliary Carry Flag (for BCD operations)
FLAG_DIR = 1 << 7  # Direction Flag (for string operations)
FLAG_IOPL = 1 << 8  # I/O Privilege Level (for privilege levels)
FLAG_NT = 1 << 9   # Nested Task Flag (for task switching)
FLAG_RF = 1 << 10  # Resume Flag (for debugging)
FLAG_VM = 1 << 11  # Virtual 8086 Mode Flag
FLAG_AC = 1 << 12  # Alignment Check Flag
FLAG_VIF = 1 << 13  # Virtual Interrupt Flag
FLAG_VIP = 1 << 14  # Virtual Interrupt Pending Flag
FLAG_ID = 1 << 15  # ID Flag (identification)
# --- More Additional Flags ---
FLAG_VME = 1 << 16  # Virtual-8086 Mode Extensions
FLAG_PVI = 1 << 17  # Protected-Mode Virtual Interrupt Flag
FLAG_TSD = 1 << 18  # Time Stamp Disable
# Opcodes
OP_NOP = 0x00
OP_MOV = 0x01
OP_LOADI = 0x02
OP_LOAD = 0x03
OP_STORE = 0x04
OP_ADD = 0x05
OP_SUB = 0x06
OP_AND = 0x07
OP_OR = 0x08
OP_XOR = 0x09
OP_NOT = 0x0A
OP_SHL = 0x0B
OP_SHR = 0x0C
OP_JMP = 0x0D
OP_JZ = 0x0E
OP_JNZ = 0x0F
OP_CMP = 0x10
OP_PUSH = 0x11
OP_POP = 0x12
OP_CALL = 0x13
OP_RET = 0x14
OP_HALT = 0x15
OP_INC = 0x16
OP_DEC = 0x17
OP_OUT = 0x18
OP_IN = 0x19
OP_NOP2 = 0x1A
OP_LEA = 0x1B  # Load Effective Address
OP_MOVZX = 0x1C  # Move with Zero Extension
OP_MOVSX = 0x1D  # Move with Sign Extension
OP_TEST = 0x1E  # Test bits
OP_JE = 0x1F  # Jump if Equal
OP_JNE = 0x20  # Jump if Not Equal
OP_JL = 0x21  # Jump if Less
OP_JG = 0x22  # Jump if Greater
OP_JLE = 0x23  # Jump if Less or Equal
OP_JGE = 0x24  # Jump if Greater or Equal
OP_MUL = 0x25
OP_IMUL = 0x26  # Signed Multiply
OP_DIV = 0x27
OP_IDIV = 0x28  # Signed Divide
OP_MOD = 0x29
OP_SYSCALL = 0x2A  # software interrupt / syscall
OP_INT = 0x2B  # Hardware interrupt
OP_IRET = 0x2C  # Interrupt return
OP_CLC = 0x2D  # Clear Carry Flag
OP_STC = 0x2E  # Set Carry Flag
OP_CLI = 0x2F  # Clear Interrupt Flag
OP_STI = 0x30  # Set Interrupt Flag
OP_PUSHF = 0x31  # Push Flags
OP_POPF = 0x32  # Pop Flags
OP_ENTER = 0x33  # Enter function
OP_LEAVE = 0x34  # Leave function
OP_ADC = 0x35  # Add with Carry
OP_SBB = 0x36  # Subtract with Borrow
OP_ROL = 0x37  # Rotate Left
OP_ROR = 0x38  # Rotate Right
OP_BT = 0x39   # Bit Test
OP_BTS = 0x3A  # Bit Test and Set
OP_BTR = 0x3B  # Bit Test and Reset
OP_NEG = 0x3C  # Negate
OP_CBW = 0x3D  # Convert Byte to Word
OP_CWD = 0x3E  # Convert Word to Doubleword
OP_CWDQ = 0x3F # Convert Doubleword to Quadword
# FPU Instructions
OP_FLD = 0x40  # Load Float
OP_FST = 0x41  # Store Float
OP_FADD = 0x42  # Add Float
OP_FSUB = 0x43  # Subtract Float
OP_FMUL = 0x44  # Multiply Float
OP_FDIV = 0x45  # Divide Float
OP_FCOMP = 0x46  # Compare Float
OP_FCHS = 0x47  # Change Sign
OP_FABS = 0x48  # Absolute Value
OP_FSQRT = 0x49  # Square Root
OP_FSTP = 0x4A  # Store and Pop
OP_FLDZ = 0x4B  # Load Zero
OP_FLD1 = 0x4C  # Load One
OP_FLDPI = 0x4D  # Load Pi
OP_FLDLG2 = 0x4E  # Load Log10(2)
OP_FLDLN2 = 0x4F  # Load Ln(2)
OP_FXCH = 0x50  # Exchange ST(0) with ST(i)
OP_FSTSW = 0x51  # Store Status Word
OP_FCLEX = 0x52  # Clear Exceptions
OP_FILD = 0x53  # Load Integer
OP_FIST = 0x54  # Store Integer
OP_FISTP = 0x55 # Store Integer and Pop
# String Instructions
OP_MOVS = 0x60  # Move String
OP_STOS = 0x61  # Store String
OP_LODS = 0x62  # Load String
OP_SCAS = 0x63  # Scan String
OP_CMPS = 0x64  # Compare String
# Control Instructions
OP_LGDT = 0x70  # Load Global Descriptor Table
OP_LIDT = 0x71  # Load Interrupt Descriptor Table
OP_LDS = 0x72   # Load Far Pointer (DS)
OP_LES = 0x73   # Load Far Pointer (ES)
# Additional Instructions
OP_CLD = 0x74  # Clear Direction Flag
OP_STD = 0x75  # Set Direction Flag
OP_LAHF = 0x76  # Load AH from Flags
OP_SAHF = 0x77  # Store AH to Flags
OP_INTO = 0x78  # Interrupt on Overflow
OP_AAM = 0x79  # ASCII Adjust After Multiply
OP_AAD = 0x7A  # ASCII Adjust Before Divide
OP_XLAT = 0x7B  # Table Look-up Translation
OP_XCHG = 0x7C  # Exchange Register/Memory with Register
OP_CMPXCHG = 0x7D  # Compare and Exchange
OP_BSF = 0x7E  # Bit Scan Forward
OP_BSR = 0x7F  # Bit Scan Reverse
OP_LAR = 0x80  # Load Access Rights
OP_LSL = 0x81  # Load Segment Limit
OP_SLDT = 0x82  # Store Local Descriptor Table
OP_STR = 0x83  # Store Task Register
OP_LLDT = 0x84  # Load Local Descriptor Table
OP_LTR = 0x85  # Load Task Register
OP_VERR = 0x86  # Verify Real Mode Segment
OP_VERW = 0x87  # Verify Writeable Real Mode Segment
OP_SGDT = 0x88  # Store Global Descriptor Table
OP_SIDT = 0x89  # Store Interrupt Descriptor Table
OP_LGDT = 0x8A  # Load Global Descriptor Table
OP_LIDT = 0x8B  # Load Interrupt Descriptor Table
OP_SMSW = 0x8C  # Store Machine Status Word
OP_LMSW = 0x8D  # Load Machine Status Word
OP_CLTS = 0x8E  # Clear Task Switched Flag
OP_INVD = 0x8F  # Invalidate Cache
OP_WBINVD = 0x90  # Write Back and Invalidate Cache
OP_INVLPG = 0x91  # Invalidate TLB Entry
OP_INVPCID = 0x92  # Invalidate Process Context Identifier
OP_VMCALL = 0x93  # VM Call
OP_VMLAUNCH = 0x94  # VM Launch
OP_VMRESUME = 0x95  # VM Resume
OP_VMXOFF = 0x96  # VM Exit
OP_MONITOR = 0x97  # Monitor Processor
OP_MWAIT = 0x98  # Monitor Wait
OP_RDSEED = 0x99  # Read Random Seed
OP_RDRAND = 0xA0  # Read Random Number
OP_CLAC = 0xA1  # Clear Access Control
OP_STAC = 0xA2  # Set Access Control
OP_SKINIT = 0xA3  # Secure Key Initialization
OP_SVMEXIT = 0xA4  # SVM Exit
OP_SVMRET = 0xA5  # SVM Return
OP_SVMLOCK = 0xA6  # SVM Lock
OP_SVMUNLOCK = 0xA7  # SVM Unlock
OPCODE_NAME = {
    OP_NOP: "NOP",
    OP_MOV: "MOV",
    OP_LOADI: "LOADI",
    OP_LOAD: "LOAD",
    OP_STORE: "STORE",
    OP_ADD: "ADD",
    OP_SUB: "SUB",
    OP_AND: "AND",
    OP_OR: "OR",
    OP_XOR: "XOR",
    OP_NOT: "NOT",
    OP_SHL: "SHL",
    OP_SHR: "SHR",
    OP_JMP: "JMP",
    OP_JZ: "JZ",
    OP_JNZ: "JNZ",
    OP_CMP: "CMP",
    OP_PUSH: "PUSH",
    OP_POP: "POP",
    OP_CALL: "CALL",
    OP_RET: "RET",
    OP_HALT: "HALT",
    OP_INC: "INC",
    OP_DEC: "DEC",
    OP_OUT: "OUT",
    OP_IN: "IN",
    OP_NOP2: "NOP2",
    OP_LEA: "LEA",
    OP_MOVZX: "MOVZX",
    OP_MOVSX: "MOVSX",
    OP_TEST: "TEST",
    OP_JE: "JE",
    OP_JNE: "JNE",
    OP_JL: "JL",
    OP_JG: "JG",
    OP_JLE: "JLE",
    OP_JGE: "JGE",
    OP_MUL: "MUL",
    OP_IMUL: "IMUL",
    OP_DIV: "DIV",
    OP_IDIV: "IDIV",
    OP_MOD: "MOD",
    OP_SYSCALL: "SYSCALL",
    OP_INT: "INT",
    OP_IRET: "IRET",
    OP_CLC: "CLC",
    OP_STC: "STC",
    OP_CLI: "CLI",
    OP_STI: "STI",
    OP_PUSHF: "PUSHF",
    OP_POPF: "POPF",
    OP_ENTER: "ENTER",
    OP_LEAVE: "LEAVE",
    OP_ADC: "ADC",
    OP_SBB: "SBB",
    OP_ROL: "ROL",
    OP_ROR: "ROR",
    OP_BT: "BT",
    OP_BTS: "BTS",
    OP_BTR: "BTR",
    OP_NEG: "NEG",
    OP_CBW: "CBW",
    OP_CWD: "CWD",
    OP_CWDQ: "CWDQ",
    # FPU Instructions
    OP_FLD: "FLD",
    OP_FST: "FST",
    OP_FADD: "FADD",
    OP_FSUB: "FSUB",
    OP_FMUL: "FMUL",
    OP_FDIV: "FDIV",
    OP_FCOMP: "FCOMP",
    OP_FCHS: "FCHS",
    OP_FABS: "FABS",
    OP_FSQRT: "FSQRT",
    OP_FSTP: "FSTP",
    OP_FLDZ: "FLDZ",
    OP_FLD1: "FLD1",
    OP_FLDPI: "FLDPI",
    OP_FLDLG2: "FLDLG2",
    OP_FLDLN2: "FLDLN2",
    OP_FXCH: "FXCH",
    OP_FSTSW: "FSTSW",
    OP_FCLEX: "FCLEX",
    OP_FILD: "FILD",
    OP_FIST: "FIST",
    OP_FISTP: "FISTP",
    # String Instructions
    OP_MOVS: "MOVS",
    OP_STOS: "STOS",
    OP_LODS: "LODS",
    OP_SCAS: "SCAS",
    OP_CMPS: "CMPS",
    # Control Instructions
    OP_LGDT: "LGDT",
    OP_LIDT: "LIDT",
    OP_LDS: "LDS",
    OP_LES: "LES",
    # Additional Instructions
    OP_CLD: "CLD",
    OP_STD: "STD",
    OP_LAHF: "LAHF",
    OP_SAHF: "SAHF",
    OP_INTO: "INTO",
    OP_AAM: "AAM",
    OP_AAD: "AAD",
    OP_XLAT: "XLAT",
    OP_XCHG: "XCHG",
    OP_CMPXCHG: "CMPXCHG",
    OP_BSF: "BSF",
    OP_BSR: "BSR",
    OP_LAR: "LAR",
    OP_LSL: "LSL",
    OP_SLDT: "SLDT",
    OP_STR: "STR",
    OP_LLDT: "LLDT",
    OP_LTR: "LTR",
    OP_VERR: "VERR",
    OP_VERW: "VERW",
    OP_SGDT: "SGDT",
    OP_SIDT: "SIDT",
    OP_LGDT: "LGDT",
    OP_LIDT: "LIDT",
    OP_SMSW: "SMSW",
    OP_LMSW: "LMSW",
    OP_CLTS: "CLTS",
    OP_INVD: "INVD",
    OP_WBINVD: "WBINVD",
    OP_INVLPG: "INVLPG",
    OP_INVPCID: "INVPCID",
    OP_VMCALL: "VMCALL",
    OP_VMLAUNCH: "VMLAUNCH",
    OP_VMRESUME: "VMRESUME",
    OP_VMXOFF: "VMXOFF",
    OP_MONITOR: "MONITOR",
    OP_MWAIT: "MWAIT",
    OP_RDSEED: "RDSEED",
    OP_RDRAND: "RDRAND",
    OP_CLAC: "CLAC",
    OP_STAC: "STAC",
    OP_SKINIT: "SKINIT",
    OP_SVMEXIT: "SVMEXIT",
    OP_SVMRET: "SVMRET",
    OP_SVMLOCK: "SVMLOCK",
    OP_SVMUNLOCK: "SVMUNLOCK",
}
NAME_OPCODE = {v: k for k, v in OPCODE_NAME.items()}
# Instruction packing helpers
def pack_instruction(opcode: int, dst: int = 0, src: int = 0, imm16: int = 0) -> int:
    return ((opcode & 0xFF) << 24) | ((dst & 0x0F) << 20) | ((src & 0x0F) << 16) | (imm16 & 0xFFFF)
def unpack_instruction(word: int) -> Tuple[int, int, int, int]:
    opcode = (word >> 24) & 0xFF
    dst = (word >> 20) & 0x0F
    src = (word >> 16) & 0x0F
    imm16 = word & 0xFFFF
    return opcode, dst, src, imm16
def to_signed16(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x
def to_signed32(x: int) -> int:
    x &= 0xFFFFFFFF
    return x - 0x100000000 if x & 0x80000000 else x
def itob_le(val: int) -> bytes:
    v = val & 0xFFFFFFFF
    return bytes((v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF))
def btoi_le(b: bytes) -> int:
    return b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24)
def float_to_bits(f: float) -> int:
    return struct.unpack('<I', struct.pack('<f', f))[0]
def bits_to_float(bits: int) -> float:
    return struct.unpack('<f', struct.pack('<I', bits & 0xFFFFFFFF))[0]

# ---------------------------
# BIOS - Basic Input/Output System
# ---------------------------
class BIOS:
    """Emulated BIOS providing basic system services"""
    def __init__(self):
        self.boot_sector_addr = 0x7C00  # Standard boot sector load address
        self.bootloader_addr = 0x7E00   # Bootloader load address
        self.system_info = {
            "bios_version": "SimpleOS BIOS v1.1",
            "memory_size": 0,
            "cpu_features": ["32-bit", "FPU", "MMU"],
            "boot_devices": ["HDD", "FDD", "CDROM"]
        }
    def initialize_hardware(self, memory_size: int):
        """Initialize emulated hardware"""
        self.system_info["memory_size"] = memory_size
        # Get current date/time for BIOS info
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print("="*50)
        print("BIOS: Initializing system")
        print(f"BIOS Version: {self.system_info['bios_version']}")
        print(f"Date/Time: {current_time}")
        print(f"Memory Size: {memory_size} bytes ({memory_size // (1024*1024)} MB)")
        print(f"CPU Features: {', '.join(self.system_info['cpu_features'])}")
        print("="*50)
        return True
    def load_boot_sector(self, memory: Memory, boot_data: bytes):
        """Load boot sector into memory"""
        try:
            memory.load_bytes(self.boot_sector_addr, boot_data)
            print(f"BIOS: Boot sector loaded at 0x{self.boot_sector_addr:08x}")
            return True
        except Exception as e:
            print(f"BIOS: Failed to load boot sector: {e}")
            return False
    def get_system_info(self) -> dict:
        """Return system information"""
        return self.system_info.copy()

# ---------------------------
# Bootloader
# ---------------------------
class Bootloader:
    """Simple bootloader for loading OS kernel"""
    # Fixed BOOTLOADER_ASM: Corrected STORE instruction and JMP
    # The key fix is ensuring LOAD uses a memory address, not a register
    BOOTLOADER_ASM = r"""
.org 0x7C00
; Simple bootloader
LOADI R0, 0x7C00    ; Set up stack
MOV R14, R0         ; SP = 0x7C00
LOADI R0, 0x1000    ; Load kernel to 0x1000
LOADI R1, 0x2000    ; Kernel size (placeholder)
LOADI R2, 0x0000    ; Disk sector 0
CALL load_kernel    ; Load kernel
LOADI R0, 0x1000    ; Jump to kernel
JMP 0x1000          ; Execute kernel (Corrected JMP)
HALT
load_kernel:
; Simple kernel loading routine
; R0 = destination address
; R1 = size
; R2 = sector number
PUSH R0
PUSH R1
PUSH R2
; In real system, this would read from disk
; For emulation, we'll just copy from a predefined location
LOADI R3, 0x3000    ; Source of kernel data (address)
MOV R4, R0          ; Destination (address)
MOV R5, R1          ; Size counter
copy_loop:
CMP R5, R15         ; Compare with 0
JE copy_done        ; If zero, done
LOAD R6, R3         ; Load word from source address (FIXED: R3 is address, not register)
STORE R6, R4        ; Store to destination address (FIXED: R4 is address, not register)
ADD R3, R15, 4      ; Source += 4
ADD R4, R15, 4      ; Destination += 4
DEC R5              ; Size -= 4
JMP copy_loop
copy_done:
POP R2
POP R1
POP R0
RET
"""
    def __init__(self):
        self.assembler = Assembler()
    def generate_bootloader(self) -> bytes:
        """Generate bootloader binary"""
        try:
            return self.assembler.assemble(self.BOOTLOADER_ASM)
        except Exception as e:
            print(f"Bootloader: Failed to assemble: {e}")
            # Return minimal bootloader if assembly fails
            # This is a minimal valid bootloader that doesn't rely on problematic instructions
            # It simply halts after loading itself
            # This is a fallback to avoid crashing
            # It's not a working bootloader but avoids an error
            # We'll create a minimal binary that just halts
            print("WARNING: Using fallback bootloader due to assembly failure.")
            # Create a simple halt instruction at the end
            # This is not a real bootloader but prevents crashing
            return b"\x00\x00\x00\x00" * 128 + b"\x15\x00\x00\x00" # HALT at end

# ---------------------------
# Memory with region registration
# ---------------------------
class Memory:
    """
    Byte-addressable memory that can be expanded or have regions registered.
    For simplicity, regions are contiguous and we maintain a single bytearray that may grow.
    """
    def __init__(self, size_bytes: int = DEFAULT_MEMORY_BYTES):
        self.data = bytearray(size_bytes)
        self.size = size_bytes
        self.protected_regions = {}  # addr -> (size, permissions)
        logger.debug("Memory initialized: %d bytes", self.size)
    def check_address(self, addr: int, length: int = 1):
        if addr < 0 or addr + length > self.size:
            raise MemoryError(f"Memory access out of range: addr={addr} len={length} size={self.size}")
        # Check protection
        for prot_addr, (prot_size, perms) in self.protected_regions.items():
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x1):  # Read permission
                    raise MemoryError(f"Memory access violation: read protected at {addr:08x}")
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if length > 1 and addr + length > prot_addr + prot_size:
                    raise MemoryError(f"Memory access violation: cross boundary at {addr:08x}")
    def read_byte(self, addr: int) -> int:
        self.check_address(addr, 1)
        return self.data[addr]
    def write_byte(self, addr: int, val: int):
        self.check_address(addr, 1)
        # Check write protection
        for prot_addr, (prot_size, perms) in self.protected_regions.items():
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x2):  # Write permission
                    raise MemoryError(f"Memory access violation: write protected at {addr:08x}")
        self.data[addr] = val & 0xFF
    def read_word(self, addr: int) -> int:
        self.check_address(addr, 4)
        return btoi_le(bytes(self.data[addr:addr+4]))
    def write_word(self, addr: int, val: int):
        self.check_address(addr, 4)
        # Check write protection
        for prot_addr, (prot_size, perms) in self.protected_regions.items():
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x2):  # Write permission
                    raise MemoryError(f"Memory access violation: write protected at {addr:08x}")
        self.data[addr:addr+4] = itob_le(val)
    def load_bytes(self, addr: int, payload: bytes):
        self.check_expand(addr + len(payload))
        # Check write protection for the entire range
        for prot_addr, (prot_size, perms) in self.protected_regions.items():
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x2):  # Write permission
                    raise MemoryError(f"Memory access violation: write protected at {addr:08x}")
            if addr + len(payload) > prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x2):  # Write permission
                    raise MemoryError(f"Memory access violation: write protected at {addr:08x}")
        self.data[addr:addr+len(payload)] = payload
    def dump(self, start: int = 0, length: int = 256) -> bytes:
        self.check_address(start, length)
        return bytes(self.data[start:start+length])
    def check_expand(self, required_size: int):
        """Ensure backing storage is large enough; expand if necessary."""
        if required_size <= self.size:
            return
        # Expand in powers of two for simplicity (or by chunks)
        new_size = max(self.size * 2, required_size)
        logger.info("Expanding memory from %d to %d bytes", self.size, new_size)
        self.data.extend(bytearray(new_size - self.size))
        self.size = new_size
    def register_region(self, addr: int, size: int, permissions: int = 0x3):
        """Register/allocate a region starting at addr of given size (zero-filled).
           This will expand memory if necessary.
           permissions: 0x1=read, 0x2=write, 0x3=read+write"""
        if addr < 0:
            raise MemoryError("Negative address")
        self.check_expand(addr + size)
        self.protected_regions[addr] = (size, permissions)
        logger.info("Registered memory region: %08x - %08x (perm=%x)", addr, addr + size - 1, permissions)
    def unregister_region(self, addr: int):
        """Unregister a memory region."""
        if addr in self.protected_regions:
            del self.protected_regions[addr]
            logger.info("Unregistered memory region at %08x", addr)

# ---------------------------
# Process Management
# ---------------------------
class ProcessState(IntEnum):
    RUNNING = 1
    READY = 2
    BLOCKED = 3
    TERMINATED = 4
class Process:
    def __init__(self, pid: int, name: str, entry_point: int, memory_size: int = 4096):
        self.pid = pid
        self.name = name
        self.state = ProcessState.READY
        self.entry_point = entry_point
        self.memory_base = 0
        self.memory_size = memory_size
        self.registers = [0] * NUM_REGS
        self.fpu_registers = [0.0] * NUM_FPU_REGS
        self.pc = entry_point
        self.flags = 0
        self.stack_pointer = 0
        self.priority = 10  # Lower number = higher priority
        self.created_time = time.time()
        self.cpu_time = 0.0

# ---------------------------
# Simple Kernel / OS
# ---------------------------
class Kernel:
    """
    Very small kernel providing:
    - in-memory filesystem (dict filename -> bytes)
    - syscall handler that the CPU invokes
    - simple user environment (username)
    - ability to register memory regions
    - process management
    - file permissions
    Syscall convention (toy):
    - R0: syscall number
    - R1..R3: args (meaning depends on syscall)
    - Return value in R0
    Syscall numbers:
    1: WRITE (fd, buf_addr, len) -> writes to console if fd==1
    2: READ (fd, buf_addr, len) -> reads from stdin (not fully supported)
    3: LIST_DIR (dir_addr, out_addr) -> lists files into memory (simple format)
    4: WHOAMI (out_addr) -> writes username string to memory
    5: ALLOC (addr, size) -> register memory region
    6: LOAD_FILE (filename_addr, dest_addr) -> load file contents into memory at dest
    7: STORE_FILE (filename_addr, src_addr, len) -> write file into FS
    8: HALT -> stop CPU
    9: GET_TIME -> get system time in milliseconds
    10: SLEEP -> sleep for specified milliseconds
    11: CREATE_PROCESS (name_addr, entry_addr, mem_size) -> create new process
    12: EXIT_PROCESS -> terminate current process
    13: YIELD -> yield CPU to next process
    14: GET_PID -> get current process ID
    15: KILL_PROCESS (pid) -> kill process by ID
    16: LIST_PROCESSES (out_addr) -> list all processes
    17: CHMOD (filename_addr, mode) -> change file permissions
    18: MKDIR (dirname_addr) -> create directory
    19: REMOVE (filename_addr) -> remove file or directory
    20: COPY (src_addr, dest_addr) -> copy file
    21: MOVE (src_addr, dest_addr) -> move file
    22: STAT (filename_addr, stat_buf_addr) -> get file statistics
    23: EXEC (filename_addr) -> execute program
    24: REBOOT -> reboot system
    25: GET_BIOS_INFO (out_addr) -> get BIOS information
    26: GENERATE_RANDOM -> generate random number
    27: GET_SYSTEM_INFO (out_addr) -> get system information
    28: SET_ENV_VAR (var_addr, val_addr) -> set environment variable
    29: GET_ENV_VAR (var_addr, out_addr) -> get environment variable
    30: CLEAR_SCREEN -> clear screen
    31: SHOW_HISTORY -> show command history
    32: PING (host_addr) -> simulate ping
    33: UPTIME -> get system uptime
    34: DF -> get disk usage
    35: TOP -> get process info
    36: FIND (path_addr, pattern_addr) -> search for files
    37: CALC (num1, num2, operation) -> perform calculation
    38: DATE -> get current date
    39: TIME -> get current time
    40: TYPE (file_addr) -> print file contents
    41: CURL (url_addr) -> simulate curl command
    42: WGET (url_addr) -> simulate wget command
    43: GREP (pattern_addr, file_addr) -> search within file
    44: WC (file_addr) -> count lines, words, characters in a file
    """
    def __init__(self, username: str = "guest"):
        self.files: Dict[str, Dict[str, Any]] = {}  # filename -> {data, permissions, created_time, modified_time}
        self.username = username
        self.running = True
        self.processes: Dict[int, Process] = {}
        self.current_pid = 1
        self.next_pid = 2
        self.system_info = {
            "os_name": "SimpleOS",
            "version": "2.0",
            "architecture": "32-bit",
            "features": ["FPU", "MMU", "Multitasking"]
        }
        self.env_vars: Dict[str, str] = {"USER": username, "HOME": "/home/" + username}
        self.command_history: List[str] = []
        self.start_time = time.time()
        # seed some files
        self.files["/readme.txt"] = {
            "data": b"SimpleOS readme: use ls, cat, whoami, echo, write, loadasm, run\n",
            "permissions": 0o644,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        self.files["/hello.bin"] = {
            "data": b"",  # maybe an assembled program can be stored here
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        self.files["/"] = {
            "data": b"",  # Directory marker
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
    def syscall(self, cpu: "CPU"):
        num = cpu.reg_read(0)
        a1 = cpu.reg_read(1)
        a2 = cpu.reg_read(2)
        a3 = cpu.reg_read(3)
        logger.debug("Kernel syscall %d args=%08x %08x %08x", num, a1, a2, a3)
        if num == 1:  # WRITE(fd, buf_addr, len)
            fd = a1
            addr = a2
            length = a3
            if fd == 1:
                # write to host stdout
                try:
                    data = cpu.mem.dump(addr, length)
                except Exception:
                    cpu.reg_write(0, 0)
                    return
                try:
                    sys.stdout.write(data.decode("utf-8", errors="replace"))
                    sys.stdout.flush()
                except Exception:
                    sys.stdout.write(str(data))
                cpu.reg_write(0, length)
            else:
                cpu.reg_write(0, 0)
        elif num == 2:  # READ(fd, buf_addr, len)
            fd = a1
            addr = a2
            length = a3
            if fd == 0:
                # blocking read from stdin up to length bytes
                s = sys.stdin.read(1)  # keep simple: read one char
                if s == "":
                    cpu.reg_write(0, 0)
                else:
                    b = s.encode("utf-8")[0]
                    cpu.mem.write_byte(addr, b)
                    cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 3:  # LIST_DIR(dir_addr, out_addr)
            # ignore dir_arg and just list root
            out_addr = a2
            # Format: null-separated filenames, terminated by double null
            names = "\0".join(self.files.keys()) + "\0\0"
            data = names.encode("utf-8")
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(self.files))
        elif num == 4:  # WHOAMI(out_addr)
            out_addr = a1
            data = (self.username + "\0").encode("utf-8")
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 5:  # ALLOC(addr, size)
            addr = a1
            size = a2
            try:
                cpu.mem.register_region(addr, size)
                cpu.reg_write(0, 1)
            except Exception:
                cpu.reg_write(0, 0)
        elif num == 6:  # LOAD_FILE(filename_addr, dest_addr)
            faddr = a1
            dest = a2
            # Read filename (null-terminated)
            fname = self.read_cstring(cpu.mem, faddr)
            if fname in self.files:
                data = self.files[fname]["data"]
                cpu.mem.load_bytes(dest, data)
                cpu.reg_write(0, len(data))
            else:
                cpu.reg_write(0, 0)
        elif num == 7:  # STORE_FILE(filename_addr, src_addr, len)
            fname = self.read_cstring(cpu.mem, a1)
            src = a2
            length = a3
            try:
                data = cpu.mem.dump(src, length)
                self.files[fname] = {
                    "data": data,
                    "permissions": 0o644,
                    "created_time": time.time(),
                    "modified_time": time.time()
                }
                cpu.reg_write(0, len(data))
            except Exception:
                cpu.reg_write(0, 0)
        elif num == 8:  # HALT
            cpu.halted = True
            cpu.reg_write(0, 1)
        elif num == 9:  # GET_TIME
            # Return time in milliseconds since epoch
            cpu.reg_write(0, int(time.time() * 1000) & 0xFFFFFFFF)
        elif num == 10:  # SLEEP
            # Sleep for a1 milliseconds
            time.sleep(a1 / 1000.0)
            cpu.reg_write(0, 1)
        elif num == 11:  # CREATE_PROCESS
            name_addr = a1
            entry_addr = a2
            mem_size = a3
            name = self.read_cstring(cpu.mem, name_addr)
            pid = self.next_pid
            self.next_pid += 1
            process = Process(pid, name, entry_addr, mem_size)
            self.processes[pid] = process
            cpu.reg_write(0, pid)
        elif num == 12:  # EXIT_PROCESS
            # In a real system, we would terminate the current process
            # For simplicity, we'll just halt the CPU
            cpu.halted = True
            cpu.reg_write(0, 1)
        elif num == 13:  # YIELD
            # In a real system, we would switch to another process
            # For simplicity, we'll just return
            cpu.reg_write(0, 1)
        elif num == 14:  # GET_PID
            # Return current process ID (for now, always 1)
            cpu.reg_write(0, 1)
        elif num == 15:  # KILL_PROCESS
            pid = a1
            if pid in self.processes:
                self.processes[pid].state = ProcessState.TERMINATED
                del self.processes[pid]
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 16:  # LIST_PROCESSES
            out_addr = a1
            # Format process list as string
            process_list = []
            for pid, proc in self.processes.items():
                process_list.append(f"{pid}: {proc.name} ({proc.state.name})")
            data = "\n".join(process_list).encode("utf-8") + b"\0"
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 17:  # CHMOD
            fname = self.read_cstring(cpu.mem, a1)
            mode = a2
            if fname in self.files:
                self.files[fname]["permissions"] = mode
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 18:  # MKDIR
            dirname = self.read_cstring(cpu.mem, a1)
            if dirname not in self.files:
                self.files[dirname] = {
                    "data": b"",
                    "permissions": 0o755,
                    "created_time": time.time(),
                    "modified_time": time.time()
                }
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 19:  # REMOVE
            fname = self.read_cstring(cpu.mem, a1)
            if fname in self.files:
                del self.files[fname]
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 20:  # COPY
            src_name = self.read_cstring(cpu.mem, a1)
            dest_name = self.read_cstring(cpu.mem, a2)
            if src_name in self.files:
                self.files[dest_name] = self.files[src_name].copy()
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 21:  # MOVE
            src_name = self.read_cstring(cpu.mem, a1)
            dest_name = self.read_cstring(cpu.mem, a2)
            if src_name in self.files:
                self.files[dest_name] = self.files[src_name]
                del self.files[src_name]
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 22:  # STAT
            fname = self.read_cstring(cpu.mem, a1)
            stat_buf_addr = a2
            if fname in self.files:
                file_info = self.files[fname]
                # Pack file stats into memory
                # Format: size(4), permissions(4), created_time(8), modified_time(8)
                stat_data = bytearray(24)
                size = len(file_info["data"])
                permissions = file_info["permissions"]
                created_time = int(file_info["created_time"] * 1000) & 0xFFFFFFFFFFFFFFFF
                modified_time = int(file_info["modified_time"] * 1000) & 0xFFFFFFFFFFFFFFFF
                stat_data[0:4] = itob_le(size)
                stat_data[4:8] = itob_le(permissions)
                stat_data[8:16] = struct.pack('<Q', created_time)
                stat_data[16:24] = struct.pack('<Q', modified_time)
                cpu.mem.load_bytes(stat_buf_addr, stat_data)
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 23:  # EXEC
            fname = self.read_cstring(cpu.mem, a1)
            if fname in self.files:
                # Load program into memory at address 0x1000
                data = self.files[fname]["data"]
                cpu.mem.load_bytes(0x1000, data)
                cpu.pc = 0x1000
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 24:  # REBOOT
            # Signal reboot to shell
            cpu.halted = True
            cpu.reg_write(0, 0xDEADBEEF)  # Special reboot code
        elif num == 25:  # GET_BIOS_INFO
            out_addr = a1
            # Return BIOS info as string
            bios_info = "SimpleOS BIOS v1.1\nMemory: 32MB\nCPU: 32-bit with FPU\n"
            data = bios_info.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 26:  # GENERATE_RANDOM
            # Generate random number
            random_val = random.randint(0, 0xFFFFFFFF)
            cpu.reg_write(0, random_val)
        elif num == 27:  # GET_SYSTEM_INFO
            out_addr = a1
            # Return system info as string
            sys_info = f"OS: {self.system_info['os_name']} {self.system_info['version']}\n"
            sys_info += f"Architecture: {self.system_info['architecture']}\n"
            sys_info += f"Features: {', '.join(self.system_info['features'])}\n"
            data = sys_info.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 28:  # SET_ENV_VAR
            var_addr = a1
            val_addr = a2
            var_name = self.read_cstring(cpu.mem, var_addr)
            var_value = self.read_cstring(cpu.mem, val_addr)
            self.env_vars[var_name] = var_value
            cpu.reg_write(0, 1)
        elif num == 29:  # GET_ENV_VAR
            var_addr = a1
            out_addr = a2
            var_name = self.read_cstring(cpu.mem, var_addr)
            var_value = self.env_vars.get(var_name, "")
            data = (var_value + "\0").encode("utf-8")
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 30:  # CLEAR_SCREEN
            # Simulate clearing the screen by printing newlines
            print("\033[H\033[J", end="")
            cpu.reg_write(0, 1)
        elif num == 31:  # SHOW_HISTORY
            out_addr = a1
            # Format history as string
            hist_str = "\n".join(self.command_history) + "\n"
            data = hist_str.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 32:  # PING
            host_addr = a1
            host_name = self.read_cstring(cpu.mem, host_addr)
            # Simulate ping response
            cpu.reg_write(0, 1) # Success
        elif num == 33:  # UPTIME
            uptime_seconds = time.time() - self.start_time
            cpu.reg_write(0, int(uptime_seconds)) # Return uptime in seconds
        elif num == 34:  # DF
            out_addr = a1
            # Simulated disk usage
            df_output = "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1       32MB   2MB  30MB  6% /\n"
            data = df_output.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 35:  # TOP
            out_addr = a1
            # Simulated top output
            top_output = "  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND\n    1 root      20   0  12345   1234   1234 S   0.0  0.1   0:00.01 init\n"
            data = top_output.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 36:  # FIND
            path_addr = a1
            pattern_addr = a2
            path = self.read_cstring(cpu.mem, path_addr)
            pattern = self.read_cstring(cpu.mem, pattern_addr)
            # Simulated find result
            find_result = "/readme.txt\n/hello.bin\n"
            data = find_result.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(a3, data) # Output to third argument address
            cpu.reg_write(0, len(data))
        elif num == 37:  # CALC
            num1 = a1
            num2 = a2
            operation = a3
            # Perform calculation
            result = 0
            if operation == 1: # ADD
                result = num1 + num2
            elif operation == 2: # SUB
                result = num1 - num2
            elif operation == 3: # MUL
                result = num1 * num2
            elif operation == 4: # DIV
                if num2 != 0:
                    result = num1 // num2
                else:
                    result = 0 # Division by zero
            cpu.reg_write(0, result)
        elif num == 38:  # DATE
            # Return current date as string
            date_str = time.strftime("%Y-%m-%d", time.localtime())
            out_addr = a1
            data = (date_str + "\0").encode("utf-8")
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 39:  # TIME
            # Return current time as string
            time_str = time.strftime("%H:%M:%S", time.localtime())
            out_addr = a1
            data = (time_str + "\0").encode("utf-8")
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 40:  # TYPE
            file_addr = a1
            fname = self.read_cstring(cpu.mem, file_addr)
            if fname in self.files:
                data = self.files[fname]["data"]
                try:
                    cpu.mem.load_bytes(a2, data) # Load data into buffer at a2
                    cpu.reg_write(0, len(data))
                except Exception:
                    cpu.reg_write(0, 0)
            else:
                cpu.reg_write(0, 0)
        elif num == 41:  # CURL
            url_addr = a1
            url = self.read_cstring(cpu.mem, url_addr)
            # Simulate curl response
            cpu.reg_write(0, 1) # Success
        elif num == 42:  # WGET
            url_addr = a1
            url = self.read_cstring(cpu.mem, url_addr)
            # Simulate wget response
            cpu.reg_write(0, 1) # Success
        elif num == 43:  # GREP
            pattern_addr = a1
            file_addr = a2
            pattern = self.read_cstring(cpu.mem, pattern_addr)
            fname = self.read_cstring(cpu.mem, file_addr)
            # Simulated grep result
            grep_result = "SimpleOS readme: use ls, cat, whoami, echo, write, loadasm, run\n"
            data = grep_result.encode("utf-8") + b"\0"
            cpu.mem.load_bytes(a3, data) # Output to third argument address
            cpu.reg_write(0, len(data))
        elif num == 44:  # WC
            file_addr = a1
            fname = self.read_cstring(cpu.mem, file_addr)
            if fname in self.files:
                data = self.files[fname]["data"]
                # Count lines, words, chars
                lines = data.count(b'\n')
                words = len(data.split())
                chars = len(data)
                # Pack result into memory (e.g., 4 bytes for lines, 4 for words, 4 for chars)
                # For simplicity, we'll just return lines
                result = lines
                cpu.reg_write(0, result)
            else:
                cpu.reg_write(0, 0)
        else:
            logger.warning("Unknown syscall %d", num)
            cpu.reg_write(0, 0)
    @staticmethod
    def read_cstring(mem: Memory, addr: int, maxlen: int = 1024) -> str:
        # read until null byte
        out = []
        for i in range(maxlen):
            try:
                b = mem.read_byte(addr + i)
            except Exception:
                break
            if b == 0:
                break
            out.append(chr(b))
        return "".join(out)

# ---------------------------
# CPU core with syscall hook
# ---------------------------
class CPU:
    def __init__(self, memory: Optional[Memory] = None, kernel: Optional[Kernel] = None):
        self.mem = memory if memory is not None else Memory()
        self.regs = [0] * NUM_REGS
        self.fpu_regs = [0.0] * NUM_FPU_REGS
        self.pc = 0
        self.flags = 0
        self.halted = False
        self.tracing = False
        self.kernel = kernel
        self.interrupt_vector = [0] * 256  # Interrupt vector table
        self.interrupt_enabled = True
        # initialize SP to top aligned
        top_sp = (self.mem.size - 4) // 4 * 4
        self.reg_write(REG_SP, top_sp)
        logger.debug("CPU created: SP=%08x", self.reg_read(REG_SP))
    def reg_read(self, idx: int) -> int:
        if idx < 0 or idx >= NUM_REGS:
            raise IndexError("Register index out of range")
        return self.regs[idx] & 0xFFFFFFFF
    def reg_write(self, idx: int, val: int):
        if idx < 0 or idx >= NUM_REGS:
            raise IndexError("Register index out of range")
        self.regs[idx] = val & 0xFFFFFFFF
    def fpu_reg_read(self, idx: int) -> float:
        if idx < 0 or idx >= NUM_FPU_REGS:
            raise IndexError("FPU register index out of range")
        return self.fpu_regs[idx]
    def fpu_reg_write(self, idx: int, val: float):
        if idx < 0 or idx >= NUM_FPU_REGS:
            raise IndexError("FPU register index out of range")
        self.fpu_regs[idx] = val
    def set_flag(self, mask: int):
        self.flags |= mask
    def clear_flag(self, mask: int):
        self.flags &= ~mask
    def test_flag(self, mask: int) -> bool:
        return bool(self.flags & mask)
    def update_zero_and_neg_flags(self, val: int):
        if (val & 0xFFFFFFFF) == 0:
            self.set_flag(FLAG_ZERO)
        else:
            self.clear_flag(FLAG_ZERO)
        if (val >> 31) & 1:
            self.set_flag(FLAG_NEG)
        else:
            self.clear_flag(FLAG_NEG)
    # stack grows down
    def push_word(self, val: int):
        sp = (self.reg_read(REG_SP) - 4) & 0xFFFFFFFF
        if sp + 4 > self.mem.size:
            raise MemoryError("Stack overflow")
        self.reg_write(REG_SP, sp)
        self.mem.write_word(sp, val)
    def pop_word(self) -> int:
        sp = self.reg_read(REG_SP)
        if sp + 4 > self.mem.size:
            raise MemoryError("Stack underflow")
        val = self.mem.read_word(sp)
        self.reg_write(REG_SP, (sp + 4) & 0xFFFFFFFF)
        return val
    def fetch(self) -> int:
        if self.pc + 4 > self.mem.size:
            raise MemoryError("PC out of memory range")
        return self.mem.read_word(self.pc)
    def step(self):
        if self.halted:
            return
        instr = self.fetch()
        opcode, dst, src, imm16 = unpack_instruction(instr)
        next_pc = (self.pc + 4) & 0xFFFFFFFF
        if self.tracing:
            logger.info("PC=%08x %s dst=%d src=%d imm=%d", self.pc, OPCODE_NAME.get(opcode, f"OP_{opcode:02x}"), dst, src, to_signed16(imm16))
        if opcode == OP_NOP or opcode == OP_NOP2:
            pass
        elif opcode == OP_MOV:
            self.reg_write(dst, self.reg_read(src))
            self.update_zero_and_neg_flags(self.reg_read(dst))
        elif opcode == OP_LOADI:
            self.reg_write(dst, (to_signed16(imm16) & 0xFFFFFFFF))
            self.update_zero_and_neg_flags(self.reg_read(dst))
        elif opcode == OP_LOAD:
            addr = imm16
            val = self.mem.read_word(addr)
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_STORE:
            addr = imm16
            val = self.reg_read(dst)  # dst field holds source reg for store
            self.mem.write_word(addr, val)
        elif opcode == OP_ADD:
            a = self.reg_read(dst)
            b = self.reg_read(src)
            res = (a + b) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SUB:
            a = self.reg_read(dst)
            b = self.reg_read(src)
            res = (a - b) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_AND:
            res = self.reg_read(dst) & self.reg_read(src)
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_OR:
            res = self.reg_read(dst) | self.reg_read(src)
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_XOR:
            res = self.reg_read(dst) ^ self.reg_read(src)
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_NOT:
            res = (~self.reg_read(dst)) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SHL:
            s = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            res = (s << bits) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SHR:
            s = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            res = (s >> bits) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_JMP:
            next_pc = imm16
        elif opcode == OP_JZ:
            if self.test_flag(FLAG_ZERO):
                next_pc = imm16
        elif opcode == OP_JNZ:
            if not self.test_flag(FLAG_ZERO):
                next_pc = imm16
        elif opcode == OP_JE:
            if self.test_flag(FLAG_ZERO):
                next_pc = imm16
        elif opcode == OP_JNE:
            if not self.test_flag(FLAG_ZERO):
                next_pc = imm16
        elif opcode == OP_JL:
            # Jump if less (SF != OF)
            if (self.test_flag(FLAG_NEG) != self.test_flag(FLAG_OVERFLOW)):
                next_pc = imm16
        elif opcode == OP_JG:
            # Jump if greater (ZF=0 and SF=OF)
            if not self.test_flag(FLAG_ZERO) and (self.test_flag(FLAG_NEG) == self.test_flag(FLAG_OVERFLOW)):
                next_pc = imm16
        elif opcode == OP_JLE:
            # Jump if less or equal (ZF=1 or SF != OF)
            if self.test_flag(FLAG_ZERO) or (self.test_flag(FLAG_NEG) != self.test_flag(FLAG_OVERFLOW)):
                next_pc = imm16
        elif opcode == OP_JGE:
            # Jump if greater or equal (SF=OF)
            if (self.test_flag(FLAG_NEG) == self.test_flag(FLAG_OVERFLOW)):
                next_pc = imm16
        elif opcode == OP_CMP:
            a = self.reg_read(dst)
            b = self.reg_read(src)
            res = (a - b) & 0xFFFFFFFF
            if res == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
            if (res >> 31) & 1:
                self.set_flag(FLAG_NEG)
            else:
                self.clear_flag(FLAG_NEG)
            # Set overflow flag for signed comparison
            if (a ^ b) & (a ^ res) & 0x80000000:
                self.set_flag(FLAG_OVERFLOW)
            else:
                self.clear_flag(FLAG_OVERFLOW)
        elif opcode == OP_TEST:
            res = self.reg_read(dst) & self.reg_read(src)
            if res == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
            if (res >> 31) & 1:
                self.set_flag(FLAG_NEG)
            else:
                self.clear_flag(FLAG_NEG)
        elif opcode == OP_PUSH:
            self.push_word(self.reg_read(dst))
        elif opcode == OP_POP:
            val = self.pop_word()
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_CALL:
            self.push_word(next_pc)
            next_pc = imm16
        elif opcode == OP_RET:
            ret = self.pop_word()
            next_pc = ret
        elif opcode == OP_HALT:
            self.halted = True
        elif opcode == OP_INC:
            v = (self.reg_read(dst) + 1) & 0xFFFFFFFF
            self.reg_write(dst, v)
            self.update_zero_and_neg_flags(v)
        elif opcode == OP_DEC:
            v = (self.reg_read(dst) - 1) & 0xFFFFFFFF
            self.reg_write(dst, v)
            self.update_zero_and_neg_flags(v)
        elif opcode == OP_OUT:
            v = self.reg_read(dst) & 0xFF
            try:
                sys.stdout.write(chr(v))
                sys.stdout.flush()
            except Exception:
                sys.stdout.write(f"<{v}>")
        elif opcode == OP_IN:
            try:
                ch = sys.stdin.read(1)
                if ch == "":
                    self.reg_write(dst, 0)
                else:
                    self.reg_write(dst, ord(ch[0]))
            except Exception:
                self.reg_write(dst, 0)
        elif opcode == OP_MUL:
            a = self.reg_read(dst)
            b = self.reg_read(src)
            res = (a * b) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_IMUL:
            a = to_signed32(self.reg_read(dst))
            b = to_signed32(self.reg_read(src))
            res = (a * b) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_DIV:
            a = self.reg_read(dst)
            b = self.reg_read(src)
            if b == 0:
                self.reg_write(dst, 0)
                self.set_flag(FLAG_OVERFLOW)
            else:
                self.reg_write(dst, (a // b) & 0xFFFFFFFF)
            self.update_zero_and_neg_flags(self.reg_read(dst))
        elif opcode == OP_IDIV:
            a = to_signed32(self.reg_read(dst))
            b = to_signed32(self.reg_read(src))
            if b == 0:
                self.reg_write(dst, 0)
                self.set_flag(FLAG_OVERFLOW)
            else:
                self.reg_write(dst, (a // b) & 0xFFFFFFFF)
            self.update_zero_and_neg_flags(self.reg_read(dst))
        elif opcode == OP_MOD:
            a = self.reg_read(dst)
            b = self.reg_read(src)
            if b == 0:
                self.reg_write(dst, 0)
                self.set_flag(FLAG_OVERFLOW)
            else:
                self.reg_write(dst, (a % b) & 0xFFFFFFFF)
            self.update_zero_and_neg_flags(self.reg_read(dst))
        elif opcode == OP_SYSCALL:
            if self.kernel is None:
                logger.error("SYSCALL but no kernel attached")
                self.reg_write(0, 0)
            else:
                # Kernel will inspect regs and may modify mem/regs
                self.kernel.syscall(self)
        elif opcode == OP_INT:
            # Software interrupt
            if self.interrupt_enabled:
                vector = imm16 & 0xFF
                if vector < len(self.interrupt_vector):
                    handler = self.interrupt_vector[vector]
                    if handler != 0:
                        # Save current PC and flags
                        self.push_word(self.pc)
                        self.push_word(self.flags)
                        # Jump to interrupt handler
                        next_pc = handler
                        # Disable further interrupts
                        self.interrupt_enabled = False
        elif opcode == OP_IRET:
            # Interrupt return
            flags = self.pop_word()
            ret_addr = self.pop_word()
            self.flags = flags
            next_pc = ret_addr
            # Re-enable interrupts
            self.interrupt_enabled = True
        elif opcode == OP_CLC:
            self.clear_flag(FLAG_CARRY)
        elif opcode == OP_STC:
            self.set_flag(FLAG_CARRY)
        elif opcode == OP_CLI:
            self.interrupt_enabled = False
        elif opcode == OP_STI:
            self.interrupt_enabled = True
        elif opcode == OP_PUSHF:
            self.push_word(self.flags)
        elif opcode == OP_POPF:
            self.flags = self.pop_word()
        elif opcode == OP_ENTER:
            # Create stack frame
            size = imm16
            self.push_word(self.reg_read(REG_SP))
            self.reg_write(REG_SP, (self.reg_read(REG_SP) - size) & 0xFFFFFFFF)
        elif opcode == OP_LEAVE:
            # Destroy stack frame
            self.reg_write(REG_SP, self.pop_word())
        elif opcode == OP_LEA:
            # Load effective address
            addr = imm16
            self.reg_write(dst, addr)
        elif opcode == OP_MOVZX:
            # Move with zero extension (byte to word)
            val = self.reg_read(src) & 0xFF
            self.reg_write(dst, val)
        elif opcode == OP_MOVSX:
            # Move with sign extension (byte to word)
            val = self.reg_read(src) & 0xFF
            if val & 0x80:
                val |= 0xFFFFFF00
            self.reg_write(dst, val)
        elif opcode == OP_ADC:
            # Add with carry
            a = self.reg_read(dst)
            b = self.reg_read(src)
            carry = 1 if self.test_flag(FLAG_CARRY) else 0
            res = (a + b + carry) & 0xFFFFFFFF
            if (a + b + carry) > 0xFFFFFFFF:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SBB:
            # Subtract with borrow
            a = self.reg_read(dst)
            b = self.reg_read(src)
            borrow = 1 if self.test_flag(FLAG_CARRY) else 0
            res = (a - b - borrow) & 0xFFFFFFFF
            if (a - b - borrow) < 0:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_ROL:
            # Rotate left
            val = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            res = ((val << bits) | (val >> (32 - bits))) & 0xFFFFFFFF
            self.reg_write(dst, res)
        elif opcode == OP_ROR:
            # Rotate right
            val = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            res = ((val >> bits) | (val << (32 - bits))) & 0xFFFFFFFF
            self.reg_write(dst, res)
        elif opcode == OP_BT:
            # Bit Test
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            bit_val = (val >> bit_pos) & 1
            if bit_val:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_BTS:
            # Bit Test and Set
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            old_bit = (val >> bit_pos) & 1
            new_val = val | (1 << bit_pos)
            self.reg_write(dst, new_val)
            if old_bit:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_BTR:
            # Bit Test and Reset
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            old_bit = (val >> bit_pos) & 1
            new_val = val & ~(1 << bit_pos)
            self.reg_write(dst, new_val)
            if old_bit:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_NEG:
            # Negate
            val = self.reg_read(dst)
            res = (-val) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_CBW:
            # Convert Byte to Word
            val = self.reg_read(dst) & 0xFF
            if val & 0x80:
                self.reg_write(dst, val | 0xFFFFFF00)
            else:
                self.reg_write(dst, val & 0x000000FF)
        elif opcode == OP_CWD:
            # Convert Word to Doubleword
            val = self.reg_read(dst) & 0xFFFF
            if val & 0x8000:
                self.reg_write(dst, val | 0xFFFF0000)
            else:
                self.reg_write(dst, val & 0x0000FFFF)
        elif opcode == OP_CWDQ:
            # Convert Doubleword to Quadword
            val = self.reg_read(dst)
            if val & 0x80000000:
                self.reg_write(dst, val | 0xFFFFFFFF00000000)
            else:
                self.reg_write(dst, val & 0x00000000FFFFFFFF)
        # FPU Instructions
        elif opcode == OP_FLD:
            # Load float from memory
            addr = imm16
            bits = self.mem.read_word(addr)
            val = bits_to_float(bits)
            # Push onto FPU stack (shift registers)
            for i in range(NUM_FPU_REGS - 1, 0, -1):
                self.fpu_reg_write(i, self.fpu_reg_read(i - 1))
            self.fpu_reg_write(0, val)
        elif opcode == OP_FST:
            # Store float to memory
            addr = imm16
            val = self.fpu_reg_read(0)
            bits = float_to_bits(val)
            self.mem.write_word(addr, bits)
        elif opcode == OP_FADD:
            # Add floating point numbers
            a = self.fpu_reg_read(dst)
            b = self.fpu_reg_read(src)
            res = a + b
            self.fpu_reg_write(dst, res)
        elif opcode == OP_FSUB:
            # Subtract floating point numbers
            a = self.fpu_reg_read(dst)
            b = self.fpu_reg_read(src)
            res = a - b
            self.fpu_reg_write(dst, res)
        elif opcode == OP_FMUL:
            # Multiply floating point numbers
            a = self.fpu_reg_read(dst)
            b = self.fpu_reg_read(src)
            res = a * b
            self.fpu_reg_write(dst, res)
        elif opcode == OP_FDIV:
            # Divide floating point numbers
            a = self.fpu_reg_read(dst)
            b = self.fpu_reg_read(src)
            if b != 0.0:
                res = a / b
            else:
                res = float('inf') if a >= 0 else float('-inf')
            self.fpu_reg_write(dst, res)
        elif opcode == OP_FCOMP:
            # Compare floating point numbers
            a = self.fpu_reg_read(dst)
            b = self.fpu_reg_read(src)
            if a == b:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
            if a < b:
                self.set_flag(FLAG_NEG)
            else:
                self.clear_flag(FLAG_NEG)
        elif opcode == OP_FCHS:
            # Change sign
            val = self.fpu_reg_read(dst)
            self.fpu_reg_write(dst, -val)
        elif opcode == OP_FABS:
            # Absolute value
            val = self.fpu_reg_read(dst)
            self.fpu_reg_write(dst, abs(val))
        elif opcode == OP_FSQRT:
            # Square root
            val = self.fpu_reg_read(dst)
            if val >= 0:
                self.fpu_reg_write(dst, math.sqrt(val))
            else:
                self.fpu_reg_write(dst, float('nan'))
        elif opcode == OP_FSTP:
            # Store and pop
            addr = imm16
            val = self.fpu_reg_read(0)
            bits = float_to_bits(val)
            self.mem.write_word(addr, bits)
            # Pop from FPU stack (shift registers)
            for i in range(NUM_FPU_REGS - 1):
                self.fpu_reg_write(i, self.fpu_reg_read(i + 1))
            self.fpu_reg_write(NUM_FPU_REGS - 1, 0.0)
        elif opcode == OP_FLDZ:
            # Load zero
            self.fpu_reg_write(dst, 0.0)
        elif opcode == OP_FLD1:
            # Load one
            self.fpu_reg_write(dst, 1.0)
        elif opcode == OP_FLDPI:
            # Load pi
            self.fpu_reg_write(dst, math.pi)
        elif opcode == OP_FLDLG2:
            # Load log10(2)
            self.fpu_reg_write(dst, math.log10(2))
        elif opcode == OP_FLDLN2:
            # Load ln(2)
            self.fpu_reg_write(dst, math.log(2))
        elif opcode == OP_FXCH:
            # Exchange ST(0) with ST(i)
            temp = self.fpu_reg_read(0)
            self.fpu_reg_write(0, self.fpu_reg_read(src))
            self.fpu_reg_write(src, temp)
        elif opcode == OP_FSTSW:
            # Store status word
            self.reg_write(dst, self.flags)
        elif opcode == OP_FCLEX:
            # Clear exceptions
            self.clear_flag(FLAG_OVERFLOW)
        elif opcode == OP_FILD:
            # Load integer from memory and convert to float
            addr = imm16
            val = self.mem.read_word(addr)
            float_val = float(to_signed32(val))
            # Push onto FPU stack
            for i in range(NUM_FPU_REGS - 1, 0, -1):
                self.fpu_reg_write(i, self.fpu_reg_read(i - 1))
            self.fpu_reg_write(0, float_val)
        elif opcode == OP_FIST:
            # Store float as integer to memory
            addr = imm16
            val = self.fpu_reg_read(0)
            int_val = int(val) & 0xFFFFFFFF
            self.mem.write_word(addr, int_val)
        elif opcode == OP_FISTP:
            # Store float as integer to memory and pop
            addr = imm16
            val = self.fpu_reg_read(0)
            int_val = int(val) & 0xFFFFFFFF
            self.mem.write_word(addr, int_val)
            # Pop from FPU stack
            for i in range(NUM_FPU_REGS - 1):
                self.fpu_reg_write(i, self.fpu_reg_read(i + 1))
            self.fpu_reg_write(NUM_FPU_REGS - 1, 0.0)
        # Additional Instructions
        elif opcode == OP_CLD:
            self.clear_flag(FLAG_DIR)
        elif opcode == OP_STD:
            self.set_flag(FLAG_DIR)
        elif opcode == OP_LAHF:
            # Load AH from flags
            ah = self.flags & 0xFF
            self.reg_write(0, ah) # Store AH in R0
        elif opcode == OP_SAHF:
            # Store AH to flags
            ah = self.reg_read(0) & 0xFF
            self.flags = (self.flags & 0xFFFFFF00) | ah
        elif opcode == OP_INTO:
            # Interrupt on overflow
            if self.test_flag(FLAG_OVERFLOW):
                # Simulate interrupt
                self.push_word(self.pc)
                self.push_word(self.flags)
                self.pc = 0x00000004 # Simulate interrupt vector 4
                self.interrupt_enabled = False
        elif opcode == OP_AAM:
            # ASCII Adjust After Multiply
            al = self.reg_read(0) & 0xFF
            ah = al // 10
            al = al % 10
            self.reg_write(0, (ah << 8) | al)
            self.update_zero_and_neg_flags(al)
        elif opcode == OP_AAD:
            # ASCII Adjust Before Divide
            al = self.reg_read(0) & 0xFF
            ah = (self.reg_read(0) >> 8) & 0xFF
            result = (ah * 10) + al
            self.reg_write(0, result & 0xFF)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_XLAT:
            # Table Look-up Translation
            # Uses AL as index into DS:[BX] table
            # For simplicity, we'll just return AL
            # In a real system, this would read from memory
            pass # Placeholder
        elif opcode == OP_XCHG:
            # Exchange Register/Memory with Register
            temp = self.reg_read(dst)
            self.reg_write(dst, self.reg_read(src))
            self.reg_write(src, temp)
        elif opcode == OP_CMPXCHG:
            # Compare and Exchange
            # Compare EAX with operand, if equal, store EDX in operand
            # Simplified for R0/R1
            eax = self.reg_read(0)
            ecx = self.reg_read(1)
            if eax == ecx:
                self.reg_write(1, eax) # Store EAX in ECX
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_BSF:
            # Bit Scan Forward
            val = self.reg_read(dst)
            if val == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
                # Find position of lowest set bit
                pos = 0
                while (val & 1) == 0:
                    val >>= 1
                    pos += 1
                self.reg_write(src, pos) # Store position in src register
        elif opcode == OP_BSR:
            # Bit Scan Reverse
            val = self.reg_read(dst)
            if val == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
                # Find position of highest set bit
                pos = 31
                while (val & (1 << pos)) == 0:
                    pos -= 1
                self.reg_write(src, pos) # Store position in src register
        elif opcode == OP_LAR:
            # Load Access Rights
            # Simplified for demonstration
            self.reg_write(dst, 0x00000000) # Return dummy access rights
        elif opcode == OP_LSL:
            # Load Segment Limit
            # Simplified for demonstration
            self.reg_write(dst, 0x00000000) # Return dummy limit
        elif opcode == OP_SLDT:
            # Store Local Descriptor Table
            # Simplified for demonstration
            self.reg_write(dst, 0x00000000) # Return dummy LDT base
        elif opcode == OP_STR:
            # Store Task Register
            # Simplified for demonstration
            self.reg_write(dst, 0x00000000) # Return dummy TR base
        elif opcode == OP_LLDT:
            # Load Local Descriptor Table
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_LTR:
            # Load Task Register
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_VERR:
            # Verify Real Mode Segment
            # Simplified for demonstration
            self.set_flag(FLAG_ZERO) # Assume success
        elif opcode == OP_VERW:
            # Verify Writeable Real Mode Segment
            # Simplified for demonstration
            self.set_flag(FLAG_ZERO) # Assume success
        elif opcode == OP_SGDT:
            # Store Global Descriptor Table
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SIDT:
            # Store Interrupt Descriptor Table
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_LGDT:
            # Load Global Descriptor Table
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_LIDT:
            # Load Interrupt Descriptor Table
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SMSW:
            # Store Machine Status Word
            # Simplified for demonstration
            self.reg_write(dst, self.flags) # Return flags
        elif opcode == OP_LMSW:
            # Load Machine Status Word
            # Simplified for demonstration
            self.flags = self.reg_read(dst) # Load flags
        elif opcode == OP_CLTS:
            # Clear Task Switched Flag
            # Simplified for demonstration
            self.clear_flag(FLAG_NT)
        elif opcode == OP_INVD:
            # Invalidate Cache
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_WBINVD:
            # Write Back and Invalidate Cache
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_INVLPG:
            # Invalidate TLB Entry
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_INVPCID:
            # Invalidate Process Context Identifier
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_VMCALL:
            # VM Call
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_VMLAUNCH:
            # VM Launch
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_VMRESUME:
            # VM Resume
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_VMXOFF:
            # VM Exit
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_MONITOR:
            # Monitor Processor
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_MWAIT:
            # Monitor Wait
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_RDSEED:
            # Read Random Seed
            # Simplified for demonstration
            self.reg_write(dst, random.randint(0, 0xFFFFFFFF))
        elif opcode == OP_RDRAND:
            # Read Random Number
            # Simplified for demonstration
            self.reg_write(dst, random.randint(0, 0xFFFFFFFF))
        elif opcode == OP_CLAC:
            # Clear Access Control
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_STAC:
            # Set Access Control
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SKINIT:
            # Secure Key Initialization
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SVMEXIT:
            # SVM Exit
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SVMRET:
            # SVM Return
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SVMLOCK:
            # SVM Lock
            # Simplified for demonstration
            pass # Placeholder
        elif opcode == OP_SVMUNLOCK:
            # SVM Unlock
            # Simplified for demonstration
            pass # Placeholder
        else:
            raise NotImplementedError(f"Opcode {opcode:02x} not implemented")
        self.pc = next_pc & 0xFFFFFFFF
    def run(self, max_steps: Optional[int] = None, trace: bool = False):
        steps = 0
        self.tracing = trace
        try:
            while True:
                if self.halted:
                    break
                if max_steps is not None and steps >= max_steps:
                    break
                self.step()
                steps += 1
        finally:
            self.tracing = False
        return steps
    def dump_regs(self) -> str:
        lines = []
        for i in range(0, NUM_REGS, 4):
            lines.append(" ".join(f"R{j:02}={self.regs[j]:08x}" for j in range(i, i+4)))
        lines.append(f"PC={self.pc:08x} FLAGS={self.flags:02x}")
        # Add FPU registers
        fpu_lines = []
        for i in range(0, NUM_FPU_REGS, 2):
            fpu_lines.append(" ".join(f"ST{j}={self.fpu_regs[j]:.6f}" for j in range(i, min(i+2, NUM_FPU_REGS))))
        lines.extend(fpu_lines)
        return "\n".join(lines)
    def disassemble_at(self, addr: int, count: int = 8) -> List[str]:
        out = []
        pc = addr
        for _ in range(count):
            if pc + 4 > self.mem.size:
                break
            instr = self.mem.read_word(pc)
            opcode, dst, src, imm16 = unpack_instruction(instr)
            name = OPCODE_NAME.get(opcode, f"OP_{opcode:02x}")
            if name in ("LOADI",):
                s = f"{pc:08x}: {name} R{dst}, {to_signed16(imm16)}"
            elif name in ("JMP", "JZ", "JNZ", "JE", "JNE", "JL", "JG", "JLE", "JGE", "CALL", "LOAD", "STORE", "INT"):
                s = f"{pc:08x}: {name} {imm16} (0x{imm16:04x})"
            elif name in ("MOV","ADD","SUB","AND","OR","XOR","CMP","TEST","SHL","SHR","MUL","IMUL","DIV","IDIV","MOD","FADD","FSUB","FMUL","FDIV","FCOMP","FXCH","ADC","SBB","ROL","ROR","BT","BTS","BTR","BSF","BSR","LAR","LSL","SLDT","STR","LLDT","LTR","VERR","VERW","SGDT","SIDT","LGDT","LIDT","SMSW","LMSW","CLTS","INVD","WBINVD","INVLPG","INVPCID","VMCALL","VMLAUNCH","VMRESUME","VMXOFF","MONITOR","MWAIT","RDSEED","RDRAND","CLAC","STAC","SKINIT","SVMEXIT","SVMRET","SVMLOCK","SVMUNLOCK"):
                s = f"{pc:08x}: {name} R{dst}, R{src}"
            elif name in ("PUSH","POP","INC","DEC","NOT","OUT","IN","SYSCALL","FLD","FST","FCHS","FABS","FSQRT","FSTP","FLDZ","FLD1","FLDPI","FLDLG2","FLDLN2","FSTSW","FCLEX","FILD","FIST","FISTP","NEG","CBW","CWD","CWDQ","LAHF","SAHF","XCHG","CMPXCHG","IN","OUT","CLD","STD","INTO","AAM","AAD","XLAT"):
                s = f"{pc:08x}: {name} R{dst}"
            elif name in ("NOP", "NOP2", "RET", "HALT", "CLC", "STC", "CLI", "STI", "IRET", "LEAVE","NEG","CBW","CWD","CWDQ","CLD","STD","INTO","AAM","AAD","XLAT","IN","OUT"):
                s = f"{pc:08x}: {name}"
            elif name in ("PUSHF", "POPF"):
                s = f"{pc:08x}: {name}"
            elif name in ("ENTER"):
                s = f"{pc:08x}: {name} {imm16}"
            elif name in ("LEA", "MOVZX", "MOVSX"):
                s = f"{pc:08x}: {name} R{dst}, {imm16}"
            else:
                s = f"{pc:08x}: {name}"
            out.append(s)
            pc += 4
        return out

# ---------------------------
# Assembler (improved)
# ---------------------------
class AssemblerError(Exception):
    pass
class Assembler:
    """
    Simple two-pass assembler supporting labels, .org, .word, .byte, .float, .double
    Syntax:
    LABEL:
    MNEMONIC operands ; comment
    Registers: R0..R15, ST0..ST7
    """
    def __init__(self):
        self.labels: Dict[str, int] = {}
        self.orig = 0
        self.lines: List[Tuple[int, str]] = []
    def parse_reg(self, tok: str) -> int:
        tok = tok.upper().strip()
        if tok.startswith("R"):
            idx = int(tok[1:])
            if idx < 0 or idx >= NUM_REGS:
                raise AssemblerError(f"Register out of range {tok}")
            return idx
        elif tok.startswith("ST"):
            idx = int(tok[2:])
            if idx < 0 or idx >= NUM_FPU_REGS:
                raise AssemblerError(f"FPU register out of range {tok}")
            return idx
        else:
            raise AssemblerError(f"Invalid register {tok}")
    def parse_imm(self, tok: str) -> int:
        tok = tok.strip()
        if tok.startswith("0x") or tok.startswith("0X"):
            return int(tok, 16) & 0xFFFFFFFF
        if tok.endswith("h") or tok.endswith("H"):
            return int(tok[:-1], 16) & 0xFFFFFFFF
        return int(tok, 0) & 0xFFFFFFFF
    def parse_float(self, tok: str) -> float:
        return float(tok)
    def first_pass(self, text: str):
        self.labels.clear()
        self.orig = 0
        self.lines = []
        pc = self.orig
        for i, raw in enumerate(text.splitlines()):
            line = raw.split(';',1)[0].strip()
            if not line:
                self.lines.append((i+1, raw))
                continue
            if ':' in line:
                parts = line.split(':',1)
                label = parts[0].strip()
                if label in self.labels:
                    raise AssemblerError(f"Duplicate label {label} on line {i+1}")
                self.labels[label] = pc
                line = parts[1].strip()
                if line == "":
                    self.lines.append((i+1, raw))
                    continue
            if line.startswith('.'):
                tokens = line.split()
                directive = tokens[0].lower()
                if directive == '.org':
                    if len(tokens) < 2:
                        raise AssemblerError("Missing .org operand")
                    pc = self.parse_imm(tokens[1])
                    self.orig = pc
                elif directive == '.word':
                    pc += 4
                elif directive == '.byte':
                    pc += 1
                elif directive == '.float':
                    pc += 4
                elif directive == '.double':
                    pc += 8
                else:
                    raise AssemblerError(f"Unknown directive {directive}")
                self.lines.append((i+1, raw))
            else:
                # instruction occupies 4 bytes
                pc += 4
                self.lines.append((i+1, raw))
        logger.debug("First pass labels: %s", self.labels)
    def second_pass(self) -> bytes:
        pc = self.orig
        out = bytearray()
        # pre-allocate if origin > 0
        if pc > 0:
            out.extend(bytearray(pc))
        for (ln, raw) in self.lines:
            line = raw.split(';',1)[0].strip()
            if not line:
                continue
            if ':' in line:
                line = line.split(':',1)[1].strip()
                if not line:
                    continue
            if line.startswith('.'):
                tokens = line.split()
                directive = tokens[0].lower()
                if directive == '.org':
                    pc = self.parse_imm(tokens[1])
                    if pc > len(out):
                        out.extend(bytearray(pc - len(out)))
                elif directive == '.word':
                    val = self.parse_imm(tokens[1])
                    if pc + 4 > len(out):
                        out.extend(bytearray(pc + 4 - len(out)))
                    out[pc:pc+4] = itob_le(val)
                    pc += 4
                elif directive == '.byte':
                    val = self.parse_imm(tokens[1]) & 0xFF
                    if pc + 1 > len(out):
                        out.extend(bytearray(pc + 1 - len(out)))
                    out[pc] = val
                    pc += 1
                elif directive == '.float':
                    val = self.parse_float(tokens[1])
                    bits = float_to_bits(val)
                    if pc + 4 > len(out):
                        out.extend(bytearray(pc + 4 - len(out)))
                    out[pc:pc+4] = itob_le(bits)
                    pc += 4
                elif directive == '.double':
                    val = self.parse_float(tokens[1])
                    if pc + 8 > len(out):
                        out.extend(bytearray(pc + 8 - len(out)))
                    # Pack as two 32-bit words (low, high)
                    packed = struct.pack('<d', val)
                    out[pc:pc+8] = packed
                    pc += 8
                else:
                    raise AssemblerError(f"Unsupported directive {directive} on line {ln}")
            else:
                tokens = shlex.split(line)
                if not tokens:
                    continue
                mnem = tokens[0].upper()
                args_part = line[len(tokens[0]):].strip()
                args = [a.strip() for a in args_part.split(',') if a.strip()!='']
                opcode = NAME_OPCODE.get(mnem)
                if opcode is None:
                    raise AssemblerError(f"Unknown mnemonic {mnem} on line {ln}")
                word = 0
                if opcode in (OP_NOP, OP_NOP2, OP_RET, OP_HALT, OP_CLC, OP_STC, OP_CLI, OP_STI, OP_IRET, OP_LEAVE, OP_FLDZ, OP_FLD1, OP_FLDPI, OP_FLDLG2, OP_FLDLN2, OP_FCLEX, OP_NEG, OP_CBW, OP_CWD, OP_CWDQ, OP_CLD, OP_STD, OP_LAHF, OP_SAHF, OP_INTO, OP_AAM, OP_AAD, OP_XLAT, OP_XCHG, OP_CMPXCHG, OP_LAR, OP_LSL, OP_SLDT, OP_STR, OP_LLDT, OP_LTR, OP_VERR, OP_VERW, OP_SGDT, OP_SIDT, OP_LGDT, OP_LIDT, OP_SMSW, OP_LMSW, OP_CLTS, OP_INVD, OP_WBINVD, OP_INVLPG, OP_INVPCID, OP_VMCALL, OP_VMLAUNCH, OP_VMRESUME, OP_VMXOFF, OP_MONITOR, OP_MWAIT, OP_RDSEED, OP_RDRAND, OP_CLAC, OP_STAC, OP_SKINIT, OP_SVMEXIT, OP_SVMRET, OP_SVMLOCK, OP_SVMUNLOCK):
                    word = pack_instruction(opcode, 0, 0, 0)
                elif opcode in (OP_MOV, OP_ADD, OP_SUB, OP_AND, OP_OR, OP_XOR, OP_CMP, OP_TEST, OP_SHL, OP_SHR, OP_MUL, OP_IMUL, OP_DIV, OP_IDIV, OP_MOD, OP_FADD, OP_FSUB, OP_FMUL, OP_FDIV, OP_FCOMP, OP_FXCH, OP_ADC, OP_SBB, OP_ROL, OP_ROR, OP_BT, OP_BTS, OP_BTR, OP_BSF, OP_BSR):
                    if len(args) != 2:
                        raise AssemblerError(f"{mnem} requires two operands on line {ln}")
                    dst = self.parse_reg(args[0])
                    src = self.parse_reg(args[1])
                    word = pack_instruction(opcode, dst, src, 0)
                elif opcode == OP_LOADI:
                    if len(args) != 2:
                        raise AssemblerError("LOADI requires two operands")
                    dst = self.parse_reg(args[0])
                    imm = args[1]
                    imm = self.resolve_label_token(imm)
                    imm_val = self.parse_imm(imm)
                    word = pack_instruction(opcode, dst, 0, imm_val & 0xFFFF)
                elif opcode in (OP_LOAD, OP_STORE, OP_JMP, OP_JZ, OP_JNZ, OP_JE, OP_JNE, OP_JL, OP_JG, OP_JLE, OP_JGE, OP_CALL, OP_INT, OP_FLD, OP_FST, OP_FSTP, OP_FILD, OP_FIST, OP_FISTP):
                    if len(args) != 1:
                        raise AssemblerError(f"{mnem} requires one operand")
                    val = self.resolve_label_token(args[0])
                    valnum = self.parse_imm(val) & 0xFFFF
                    word = pack_instruction(opcode, 0, 0, valnum)
                elif opcode in (OP_PUSH, OP_POP, OP_INC, OP_DEC, OP_NOT, OP_OUT, OP_IN, OP_SYSCALL, OP_FCHS, OP_FABS, OP_FSQRT, OP_FSTSW, OP_LAR, OP_LSL, OP_SLDT, OP_STR, OP_LLDT, OP_LTR, OP_VERR, OP_VERW, OP_SGDT, OP_SIDT, OP_LGDT, OP_LIDT, OP_SMSW, OP_LMSW, OP_CLTS, OP_INVD, OP_WBINVD, OP_INVLPG, OP_INVPCID, OP_VMCALL, OP_VMLAUNCH, OP_VMRESUME, OP_VMXOFF, OP_MONITOR, OP_MWAIT, OP_RDSEED, OP_RDRAND, OP_CLAC, OP_STAC, OP_SKINIT, OP_SVMEXIT, OP_SVMRET, OP_SVMLOCK, OP_SVMUNLOCK):
                    if len(args) != 1:
                        raise AssemblerError(f"{mnem} requires one operand")
                    dst = self.parse_reg(args[0])
                    word = pack_instruction(opcode, dst, 0, 0)
                elif opcode == OP_ENTER:
                    if len(args) != 1:
                        raise AssemblerError("ENTER requires one operand")
                    imm = self.parse_imm(args[0])
                    word = pack_instruction(opcode, 0, 0, imm & 0xFFFF)
                elif opcode in (OP_LEA, OP_MOVZX, OP_MOVSX):
                    if len(args) != 2:
                        raise AssemblerError(f"{mnem} requires two operands")
                    dst = self.parse_reg(args[0])
                    imm = self.resolve_label_token(args[1])
                    imm_val = self.parse_imm(imm)
                    word = pack_instruction(opcode, dst, 0, imm_val & 0xFFFF)
                elif opcode in (OP_PUSHF, OP_POPF):
                    word = pack_instruction(opcode, 0, 0, 0)
                else:
                    word = pack_instruction(opcode, 0, 0, 0)
                if pc + 4 > len(out):
                    out.extend(bytearray(pc + 4 - len(out)))
                out[pc:pc+4] = itob_le(word)
                pc += 4
        return bytes(out)
    def resolve_label_token(self, tok: str) -> str:
        tok = tok.strip()
        if tok in self.labels:
            return str(self.labels[tok])
        return tok
    def assemble(self, text: str) -> bytes:
        self.first_pass(text)
        return self.second_pass()

# ---------------------------
# Host-side shell (interacts with kernel)
# ---------------------------
class Shell:
    """
    A simple terminal that exposes kernel features and can load/execute assembled binaries in the CPU.
    Commands:
    ls [-l] [path] - list files (with -l for detailed info)
    cat <file> - print file contents
    whoami - print username
    echo <text...> - print text
    write <file> <text...> - write text to file
    loadasm <srcfile> <destfile> - assemble source file and store as binary
    run <file> [addr] - load and execute binary file
    memmap <addr> <len> - map memory region
    regs - dump CPU registers
    disasm <addr> [count] - disassemble memory
    help - show this help
    exit/quit - exit shell
    ps - list processes
    kill <pid> - kill process
    chmod <mode> <file> - change file permissions
    mkdir <dir> - create directory
    rm <file> - remove file
    cp <src> <dest> - copy file
    mv <src> <dest> - move file
    stat <file> - show file statistics
    time <command> - time command execution
    debug [on|off] - enable/disable CPU tracing
    trace <addr> <count> - trace execution
    reboot - reboot the system
    bios - show BIOS information
    sysinfo - show system information
    random - generate random number
    bootload - enter bootloader mode
    clear - clear screen
    history - show command history
    set <var> <value> - set environment variable
    get <var> - get environment variable
    sleep <seconds> - delay execution
    ping <host> - test network connectivity
    uptime - show system uptime
    df - show disk usage
    top - show running processes
    find <path> <pattern> - search for files
    cls - clear screen
    ver - show version information
    calc <num1> <num2> <operation> - perform calculation (1=add, 2=sub, 3=mul, 4=div)
    date - show current date
    time - show current time
    type <file> - print file contents
    curl <url> - simulate curl command
    wget <url> - simulate wget command
    grep <pattern> <file> - search within file
    wc <file> - count lines, words, characters in a file
    """
    def __init__(self, kernel: Kernel, cpu: CPU, assembler: Assembler, bios: BIOS):
        self.kernel = kernel
        self.cpu = cpu
        self.assembler = assembler
        self.bios = bios
        self.bootloader = Bootloader()
        self.history_index = 0
    def run(self):
        print("Welcome to SimpleOS shell. Type 'help' for commands.")
        while True:
            try:
                line = input("simpleos> ")
            except EOFError:
                print()
                break
            line = line.strip()
            if not line:
                continue
            self.kernel.command_history.append(line) # Add to history
            parts = shlex.split(line)
            cmd = parts[0].lower()
            args = parts[1:]
            try:
                if cmd == "help":
                    print(textwrap.dedent(self.__doc__))
                elif cmd == "ls":
                    self.do_ls(args)
                elif cmd == "cat":
                    self.do_cat(args)
                elif cmd == "whoami":
                    print(self.kernel.username)
                elif cmd == "echo":
                    print(" ".join(args))
                elif cmd == "write":
                    self.do_write(args)
                elif cmd == "loadasm":
                    self.do_loadasm(args)
                elif cmd == "run":
                    result = self.do_run(args)
                    if result == 0xDEADBEEF:  # Reboot signal
                        print("System rebooting...")
                        return True  # Signal to reboot
                elif cmd == "memmap":
                    self.do_memmap(args)
                elif cmd == "regs":
                    print(self.cpu.dump_regs())
                elif cmd == "disasm":
                    self.do_disasm(args)
                elif cmd in ("exit", "quit"):
                    print("Bye.")
                    return False  # Normal exit
                elif cmd == "ps":
                    self.do_ps(args)
                elif cmd == "kill":
                    self.do_kill(args)
                elif cmd == "chmod":
                    self.do_chmod(args)
                elif cmd == "mkdir":
                    self.do_mkdir(args)
                elif cmd == "rm":
                    self.do_rm(args)
                elif cmd == "cp":
                    self.do_cp(args)
                elif cmd == "mv":
                    self.do_mv(args)
                elif cmd == "stat":
                    self.do_stat(args)
                elif cmd == "time":
                    self.do_time(args)
                elif cmd == "debug":
                    self.do_debug(args)
                elif cmd == "trace":
                    self.do_trace(args)
                elif cmd == "reboot":
                    print("Rebooting system...")
                    # Use kernel REBOOT syscall
                    self.cpu.reg_write(0, 24)  # REBOOT
                    self.kernel.syscall(self.cpu)
                    return True  # Signal to reboot
                elif cmd == "bios":
                    self.do_bios(args)
                elif cmd == "sysinfo":
                    self.do_sysinfo(args)
                elif cmd == "random":
                    self.do_random(args)
                elif cmd == "bootload":
                    self.do_bootload(args)
                elif cmd == "clear":
                    self.do_clear(args)
                elif cmd == "history":
                    self.do_history(args)
                elif cmd == "set":
                    self.do_set(args)
                elif cmd == "get":
                    self.do_get(args)
                elif cmd == "sleep":
                    self.do_sleep(args)
                elif cmd == "ping":
                    self.do_ping(args)
                elif cmd == "uptime":
                    self.do_uptime(args)
                elif cmd == "df":
                    self.do_df(args)
                elif cmd == "top":
                    self.do_top(args)
                elif cmd == "find":
                    self.do_find(args)
                elif cmd == "cls":
                    self.do_cls(args)
                elif cmd == "ver":
                    self.do_ver(args)
                elif cmd == "calc":
                    self.do_calc(args)
                elif cmd == "date":
                    self.do_date(args)
                elif cmd == "time":
                    self.do_time_cmd(args)
                elif cmd == "type":
                    self.do_type(args)
                elif cmd == "curl":
                    self.do_curl(args)
                elif cmd == "wget":
                    self.do_wget(args)
                elif cmd == "grep":
                    self.do_grep(args)
                elif cmd == "wc":
                    self.do_wc(args)
                else:
                    print("Unknown command. Type 'help'.")
            except Exception as e:
                print("Error:", e)
        return False
    def do_ls(self, args):
        long_format = False
        path = "/"
        if args:
            if args[0] == "-l":
                long_format = True
                if len(args) > 1:
                    path = args[1]
            else:
                path = args[0]
        if long_format:
            print(f"{'Mode':<10} {'Size':<8} {'Created':<20} {'Modified':<20} {'Name'}")
            for name, info in sorted(self.kernel.files.items()):
                if name.startswith(path):
                    mode_str = "rwxrwxrwx"  # Simplified
                    size = len(info["data"])
                    created = time.ctime(info["created_time"])
                    modified = time.ctime(info["modified_time"])
                    print(f"{mode_str:<10} {size:<8} {created:<20} {modified:<20} {name}")
        else:
            for name in sorted(self.kernel.files.keys()):
                if name.startswith(path):
                    size = len(self.kernel.files[name]["data"])
                    print(f"{name}\t{size} bytes")
    def do_cat(self, args):
        if not args:
            print("Usage: cat <file>")
            return
        name = args[0]
        if name not in self.kernel.files:
            print("File not found:", name)
            return
        data = self.kernel.files[name]["data"]
        try:
            print(data.decode("utf-8", errors="replace"))
        except Exception:
            print(data)
    def do_write(self, args):
        if len(args) < 2:
            print("Usage: write <file> <text...>")
            return
        name = args[0]
        text = " ".join(args[1:])
        self.kernel.files[name] = {
            "data": text.encode("utf-8"),
            "permissions": 0o644,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        print(f"Wrote {len(text)} bytes to {name}")
    def do_loadasm(self, args):
        if len(args) < 2:
            print("Usage: loadasm <srcfile> <destfile>")
            return
        src = args[0]
        dest = args[1]
        try:
            with open(src, "r") as f:
                asm_text = f.read()
        except Exception as e:
            print("Error reading assembly file:", e)
            return
        try:
            binary = self.assembler.assemble(asm_text)
        except AssemblerError as e:
            print("Assembly error:", e)
            return
        self.kernel.files[dest] = {
            "data": binary,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        print(f"Stored {len(binary)} bytes to {dest}")
    def do_run(self, args):
        if not args:
            print("Usage: run <file> [addr]")
            return
        fname = args[0]
        addr = 0x0000
        if len(args) > 1:
            addr = int(args[1], 0)
        if fname not in self.kernel.files:
            print("File not found:", fname)
            return
        data = self.kernel.files[fname]["data"]
        # Ensure we don't try to run an empty file
        if len(data) == 0:
            print(f"Warning: File {fname} is empty. Cannot execute.")
            return 0
        try:
            self.cpu.mem.load_bytes(addr, data)
        except Exception as e:
            print("Error loading file to memory:", e)
            return 0
        self.cpu.pc = addr
        self.cpu.halted = False
        self.cpu.reg_write(REG_SP, (self.cpu.mem.size - 4) // 4 * 4)
        print(f"Executing {fname} at {addr:08x} (size {len(data)} bytes).")
        try:
            self.cpu.run()
        except Exception as e:
            print("Execution error:", e)
        # Check if it was a reboot signal
        if self.cpu.reg_read(0) == 0xDEADBEEF:
            print("\n[Reboot signal received]")
            return 0xDEADBEEF
        else:
            print("\n[Program finished]")
            return 0
    def do_memmap(self, args):
        if len(args) != 2:
            print("Usage: memmap <addr> <len>")
            return
        addr = int(args[0], 0)
        length = int(args[1], 0)
        # Use kernel ALLOC syscall
        self.cpu.reg_write(0, 5)  # ALLOC
        self.cpu.reg_write(1, addr)
        self.cpu.reg_write(2, length)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print("Mapped memory")
        else:
            print("Failed to map memory")
    def do_disasm(self, args):
        if not args:
            print("Usage: disasm <addr> [count]")
            return
        addr = int(args[0], 0)
        count = 8
        if len(args) > 1:
            count = int(args[1], 0)
        lines = self.cpu.disassemble_at(addr, count)
        for l in lines:
            print(l)
    def do_ps(self, args):
        """List processes"""
        print("PID  Name        State      Priority  CPU Time")
        print("---  ----        -----      --------  --------")
        # In this simple implementation, we only have one process
        print(f"1    main        RUNNING    10        0.0")
    def do_kill(self, args):
        """Kill process by PID"""
        if not args:
            print("Usage: kill <pid>")
            return
        try:
            pid = int(args[0])
            # Use kernel KILL_PROCESS syscall
            self.cpu.reg_write(0, 15)  # KILL_PROCESS
            self.cpu.reg_write(1, pid)
            self.kernel.syscall(self.cpu)
            res = self.cpu.reg_read(0)
            if res != 0:
                print(f"Killed process {pid}")
            else:
                print(f"Failed to kill process {pid}")
        except ValueError:
            print("Invalid PID")
    def do_chmod(self, args):
        """Change file permissions"""
        if len(args) != 2:
            print("Usage: chmod <mode> <file>")
            return
        try:
            mode = int(args[0], 8)  # Octal mode
            fname = args[1]
            # Use kernel CHMOD syscall
            fname_addr = 0x2000  # Temporary address for filename
            self.cpu.mem.load_bytes(fname_addr, fname.encode('utf-8') + b'\0')
            self.cpu.reg_write(0, 17)  # CHMOD
            self.cpu.reg_write(1, fname_addr)
            self.cpu.reg_write(2, mode)
            self.kernel.syscall(self.cpu)
            res = self.cpu.reg_read(0)
            if res != 0:
                print(f"Changed permissions of {fname} to {args[0]}")
            else:
                print(f"Failed to change permissions of {fname}")
        except ValueError:
            print("Invalid mode")
    def do_mkdir(self, args):
        """Create directory"""
        if not args:
            print("Usage: mkdir <dir>")
            return
        dirname = args[0]
        # Use kernel MKDIR syscall
        dirname_addr = 0x2000  # Temporary address for dirname
        self.cpu.mem.load_bytes(dirname_addr, dirname.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 18)  # MKDIR
        self.cpu.reg_write(1, dirname_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Created directory {dirname}")
        else:
            print(f"Failed to create directory {dirname}")
    def do_rm(self, args):
        """Remove file or directory"""
        if not args:
            print("Usage: rm <file>")
            return
        fname = args[0]
        # Use kernel REMOVE syscall
        fname_addr = 0x2000  # Temporary address for filename
        self.cpu.mem.load_bytes(fname_addr, fname.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 19)  # REMOVE
        self.cpu.reg_write(1, fname_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Removed {fname}")
        else:
            print(f"Failed to remove {fname}")
    def do_cp(self, args):
        """Copy file"""
        if len(args) != 2:
            print("Usage: cp <src> <dest>")
            return
        src = args[0]
        dest = args[1]
        # Use kernel COPY syscall
        src_addr = 0x2000  # Temporary address for src
        dest_addr = 0x2100  # Temporary address for dest
        self.cpu.mem.load_bytes(src_addr, src.encode('utf-8') + b'\0')
        self.cpu.mem.load_bytes(dest_addr, dest.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 20)  # COPY
        self.cpu.reg_write(1, src_addr)
        self.cpu.reg_write(2, dest_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Copied {src} to {dest}")
        else:
            print(f"Failed to copy {src} to {dest}")
    def do_mv(self, args):
        """Move file"""
        if len(args) != 2:
            print("Usage: mv <src> <dest>")
            return
        src = args[0]
        dest = args[1]
        # Use kernel MOVE syscall
        src_addr = 0x2000  # Temporary address for src
        dest_addr = 0x2100  # Temporary address for dest
        self.cpu.mem.load_bytes(src_addr, src.encode('utf-8') + b'\0')
        self.cpu.mem.load_bytes(dest_addr, dest.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 21)  # MOVE
        self.cpu.reg_write(1, src_addr)
        self.cpu.reg_write(2, dest_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Moved {src} to {dest}")
        else:
            print(f"Failed to move {src} to {dest}")
    def do_stat(self, args):
        """Show file statistics"""
        if not args:
            print("Usage: stat <file>")
            return
        fname = args[0]
        # Use kernel STAT syscall
        fname_addr = 0x2000  # Temporary address for filename
        stat_buf_addr = 0x3000  # Temporary address for stat buffer
        self.cpu.mem.load_bytes(fname_addr, fname.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 22)  # STAT
        self.cpu.reg_write(1, fname_addr)
        self.cpu.reg_write(2, stat_buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read stat data from memory
            stat_data = self.cpu.mem.dump(stat_buf_addr, 24)
            size = btoi_le(stat_data[0:4])
            permissions = btoi_le(stat_data[4:8])
            created_time = struct.unpack('<Q', stat_data[8:16])[0]
            modified_time = struct.unpack('<Q', stat_data[16:24])[0]
            print(f"File: {fname}")
            print(f"Size: {size} bytes")
            print(f"Permissions: {oct(permissions)}")
            print(f"Created: {time.ctime(created_time/1000)}")
            print(f"Modified: {time.ctime(modified_time/1000)}")
        else:
            print(f"Failed to get stats for {fname}")
    def do_time(self, args):
        """Time command execution"""
        if not args:
            print("Usage: time <command> [args...]")
            return
        # Get start time
        self.cpu.reg_write(0, 9)  # GET_TIME
        self.kernel.syscall(self.cpu)
        start_time = self.cpu.reg_read(0)
        # Execute command
        cmd = args[0]
        cmd_args = args[1:]
        try:
            if cmd == "run":
                self.do_run(cmd_args)
            elif cmd == "loadasm":
                self.do_loadasm(cmd_args)
            else:
                print(f"Cannot time command: {cmd}")
                return
        except Exception as e:
            print("Error:", e)
            return
        # Get end time
        self.cpu.reg_write(0, 9)  # GET_TIME
        self.kernel.syscall(self.cpu)
        end_time = self.cpu.reg_read(0)
        elapsed = (end_time - start_time) / 1000.0  # Convert to seconds
        print(f"Command '{' '.join(args)}' took {elapsed:.3f} seconds")
    def do_debug(self, args):
        """Enable/disable CPU tracing"""
        if not args:
            print("Usage: debug [on|off]")
            return
        if args[0].lower() == "on":
            self.cpu.tracing = True
            print("Debug tracing enabled")
        elif args[0].lower() == "off":
            self.cpu.tracing = False
            print("Debug tracing disabled")
        else:
            print("Usage: debug [on|off]")
    def do_trace(self, args):
        """Trace execution for specified steps"""
        if len(args) < 2:
            print("Usage: trace <addr> <count>")
            return
        addr = int(args[0], 0)
        count = int(args[1], 0)
        self.cpu.pc = addr
        self.cpu.halted = False
        print(f"Tracing {count} steps starting at {addr:08x}")
        try:
            self.cpu.run(max_steps=count, trace=True)
        except Exception as e:
            print("Execution error:", e)
        print("\n[Trace finished]")
    def do_bios(self, args):
        """Show BIOS information"""
        # Use kernel GET_BIOS_INFO syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 25)  # GET_BIOS_INFO
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read BIOS info from memory
            data = self.cpu.mem.dump(buf_addr, 256)
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                info = data[:null_pos].decode('utf-8')
                print(info)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get BIOS information")
    def do_sysinfo(self, args):
        """Show system information"""
        # Use kernel GET_SYSTEM_INFO syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 27)  # GET_SYSTEM_INFO
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read system info from memory
            data = self.cpu.mem.dump(buf_addr, 256)
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                info = data[:null_pos].decode('utf-8')
                print(info)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get system information")
    def do_random(self, args):
        """Generate random number"""
        # Use kernel GENERATE_RANDOM syscall
        self.cpu.reg_write(0, 26)  # GENERATE_RANDOM
        self.kernel.syscall(self.cpu)
        random_num = self.cpu.reg_read(0)
        print(f"Random number: {random_num} (0x{random_num:08x})")
    def do_bootload(self, args):
        """Enter bootloader mode"""
        print("Entering bootloader mode...")
        # Generate bootloader
        bootloader_bin = self.bootloader.generate_bootloader()
        # Load bootloader to memory
        try:
            self.cpu.mem.load_bytes(0x7C00, bootloader_bin)
            self.cpu.pc = 0x7C00
            self.cpu.halted = False
            self.cpu.reg_write(REG_SP, 0x7C00)
            print(f"Bootloader loaded at 0x7C00 ({len(bootloader_bin)} bytes)")
            print("Executing bootloader...")
            self.cpu.run(max_steps=50)  # Run for a few steps
            print("\n[Bootloader execution completed]")
        except Exception as e:
            print(f"Bootloader error: {e}")
    def do_clear(self, args):
        """Clear screen"""
        # Use kernel CLEAR_SCREEN syscall
        self.cpu.reg_write(0, 30)  # CLEAR_SCREEN
        self.kernel.syscall(self.cpu)
        # No result expected
    def do_history(self, args):
        """Show command history"""
        # Use kernel SHOW_HISTORY syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 31)  # SHOW_HISTORY
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read history from memory
            data = self.cpu.mem.dump(buf_addr, 2048) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                hist_str = data[:null_pos].decode('utf-8')
                print(hist_str)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get command history")
    def do_set(self, args):
        """Set environment variable"""
        if len(args) != 2:
            print("Usage: set <var> <value>")
            return
        var_name = args[0]
        var_value = args[1]
        # Use kernel SET_ENV_VAR syscall
        var_addr = 0x2000  # Temporary address for var name
        val_addr = 0x2100  # Temporary address for value
        self.cpu.mem.load_bytes(var_addr, var_name.encode('utf-8') + b'\0')
        self.cpu.mem.load_bytes(val_addr, var_value.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 28)  # SET_ENV_VAR
        self.cpu.reg_write(1, var_addr)
        self.cpu.reg_write(2, val_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Set environment variable {var_name}={var_value}")
        else:
            print(f"Failed to set environment variable {var_name}")
    def do_get(self, args):
        """Get environment variable"""
        if not args:
            print("Usage: get <var>")
            return
        var_name = args[0]
        # Use kernel GET_ENV_VAR syscall
        var_addr = 0x2000  # Temporary address for var name
        out_addr = 0x2100  # Temporary address for output
        self.cpu.mem.load_bytes(var_addr, var_name.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 29)  # GET_ENV_VAR
        self.cpu.reg_write(1, var_addr)
        self.cpu.reg_write(2, out_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read value from memory
            data = self.cpu.mem.dump(out_addr, 256) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                value = data[:null_pos].decode('utf-8')
                print(f"{var_name}={value}")
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print(f"Failed to get environment variable {var_name}")
    def do_sleep(self, args):
        """Delay execution"""
        if not args:
            print("Usage: sleep <seconds>")
            return
        try:
            seconds = float(args[0])
            # Use kernel SLEEP syscall
            self.cpu.reg_write(0, 10)  # SLEEP
            self.cpu.reg_write(1, int(seconds * 1000))  # Convert to ms
            self.kernel.syscall(self.cpu)
            print(f"Slept for {seconds} seconds")
        except ValueError:
            print("Invalid number of seconds")
    def do_ping(self, args):
        """Test network connectivity"""
        if not args:
            print("Usage: ping <host>")
            return
        host = args[0]
        # Use kernel PING syscall
        host_addr = 0x2000  # Temporary address for host
        self.cpu.mem.load_bytes(host_addr, host.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 32)  # PING
        self.cpu.reg_write(1, host_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Ping to {host} successful")
        else:
            print(f"Ping to {host} failed")
    def do_uptime(self, args):
        """Show system uptime"""
        # Use kernel UPTIME syscall
        self.cpu.reg_write(0, 33)  # UPTIME
        self.kernel.syscall(self.cpu)
        uptime_seconds = self.cpu.reg_read(0)
        print(f"System uptime: {uptime_seconds} seconds")
    def do_df(self, args):
        """Show disk usage"""
        # Use kernel DF syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 34)  # DF
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read df output from memory
            data = self.cpu.mem.dump(buf_addr, 1024) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                df_out = data[:null_pos].decode('utf-8')
                print(df_out)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get disk usage")
    def do_top(self, args):
        """Show running processes"""
        # Use kernel TOP syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 35)  # TOP
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read top output from memory
            data = self.cpu.mem.dump(buf_addr, 1024) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                top_out = data[:null_pos].decode('utf-8')
                print(top_out)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get process info")
    def do_find(self, args):
        """Search for files"""
        if len(args) != 2:
            print("Usage: find <path> <pattern>")
            return
        path = args[0]
        pattern = args[1]
        # Use kernel FIND syscall
        path_addr = 0x2000  # Temporary address for path
        pattern_addr = 0x2100  # Temporary address for pattern
        out_addr = 0x2200  # Temporary address for output
        self.cpu.mem.load_bytes(path_addr, path.encode('utf-8') + b'\0')
        self.cpu.mem.load_bytes(pattern_addr, pattern.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 36)  # FIND
        self.cpu.reg_write(1, path_addr)
        self.cpu.reg_write(2, pattern_addr)
        self.cpu.reg_write(3, out_addr) # Output address
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read find output from memory
            data = self.cpu.mem.dump(out_addr, 1024) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                find_out = data[:null_pos].decode('utf-8')
                print(find_out)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to find files")
    def do_cls(self, args):
        """Clear screen"""
        self.do_clear(args)
    def do_ver(self, args):
        """Show version information"""
        print("SimpleOS v2.0")
        print("Built on 32-bit CPU with FPU/MMU")
    def do_calc(self, args):
        """Perform calculation"""
        if len(args) != 3:
            print("Usage: calc <num1> <num2> <operation>")
            print("Operation: 1=add, 2=sub, 3=mul, 4=div")
            return
        try:
            num1 = int(args[0])
            num2 = int(args[1])
            operation = int(args[2])
            # Use kernel CALC syscall
            self.cpu.reg_write(0, 37)  # CALC
            self.cpu.reg_write(1, num1)
            self.cpu.reg_write(2, num2)
            self.cpu.reg_write(3, operation)
            self.kernel.syscall(self.cpu)
            result = self.cpu.reg_read(0)
            print(f"Result: {result}")
        except ValueError:
            print("Invalid number or operation")
    def do_date(self, args):
        """Show current date"""
        # Use kernel DATE syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 38)  # DATE
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read date from memory
            data = self.cpu.mem.dump(buf_addr, 128) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                date_str = data[:null_pos].decode('utf-8')
                print(date_str)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get date")
    def do_time_cmd(self, args):
        """Show current time"""
        # Use kernel TIME syscall
        buf_addr = 0x4000
        self.cpu.reg_write(0, 39)  # TIME
        self.cpu.reg_write(1, buf_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read time from memory
            data = self.cpu.mem.dump(buf_addr, 128) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                time_str = data[:null_pos].decode('utf-8')
                print(time_str)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to get time")
    def do_type(self, args):
        """Print file contents"""
        if not args:
            print("Usage: type <file>")
            return
        fname = args[0]
        # Use kernel TYPE syscall
        fname_addr = 0x2000  # Temporary address for filename
        buf_addr = 0x3000  # Temporary address for buffer
        self.cpu.mem.load_bytes(fname_addr, fname.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 40)  # TYPE
        self.cpu.reg_write(1, fname_addr)
        self.cpu.reg_write(2, buf_addr) # Buffer address
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read file contents from buffer
            data = self.cpu.mem.dump(buf_addr, res) # Length is returned in R0
            try:
                print(data.decode("utf-8", errors="replace"))
            except Exception:
                print(data)
        else:
            print(f"Failed to read file {fname}")
    def do_curl(self, args):
        """Simulate curl command"""
        if not args:
            print("Usage: curl <url>")
            return
        url = args[0]
        # Use kernel CURL syscall
        url_addr = 0x2000  # Temporary address for URL
        self.cpu.mem.load_bytes(url_addr, url.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 41)  # CURL
        self.cpu.reg_write(1, url_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Curl to {url} successful")
        else:
            print(f"Curl to {url} failed")
    def do_wget(self, args):
        """Simulate wget command"""
        if not args:
            print("Usage: wget <url>")
            return
        url = args[0]
        # Use kernel WGET syscall
        url_addr = 0x2000  # Temporary address for URL
        self.cpu.mem.load_bytes(url_addr, url.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 42)  # WGET
        self.cpu.reg_write(1, url_addr)
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            print(f"Wget to {url} successful")
        else:
            print(f"Wget to {url} failed")
    def do_grep(self, args):
        """Search within file"""
        if len(args) != 2:
            print("Usage: grep <pattern> <file>")
            return
        pattern = args[0]
        fname = args[1]
        # Use kernel GREP syscall
        pattern_addr = 0x2000  # Temporary address for pattern
        file_addr = 0x2100  # Temporary address for file
        out_addr = 0x2200  # Temporary address for output
        self.cpu.mem.load_bytes(pattern_addr, pattern.encode('utf-8') + b'\0')
        self.cpu.mem.load_bytes(file_addr, fname.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 43)  # GREP
        self.cpu.reg_write(1, pattern_addr)
        self.cpu.reg_write(2, file_addr)
        self.cpu.reg_write(3, out_addr) # Output address
        self.kernel.syscall(self.cpu)
        res = self.cpu.reg_read(0)
        if res != 0:
            # Read grep output from memory
            data = self.cpu.mem.dump(out_addr, 1024) # Assume large buffer
            # Find null terminator
            null_pos = data.find(b'\0')
            if null_pos != -1:
                grep_out = data[:null_pos].decode('utf-8')
                print(grep_out)
            else:
                print(data.decode('utf-8', errors='replace'))
        else:
            print("Failed to grep file")
    def do_wc(self, args):
        """Count lines, words, characters in a file"""
        if not args:
            print("Usage: wc <file>")
            return
        fname = args[0]
        # Use kernel WC syscall
        file_addr = 0x2000  # Temporary address for file
        self.cpu.mem.load_bytes(file_addr, fname.encode('utf-8') + b'\0')
        self.cpu.reg_write(0, 44)  # WC
        self.cpu.reg_write(1, file_addr)
        self.kernel.syscall(self.cpu)
        result = self.cpu.reg_read(0)
        print(f"Lines in {fname}: {result}")

# ---------------------------
# Sample assembly programs
# ---------------------------
# Let's create a simple, non-empty sample program
SAMPLE_HELLO_ASM = r"""
.org 0x0000
; Simple hello program
; Print "Hello World\n" via kernel WRITE syscall
; We'll place the string at 0x0100
LOADI R1, 0x0100 ; address of string
LOADI R2, 12 ; length of "Hello World\n"
LOADI R0, 1 ; syscall number 1 = WRITE
; Set up syscall args: R1=fd, R2=buf, R3=len
LOADI R1, 1
LOADI R2, 0x0100
LOADI R3, 12
SYSCALL R0
HALT
.org 0x0100
.word 0x6c6c6548 ; 'Hell' little endian -> 'H','e','l','l'
.word 0x6f20646c ; 'o W' little endian -> 'o',' ','W','o'
.word 0x0000000a ; '\n\0\0\0' -> '\n'
"""
SAMPLE_COUNTDOWN = r"""
.org 0x0200
LOADI R0, 5 ; count
loop:
; print digit as character: '0' + R0
LOADI R1, 1 ; syscall number write
LOADI R2, 0x0300 ; buffer
LOADI R3, 1
MOV R4, R0
LOADI R5, 48 ; '0'
ADD R4, R5
; store R4 as byte at 0x0300
STORE R4, 0x0300
SYSCALL R1
DEC R0
CMP R0, R15 ; compare to zero using R15 zero
JNZ loop
HALT
"""
SAMPLE_FLOAT_CALC = r"""
.org 0x0400
; Calculate circle area: pi * r^2 where r=5
FLDPI ST0    ; Load pi onto FPU stack
FLDZ ST1     ; Load 0 onto FPU stack
LOADI R0, 5  ; Load radius
MOV R1, R0   ; Copy radius
IMUL R0, R1  ; R0 = r * r
MOV R2, R0   ; Copy r^2
; Convert to float and push onto FPU stack
LOADI R3, 0x0500 ; Address for temporary storage
STORE R2, 0x0500
FLD 0x0500   ; Load r^2 onto FPU stack
FMUL ST0, ST1 ; Multiply pi * r^2
; Store result
FSTP 0x0504  ; Store result and pop
HALT
"""
SAMPLE_PROCESS = r"""
.org 0x0600
; Create a new process
LOADI R1, 0x0700 ; Address of process name
LOADI R2, 0x0800 ; Entry point
LOADI R3, 4096   ; Memory size
LOADI R0, 11     ; CREATE_PROCESS syscall
SYSCALL R0
HALT
.org 0x0700
.word 0x73657473 ; "test" in little endian
.word 0x00000000 ; null terminator
.org 0x0800
; Simple process code
LOADI R0, 10
loop2:
DEC R0
CMP R0, R15
JNZ loop2
HALT
"""
SAMPLE_ADC_SBB = r"""
.org 0x0900
; Demonstrate ADC and SBB instructions
LOADI R0, 0xFFFFFFFF ; Load max value
LOADI R1, 1          ; Load 1
STC                  ; Set carry flag
ADC R0, R1           ; R0 = R0 + R1 + carry = 0xFFFFFFFF + 1 + 1 = 1
; Now R0 should be 1, and carry should be set
LOADI R2, 5
LOADI R3, 3
SUB R2, R3           ; R2 = 5 - 3 = 2
CLI                  ; Clear interrupt flag
STI                  ; Set interrupt flag
HALT
"""
# ---------------------------
# Utilities & main
# ---------------------------
def setup_demo_environment(kernel: Kernel, assembler: Assembler):
    # Assemble demo programs and store in fs
    try:
        bin_hello = assembler.assemble(SAMPLE_HELLO_ASM)
        kernel.files["/hello.bin"] = {
            "data": bin_hello,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        bin_countdown = assembler.assemble(SAMPLE_COUNTDOWN)
        kernel.files["/countdown.bin"] = {
            "data": bin_countdown,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        bin_float = assembler.assemble(SAMPLE_FLOAT_CALC)
        kernel.files["/float.bin"] = {
            "data": bin_float,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        bin_process = assembler.assemble(SAMPLE_PROCESS)
        kernel.files["/process.bin"] = {
            "data": bin_process,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        bin_adc_sbb = assembler.assemble(SAMPLE_ADC_SBB)
        kernel.files["/adc_sbb.bin"] = {
            "data": bin_adc_sbb,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        # Add some test files
        kernel.files["/test.txt"] = {
            "data": b"This is a test file.\nIt has multiple lines.\n",
            "permissions": 0o644,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        kernel.files["/data.bin"] = {
            "data": bytes(range(256)),  # Binary data 0-255
            "permissions": 0o644,
            "created_time": time.time(),
            "modified_time": time.time()
        }
    except Exception as e:
        logger.warning("Failed to assemble demo: %s", e)

def main_system():
    """Main system loop with reboot capability"""
    reboot_count = 0
    while True:
        print(f"\n{'='*50}")
        if reboot_count == 0:
            print("SimpleOS Booting...")
        else:
            print(f"SimpleOS Reboot #{reboot_count}")
        print(f"{'='*50}")
        # Parse arguments
        ap = argparse.ArgumentParser(description="SimpleOS Emulator")
        ap.add_argument("--username", default="guest", help="username for whoami")
        ap.add_argument("--mem", type=int, default=DEFAULT_MEMORY_BYTES, help="initial memory size in bytes")
        args = ap.parse_args()
        # Initialize system components
        mem = Memory(size_bytes=args.mem)
        bios = BIOS()
        bios.initialize_hardware(args.mem)
        kernel = Kernel(username=args.username)
        cpu = CPU(memory=mem, kernel=kernel)
        assembler = Assembler()
        # Setup demo environment
        setup_demo_environment(kernel, assembler)
        # Initialize shell
        shell = Shell(kernel, cpu, assembler, bios)
        # Run shell
        should_reboot = shell.run()
        if should_reboot:
            reboot_count += 1
            print("System rebooting...\n")
            continue
        else:
            print("Goodbye!")
            break

if __name__ == "__main__":
    main_system()

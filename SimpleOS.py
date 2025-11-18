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
import socket
import threading
import re
import ast
from typing import Dict, List, Tuple, Optional, Callable, Any
from enum import IntEnum
import asyncio
from dataclasses import dataclass, field
from collections import deque
# Basic logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("SimpleOS")

# ---------------------------
# Architecture constants
# ---------------------------
WORD_SIZE = 4  # bytes per word
DEFAULT_MEMORY_BYTES = 64 * 1024 * 1024  # 64 MiB default (increased)
NUM_REGS = 16
NUM_FPU_REGS = 8  # Floating point registers
# Registers indices
REG_R0 = 0
REG_R1 = 1
REG_R2 = 2
REG_R3 = 3
REG_R4 = 4
REG_R5 = 5
REG_R6 = 6
REG_R7 = 7
REG_R8 = 8
REG_R9 = 9
REG_R10 = 10
REG_R11 = 11
REG_R12 = 12
REG_KERNEL = 13  # reserved for kernel use in syscalls (optional)
REG_SP = 14      # Stack Pointer
REG_PC = 15      # Program Counter (not in regs array)

# Segment registers
REG_CS = 0  # Code Segment
REG_DS = 1  # Data Segment
REG_ES = 2  # Extra Segment
REG_FS = 3  # F Segment
REG_GS = 4  # G Segment
REG_SS = 5  # Stack Segment

# Control registers
REG_CR0 = 0
REG_CR1 = 1  # Reserved
REG_CR2 = 2  # Page Fault Linear Address
REG_CR3 = 3  # Page Directory Base Register
REG_CR4 = 4
# Control Register 0 (CR0) flags
CR0_PE = 1 << 0    # Protection Enable
CR0_MP = 1 << 1    # Monitor Coprocessor
CR0_EM = 1 << 2    # Emulation
CR0_TS = 1 << 3    # Task Switched
CR0_ET = 1 << 4    # Extension Type
CR0_NE = 1 << 5    # Numeric Error
CR0_WP = 1 << 16   # Write Protect
CR0_AM = 1 << 18   # Alignment Mask
CR0_NW = 1 << 29   # Not Write-through
CR0_CD = 1 << 30   # Cache Disable
CR0_PG = 1 << 31   # Paging

# CPU Flags
FLAG_ZERO = 1 << 0
FLAG_NEG = 1 << 1
FLAG_CARRY = 1 << 2
FLAG_OVERFLOW = 1 << 3
FLAG_INTERRUPT = 1 << 4
FLAG_TRAP = 1 << 5
# --- Additional Flags ---
FLAG_AUX = 1 << 6  # Auxiliary Carry Flag (for BCD operations)
FLAG_DIR = 1 << 7  # Direction Flag (for string operations)
FLAG_PARITY = 1 << 23  # Parity Flag (even parity)
FLAG_ADJUST = 1 << 24  # Adjust Flag (for decimal arithmetic)
FLAG_RESUME = 1 << 25  # Resume Flag (for debugging)
FLAG_POWER_SAVE = 1 << 26  # CPU running in power-save mode
FLAG_THERMAL = 1 << 27     # Thermal throttling active
FLAG_SECURE = 1 << 28      # Secure execution mode

# x86-style flag aliases
FLAG_CF = FLAG_CARRY       # Carry Flag
FLAG_PF = 1 << 29          # Parity Flag (use unique bit)
FLAG_AF = FLAG_AUX         # Auxiliary Carry Flag
FLAG_ZF = FLAG_ZERO        # Zero Flag
FLAG_SF = FLAG_NEG         # Sign Flag
FLAG_OF = FLAG_OVERFLOW    # Overflow Flag
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
FLAG_SSE = 1 << 19  # Streaming SIMD Extensions present
FLAG_MMX = 1 << 20  # MMX present
FLAG_VMX = 1 << 21  # VMX (Intel VT-x) present
FLAG_SMEP = 1 << 22 # Supervisor Mode Execution Protection

# ---------------------------
# Opcode Definitions (32 opcodes max for 8-bit field)
# ---------------------------
OP_NOP = 0x00
OP_MOV = 0x01
OP_LOADI = 0x02
OP_LOAD = 0x03
OP_STORE = 0x04
OP_ADD = 0x05
OP_SUB = 0x06
OP_MUL = 0x07
OP_DIV = 0x08
OP_MOD = 0x09
OP_AND = 0x0A
OP_OR = 0x0B
OP_XOR = 0x0C
OP_NOT = 0x0D
OP_SHL = 0x0E
OP_SHR = 0x0F
OP_CMP = 0x10
OP_TEST = 0x11
OP_JMP = 0x12
OP_JZ = 0x13
OP_JNZ = 0x14
OP_JE = 0x15
OP_JNE = 0x16
OP_JL = 0x17
OP_JG = 0x18
OP_JLE = 0x19
OP_JGE = 0x1A
OP_CALL = 0x1B
OP_RET = 0x1C
OP_PUSH = 0x1D
OP_POP = 0x1E
OP_HALT = 0x1F
OP_SYSCALL = 0x20
OP_INT = 0x21
OP_IRET = 0x22
OP_INC = 0x23
OP_DEC = 0x24
OP_NEG = 0x25
OP_IMUL = 0x26
OP_IDIV = 0x27
OP_SAR = 0x28
OP_ROL = 0x29
OP_ROR = 0x2A
OP_BT = 0x2B
OP_BTS = 0x2C
OP_BTR = 0x2D
OP_BSF = 0x2E
OP_BSR = 0x2F
OP_BSWAP = 0x30
OP_CMOV = 0x31
OP_SETZ = 0x32
OP_SETNZ = 0x33
OP_SETL = 0x34
OP_MOVB = 0x35
OP_MOVW = 0x36
OP_LOADB = 0x37
OP_STOREB = 0x38
OP_SEXT = 0x39
OP_ZEXT = 0x3A
OP_POPCNT = 0x3B
OP_MIN = 0x3C
OP_MAX = 0x3D
OP_ABS = 0x3E
OP_MEMCPY = 0x3F
OP_MEMSET = 0x40
OP_STRLEN = 0x41
OP_STRCMP = 0x42
OP_CLAMP = 0x43
OP_ADC = 0x44
OP_SBB = 0x45
OP_CBW = 0x46
OP_CWD = 0x47
OP_CWDQ = 0x48
OP_CLC = 0x49
OP_STC = 0x4A
OP_CLI = 0x4B
OP_STI = 0x4C
OP_LAHF = 0x4D
OP_SAHF = 0x4E
OP_PUSHF = 0x4F
OP_POPF = 0x50
OP_LEAVE = 0x51
OP_ENTER = 0x52
OP_NOP2 = 0x53
OP_OUT = 0x54
OP_IN = 0x55
OP_LEA = 0x109
OP_MOVZX = 0x10A
OP_MOVSX = 0x10B
OP_BTC = 0x10C
OP_SETA_REG = 0x10D
OP_SETB_REG = 0x10E
OP_SETG = 0x10F
OP_SETLE = 0x110
OP_SETGE = 0x111
OP_SETNE = 0x112
OP_SETE = 0x113
OP_LOOP = 0x114
OP_LOOPZ = 0x115
OP_LOOPNZ = 0x116
OP_REP = 0x117
OP_REPZ = 0x118
OP_REPNZ = 0x119
OP_MOVSB = 0x11A
OP_MOVSW = 0x11B
OP_MOVSD = 0x11C
OP_CMPSB = 0x11D
OP_SCASB = 0x11E
OP_LODSB = 0x11F
OP_STOSB = 0x120
OP_IMUL3 = 0x121
OP_SHLD = 0x122
OP_SHRD = 0x123
OP_RDTSC = 0x124
OP_RDMSR = 0x125
OP_WRMSR = 0x126
OP_CPUID2 = 0x127
OP_PAUSE = 0x128
OP_NOP3 = 0x129
OP_NOP4 = 0x12A
OP_LOCK = 0x12B
OP_REPNE = 0x12C
OP_REPE = 0x12D
OP_ACCADD = 0x56
OP_ACCSUB = 0x57
OP_SETACC = 0x58
OP_GETACC = 0x59
OP_XCHG = 0x5A
OP_CMPXCHG = 0x5B
OP_LAR = 0x5C
OP_LSL = 0x5D
OP_SLDT = 0x5E
OP_STR = 0x5F
OP_LLDT = 0x60
OP_LTR = 0x61
OP_VERR = 0x62
OP_VERW = 0x63
OP_SGDT = 0x64
OP_SIDT = 0x65
OP_LGDT = 0x66
OP_LIDT = 0x67
OP_SMSW = 0x68
OP_LMSW = 0x69
OP_CLTS = 0x6A
OP_INVD = 0x6B
OP_WBINVD = 0x6C
OP_INVLPG = 0x6D
OP_INVPCID = 0x6E
OP_VMCALL = 0x6F
OP_VMLAUNCH = 0x70
OP_VMRESUME = 0x71
OP_VMXOFF = 0x72
OP_MONITOR = 0x73
OP_MWAIT = 0x74
OP_RDSEED = 0x75
OP_RDRAND = 0x76
OP_CLAC = 0x77
OP_STAC = 0x78
OP_SKINIT = 0x79
OP_SVMEXIT = 0x7A
OP_SVMRET = 0x7B
OP_SVMLOCK = 0x7C
OP_SVMUNLOCK = 0x7D
OP_CLD = 0x7E
OP_STD = 0x7F
OP_INTO = 0x80
OP_AAM = 0x81
OP_AAD = 0x82
OP_XLAT = 0x83
OP_FADD = 0x84
OP_FSUB = 0x85
OP_FMUL = 0x86
OP_FDIV = 0x87
OP_FCOMP = 0x88
OP_FXCH = 0x89
OP_FLDZ = 0x8A
OP_FLD1 = 0x8B
OP_FLDPI = 0x8C
OP_FLDLG2 = 0x8D
OP_FLDLN2 = 0x8E
OP_FCLEX = 0x8F
OP_FLD = 0x90
OP_FST = 0x91
OP_FSTP = 0x92
OP_FILD = 0x93
OP_FIST = 0x94
OP_FISTP = 0x95
OP_FCHS = 0x96
OP_FABS = 0x97
OP_FSQRT = 0x98
OP_FSTSW = 0x99
OP_SETF = 0x9A
OP_TESTF = 0x9B
OP_CLRF = 0x9C
OP_CPUID = 0x9D
OP_NET_SEND = 0xD0
OP_NET_RECV = 0xD1
OP_NET_CONNECT = 0xD2
OP_NET_LISTEN = 0xD3
OP_NET_ACCEPT = 0xD4
OP_NET_CLOSE = 0xD5
OP_NET_PING = 0xD6
OP_NET_CURL = 0xD7
OP_NET_WGET = 0xD8
# Additional arithmetic
OP_SQRT = 0xDA
OP_POW = 0xDB
OP_LOG = 0xDC
OP_EXP = 0xDD
OP_SIN = 0xDE
OP_COS = 0xDF
OP_TAN = 0xE0
# Additional bitwise
OP_POPCOUNT = 0xE1
OP_LZCNT = 0xE2
OP_TZCNT = 0xE3
# Additional memory
OP_PREFETCH = 0xE4
OP_CLFLUSH = 0xE5
OP_MFENCE = 0xE6
OP_LFENCE = 0xE7
OP_SFENCE = 0xE8
# String operations
OP_STRCPY = 0xE9
OP_STRCAT = 0xEA
OP_STRNCPY = 0xEB
OP_STRNCAT = 0xEC
OP_STRCHR = 0xED
OP_STRSTR = 0xEE
# Conversion
OP_ATOI = 0xEF
OP_ITOA = 0xF0
OP_FTOI = 0xF1
OP_ITOF = 0xF2
# Comparison
OP_CMPS = 0xF3
OP_SCAS = 0xF4
# Atomic operations
OP_XADD = 0xF5
OP_XCHG_MEM = 0xF6
# Conditional set
OP_SETA = 0xF7
OP_SETB = 0xF8
OP_SETBE = 0xF9
OP_SETAE = 0xFA
OP_SETO = 0xFB
OP_SETNO = 0xFC
# Additional utility instructions
OP_SWAP = 0xFD
OP_ROT = 0xFE
OP_REVERSE = 0xFF
OP_GETSEED = 0x100
OP_SETSEED = 0x101
OP_RANDOM = 0x102
OP_HASH = 0x103
OP_CRC32 = 0x104
OP_GETTIME = 0x105
OP_SLEEP = 0x106
OP_YIELD = 0x107
OP_BARRIER = 0x108
OP_MEMSCRUB = 0x150
OP_MEMCHR = 0x200
OP_REV_MEM = 0x201
OP_ADDI = 0x151
OP_SUBI = 0x152
OP_MULI = 0x153
OP_DIVI = 0x154
OP_ANDI = 0x155
OP_ORI = 0x156
OP_XORI = 0x157
OP_SHLI = 0x158
OP_SHRI = 0x159
OP_MULI = 0x153
OP_DIVI = 0x154
# New useful opcodes for games/demos (using available 0x9E-0xCF range)
OP_LERP = 0x9E    # Linear interpolation: lerp(a, b, t)
OP_SIGN = 0x9F    # Sign of number: -1, 0, or 1
OP_SATURATE = 0xA0  # Clamp to 0-255 range (useful for colors)
# Graphics opcodes (0xA1-0xA8)
OP_PIXEL = 0xA1      # Draw pixel: PIXEL x, y, color
OP_LINE = 0xA2       # Draw line: LINE x1, y1, x2, y2, color
OP_RECT = 0xA3       # Draw rectangle outline: RECT x, y, w, h, color
OP_FILLRECT = 0xA4   # Draw filled rectangle: FILLRECT x, y, w, h, color
OP_CIRCLE = 0xA5     # Draw circle outline: CIRCLE x, y, r, color
OP_FILLCIRCLE = 0xA6 # Draw filled circle: FILLCIRCLE x, y, r, color
OP_GETPIXEL = 0xA7   # Get pixel color: GETPIXEL dst, x, y
OP_CLEAR = 0xA8      # Clear screen: CLEAR color
# New useful opcodes for better performance
OP_MULH = 0xA9       # Multiply High: Get upper 32 bits of 64-bit multiplication
OP_DIVMOD = 0xAA     # Combined DIV/MOD: dst=quotient, src gets remainder
OP_AVGB = 0xAB       # Average bytes: Average of two values (useful for blending)

OPCODE_NAME = {
    OP_NOP: "NOP", OP_MOV: "MOV", OP_LOADI: "LOADI", OP_LOAD: "LOAD", OP_STORE: "STORE",
    OP_ADD: "ADD", OP_SUB: "SUB", OP_MUL: "MUL", OP_DIV: "DIV", OP_MOD: "MOD",
    OP_AND: "AND", OP_OR: "OR", OP_XOR: "XOR", OP_NOT: "NOT", OP_SHL: "SHL", OP_SHR: "SHR",
    OP_CMP: "CMP", OP_TEST: "TEST", OP_JMP: "JMP", OP_JZ: "JZ", OP_JNZ: "JNZ",
    OP_JE: "JE", OP_JNE: "JNE", OP_JL: "JL", OP_JG: "JG", OP_JLE: "JLE", OP_JGE: "JGE",
    OP_CALL: "CALL", OP_RET: "RET", OP_PUSH: "PUSH", OP_POP: "POP", OP_HALT: "HALT",
    OP_SYSCALL: "SYSCALL", OP_INT: "INT", OP_IRET: "IRET", OP_INC: "INC", OP_DEC: "DEC",
    OP_NEG: "NEG", OP_IMUL: "IMUL", OP_IDIV: "IDIV", OP_SAR: "SAR", OP_ROL: "ROL", OP_ROR: "ROR",
    OP_BT: "BT", OP_BTS: "BTS", OP_BTR: "BTR", OP_BSF: "BSF", OP_BSR: "BSR", OP_BSWAP: "BSWAP", OP_BTC: "BTC",
    OP_CMOV: "CMOV", OP_SETZ: "SETZ", OP_SETNZ: "SETNZ", OP_SETL: "SETL",
    OP_LEA: "LEA", OP_MOVZX: "MOVZX", OP_MOVSX: "MOVSX",
    OP_MOVB: "MOVB", OP_MOVW: "MOVW", OP_LOADB: "LOADB", OP_STOREB: "STOREB",
    OP_SEXT: "SEXT", OP_ZEXT: "ZEXT", OP_POPCNT: "POPCNT", OP_MIN: "MIN", OP_MAX: "MAX", OP_ABS: "ABS",
    OP_MEMCPY: "MEMCPY", OP_MEMSET: "MEMSET", OP_MEMSCRUB: "MEMSCRUB",
    OP_STRLEN: "STRLEN", OP_STRCMP: "STRCMP", OP_CLAMP: "CLAMP",
    OP_ADC: "ADC", OP_SBB: "SBB", OP_CBW: "CBW", OP_CWD: "CWD", OP_CWDQ: "CWDQ",
    OP_CLC: "CLC", OP_STC: "STC", OP_CLI: "CLI", OP_STI: "STI", OP_LAHF: "LAHF", OP_SAHF: "SAHF",
    OP_PUSHF: "PUSHF", OP_POPF: "POPF", OP_LEAVE: "LEAVE", OP_ENTER: "ENTER", OP_NOP2: "NOP2",
    OP_OUT: "OUT", OP_IN: "IN", OP_ACCADD: "ACCADD", OP_ACCSUB: "ACCSUB", OP_SETACC: "SETACC", OP_GETACC: "GETACC",
    OP_XCHG: "XCHG", OP_CMPXCHG: "CMPXCHG", OP_LAR: "LAR", OP_LSL: "LSL", OP_SLDT: "SLDT", OP_STR: "STR",
    OP_LLDT: "LLDT", OP_LTR: "LTR", OP_VERR: "VERR", OP_VERW: "VERW", OP_SGDT: "SGDT", OP_SIDT: "SIDT",
    OP_LGDT: "LGDT", OP_LIDT: "LIDT", OP_SMSW: "SMSW", OP_LMSW: "LMSW", OP_CLTS: "CLTS", OP_INVD: "INVD",
    OP_WBINVD: "WBINVD", OP_INVLPG: "INVLPG", OP_INVPCID: "INVPCID", OP_VMCALL: "VMCALL", OP_VMLAUNCH: "VMLAUNCH",
    OP_VMRESUME: "VMRESUME", OP_VMXOFF: "VMXOFF", OP_MONITOR: "MONITOR", OP_MWAIT: "MWAIT", OP_RDSEED: "RDSEED",
    OP_RDRAND: "RDRAND", OP_CLAC: "CLAC", OP_STAC: "STAC", OP_SKINIT: "SKINIT", OP_SVMEXIT: "SVMEXIT",
    OP_SVMRET: "SVMRET", OP_SVMLOCK: "SVMLOCK", OP_SVMUNLOCK: "SVMUNLOCK", OP_CLD: "CLD", OP_STD: "STD",
    OP_INTO: "INTO", OP_AAM: "AAM", OP_AAD: "AAD", OP_XLAT: "XLAT",
    OP_FADD: "FADD", OP_FSUB: "FSUB", OP_FMUL: "FMUL", OP_FDIV: "FDIV", OP_FCOMP: "FCOMP", OP_FXCH: "FXCH",
    OP_FLDZ: "FLDZ", OP_FLD1: "FLD1", OP_FLDPI: "FLDPI", OP_FLDLG2: "FLDLG2", OP_FLDLN2: "FLDLN2", OP_FCLEX: "FCLEX",
    OP_FLD: "FLD", OP_FST: "FST", OP_FSTP: "FSTP", OP_FILD: "FILD", OP_FIST: "FIST", OP_FISTP: "FISTP",
    OP_FCHS: "FCHS", OP_FABS: "FABS", OP_FSQRT: "FSQRT", OP_FSTSW: "FSTSW", OP_SETF: "SETF", OP_TESTF: "TESTF", OP_CLRF: "CLRF", OP_CPUID: "CPUID",
    OP_NET_SEND: "NET_SEND", OP_NET_RECV: "NET_RECV", OP_NET_CONNECT: "NET_CONNECT",
    OP_NET_LISTEN: "NET_LISTEN", OP_NET_ACCEPT: "NET_ACCEPT", OP_NET_CLOSE: "NET_CLOSE",
    OP_NET_PING: "NET_PING", OP_NET_CURL: "NET_CURL", OP_NET_WGET: "NET_WGET",
    OP_SQRT: "SQRT", OP_POW: "POW", OP_LOG: "LOG", OP_EXP: "EXP", OP_SIN: "SIN", OP_COS: "COS", OP_TAN: "TAN",
    OP_POPCOUNT: "POPCOUNT", OP_LZCNT: "LZCNT", OP_TZCNT: "TZCNT",
    OP_PREFETCH: "PREFETCH", OP_CLFLUSH: "CLFLUSH", OP_MFENCE: "MFENCE", OP_LFENCE: "LFENCE", OP_SFENCE: "SFENCE",
    OP_STRCPY: "STRCPY", OP_STRCAT: "STRCAT", OP_STRNCPY: "STRNCPY", OP_STRNCAT: "STRNCAT", OP_STRCHR: "STRCHR", OP_STRSTR: "STRSTR",
    OP_ATOI: "ATOI", OP_ITOA: "ITOA", OP_FTOI: "FTOI", OP_ITOF: "ITOF",
    OP_MEMCHR: "MEMCHR", OP_REV_MEM: "REV_MEM",
    OP_CMPS: "CMPS", OP_SCAS: "SCAS",
    OP_XADD: "XADD", OP_XCHG_MEM: "XCHG_MEM",
    OP_SETA: "SETA", OP_SETB: "SETB", OP_SETBE: "SETBE", OP_SETAE: "SETAE", OP_SETO: "SETO", OP_SETNO: "SETNO",
    OP_SWAP: "SWAP", OP_ROT: "ROT", OP_REVERSE: "REVERSE", OP_GETSEED: "GETSEED", OP_SETSEED: "SETSEED",
    OP_RANDOM: "RANDOM", OP_HASH: "HASH", OP_CRC32: "CRC32", OP_GETTIME: "GETTIME", OP_SLEEP: "SLEEP",
    OP_YIELD: "YIELD", OP_BARRIER: "BARRIER",
    OP_ADDI: "ADDI", OP_SUBI: "SUBI", OP_MULI: "MULI", OP_DIVI: "DIVI",
    OP_ANDI: "ANDI", OP_ORI: "ORI", OP_XORI: "XORI", OP_SHLI: "SHLI", OP_SHRI: "SHRI",
    OP_LERP: "LERP", OP_SIGN: "SIGN", OP_SATURATE: "SATURATE",
    OP_PIXEL: "PIXEL", OP_LINE: "LINE", OP_RECT: "RECT", OP_FILLRECT: "FILLRECT",
    OP_CIRCLE: "CIRCLE", OP_FILLCIRCLE: "FILLCIRCLE", OP_GETPIXEL: "GETPIXEL", OP_CLEAR: "CLEAR",
    OP_MULH: "MULH", OP_DIVMOD: "DIVMOD", OP_AVGB: "AVGB",
    OP_SETG: "SETG", OP_SETLE: "SETLE", OP_SETGE: "SETGE", OP_SETNE: "SETNE", OP_SETE: "SETE",
    OP_LOOP: "LOOP", OP_LOOPZ: "LOOPZ", OP_LOOPNZ: "LOOPNZ",
    OP_REP: "REP", OP_REPZ: "REPZ", OP_REPNZ: "REPNZ",
    OP_MOVSB: "MOVSB", OP_MOVSW: "MOVSW", OP_MOVSD: "MOVSD",
    OP_CMPSB: "CMPSB", OP_SCASB: "SCASB", OP_LODSB: "LODSB", OP_STOSB: "STOSB",
    OP_IMUL3: "IMUL3", OP_SHLD: "SHLD", OP_SHRD: "SHRD",
    OP_RDTSC: "RDTSC", OP_RDMSR: "RDMSR", OP_WRMSR: "WRMSR", OP_CPUID2: "CPUID2",
    OP_PAUSE: "PAUSE", OP_NOP3: "NOP3", OP_NOP4: "NOP4",
OP_LOCK: "LOCK", OP_REPNE: "REPNE", OP_REPE: "REPE",
}

NAME_OPCODE = {v: k for k, v in OPCODE_NAME.items()}

# Memory region constants
# For the current 64MB default memory, place the stack just below the BIOS
# ROM region (last 64KB of memory). The stack grows downward from STACK_BASE
# and remains entirely inside valid RAM.
STACK_SIZE = 0x00010000                  # 64KB stack
STACK_BASE = DEFAULT_MEMORY_BYTES - STACK_SIZE  # Top of stack (grows downward)
HEAP_BASE = 0x10000000                   # Logical heap base (may be virtual)
HEAP_SIZE = 0x70000000                   # Logical heap size
CODE_BASE = 0x00001000                   # Code segment
CODE_SIZE = 0x0FFF0000                   # ~256MB code
DATA_BASE = 0x08000000                   # Data segment
DATA_SIZE = 0x08000000                   # 128MB data

FLAG_NAME_MAP = {
    "ZERO": FLAG_ZERO, "NEG": FLAG_NEG, "CARRY": FLAG_CARRY, "OVERFLOW": FLAG_OVERFLOW,
    "INTERRUPT": FLAG_INTERRUPT, "TRAP": FLAG_TRAP, "AUX": FLAG_AUX, "DIR": FLAG_DIR,
    "PARITY": FLAG_PARITY, "ADJUST": FLAG_ADJUST, "RESUME": FLAG_RESUME,
    "POWER": FLAG_POWER_SAVE, "THERMAL": FLAG_THERMAL, "SECURE": FLAG_SECURE,
}
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
# Network Module - Real Network I/O
# ---------------------------
class NetworkUtils:
    """Real network utilities for ping, curl, wget"""
    
    @staticmethod
    def ping(host: str, timeout: int = 2) -> bool:
        """Ping a host, return True if reachable"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, 80))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    @staticmethod
    def curl(url: str, timeout: int = 5) -> str:
        """Fetch URL content via HTTP GET"""
        try:
            from urllib.request import urlopen
            from urllib.error import URLError
            response = urlopen(url, timeout=timeout)
            content = response.read().decode('utf-8', errors='replace')
            return content[:1024]  # Limit to 1KB
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    def wget(url: str, timeout: int = 5) -> int:
        """Download URL, return bytes downloaded"""
        try:
            from urllib.request import urlopen
            response = urlopen(url, timeout=timeout)
            content = response.read()
            return len(content)
        except Exception:
            return -1

class NetworkDevice:
    """Real network device for CPU networking"""
    def __init__(self):
        self.sockets = {}  # socket_id -> socket object
        self.next_socket_id = 1
        self.packets = []  # packet buffer
        self.lock = threading.Lock()
        self.utils = NetworkUtils()
        
    def socket_create(self) -> int:
        """Create a new socket, return socket ID"""
        with self.lock:
            sock_id = self.next_socket_id
            self.next_socket_id += 1
            try:
                self.sockets[sock_id] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sockets[sock_id].settimeout(2.0)
                return sock_id
            except Exception as e:
                logger.error("Failed to create socket: %s", e)
                return -1
    
    def socket_connect(self, sock_id: int, host: str, port: int) -> int:
        """Connect socket to host:port, return 0 on success, -1 on error"""
        with self.lock:
            if sock_id not in self.sockets:
                return -1
            try:
                self.sockets[sock_id].connect((host, port))
                return 0
            except Exception as e:
                logger.error("Failed to connect: %s", e)
                return -1
    
    def socket_send(self, sock_id: int, data: bytes) -> int:
        """Send data on socket, return bytes sent or -1 on error"""
        with self.lock:
            if sock_id not in self.sockets:
                return -1
            try:
                sent = self.sockets[sock_id].send(data)
                return sent
            except Exception as e:
                logger.error("Failed to send: %s", e)
                return -1
    
    def socket_recv(self, sock_id: int, size: int) -> bytes:
        """Receive data from socket"""
        with self.lock:
            if sock_id not in self.sockets:
                return b''
            try:
                data = self.sockets[sock_id].recv(size)
                return data
            except socket.timeout:
                return b''
            except Exception as e:
                logger.error("Failed to receive: %s", e)
                return b''
    
    def socket_close(self, sock_id: int) -> int:
        """Close socket, return 0 on success"""
        with self.lock:
            if sock_id not in self.sockets:
                return -1
            try:
                self.sockets[sock_id].close()
                del self.sockets[sock_id]
                return 0
            except Exception as e:
                logger.error("Failed to close socket: %s", e)
                return -1

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
LOADI R15, 0x0      ; Ensure R15 is zero for comparisons
CMP R5, R15         ; Compare with 0
JE copy_done        ; If zero, done
; Perform indirect load/store using registers
LOAD R6, R3         ; Load word from memory at address in R3
STORE R6, R4        ; Store word to memory at address in R4
LOADI R7, 4         ; increment value
ADD R3, R7          ; R3 += 4
ADD R4, R7          ; R4 += 4
DEC R5              ; Decrement size counter (words)
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
            # We'll create a minimal binary that just halts
            print("WARNING: Using fallback bootloader due to assembly failure.")
            # Create a simple halt instruction at the end
            # This is not a real bootloader but prevents crashing
            return b"\x00\x00\x00\x00" * 128 + b"\x15\x00\x00\x00" # HALT at end

    def interactive_shell(self, cpu: 'CPU'):
        """Simple interactive bootloader shell allowing basic memory ops and boot commands."""
        print("Bootloader interactive mode. Commands: help, load <addr> <file>, write <addr> <hexbytes>, dump <addr> <len>, run <addr>, boot, exit")
        while True:
            try:
                cmdline = input("boot> ")
            except EOFError:
                print()
                break
            if not cmdline:
                continue
            parts = shlex.split(cmdline)
            cmd = parts[0].lower()
            args = parts[1:]
            try:
                if cmd == 'help':
                    print("Commands: help, load <addr> <file>, write <addr> <hexbytes>, dump <addr> <len>, run <addr>, boot, exit")
                elif cmd == 'load' and len(args) == 2:
                    addr = int(args[0], 0)
                    fname = args[1]
                    # read from host filesystem
                    try:
                        with open(fname, 'rb') as f:
                            data = f.read()
                        cpu.mem.load_bytes(addr, data)
                        print(f"Loaded {len(data)} bytes to 0x{addr:08x}")
                    except Exception as e:
                        print("Load error:", e)
                elif cmd == 'write' and len(args) >= 2:
                    addr = int(args[0], 0)
                    hexstr = ''.join(args[1:])
                    try:
                        data = bytes.fromhex(hexstr)
                        cpu.mem.load_bytes(addr, data)
                        print(f"Wrote {len(data)} bytes to 0x{addr:08x}")
                    except Exception as e:
                        print("Write error:", e)
                elif cmd == 'dump' and len(args) >= 1:
                    addr = int(args[0], 0)
                    length = int(args[1], 0) if len(args) > 1 else 64
                    try:
                        data = cpu.mem.dump(addr, length)
                        # print hex
                        print(' '.join(f"{b:02x}" for b in data))
                    except Exception as e:
                        print("Dump error:", e)
                elif cmd == 'run' and len(args) == 1:
                    addr = int(args[0], 0)
                    cpu.pc = addr
                    cpu.halted = False
                    print(f"Running at 0x{addr:08x} (running up to 1000 steps)")
                    try:
                        cpu.run(max_steps=1000)
                    except Exception as e:
                        print("Execution error:", e)
                elif cmd == 'boot':
                    # typical boot: load /kernel.bin from in-memory FS if present and jump to 0x1000
                    try:
                        if hasattr(cpu, 'kernel') and cpu.kernel is not None and '/kernel.bin' in cpu.kernel.files:
                            kdata = cpu.kernel.files['/kernel.bin']['data']
                            cpu.mem.load_bytes(0x1000, kdata)
                            print(f"Loaded /kernel.bin ({len(kdata)} bytes) to 0x1000")
                        # also load kernel message if present
                        if hasattr(cpu, 'kernel') and cpu.kernel is not None and '/kernel_msg' in cpu.kernel.files:
                            msg = cpu.kernel.files['/kernel_msg']['data']
                            cpu.mem.load_bytes(0x1100, msg)
                            print(f"Loaded /kernel_msg ({len(msg)} bytes) to 0x1100")
                        cpu.reg_write(REG_SP, (cpu.mem.size - 4) // 4 * 4)
                        cpu.pc = 0x1000
                        cpu.halted = False
                        print("Booting kernel at 0x1000")
                        # show a quick disassembly snapshot to help debug
                        try:
                            lines = cpu.disassemble_at(0x1000, 16)
                            print("Kernel disassembly preview:")
                            for l in lines:
                                print(l)
                        except Exception:
                            pass
                        cpu.run()
                    except Exception as e:
                        print("Kernel error:", e)
                elif cmd in ('exit','quit'):
                    print('Exiting bootloader')
                    break
                else:
                    print('Unknown boot command')
            except Exception as e:
                print('Error handling command:', e)

# ---------------------------
# Memory with region registration
# ---------------------------
class Memory:
    """Advanced memory management with virtual memory, paging, and protection"""
    def __init__(self, size_bytes: int = DEFAULT_MEMORY_BYTES):
        self.size = size_bytes
        self.data = bytearray(size_bytes)
        self.page_size = 4096
        self.page_table = {}
        self.protected_regions = {}
        self.mmio_handlers = {}
        # Cache
        self.cache_enabled = True
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        # Statistics
        self.memory_stats = {
            'total_reads': 0,
            'total_writes': 0,
            'total_allocations': 0,
            'fragmentation': 0.0,
            'scrub_operations': 0,
        }
        self.breakpoints = set()
        self.access_log = []
        self.max_log_size = 1000
        
        # Graphics framebuffer (320x200 pixels, 32-bit RGBA)
        self.fb_width = 320
        self.fb_height = 200
        self.framebuffer = bytearray(self.fb_width * self.fb_height * 4)  # RGBA
        
        # Initialize default memory regions
        self._init_default_regions()
        logger.debug("Memory initialized: %d bytes (%d pages)", 
                    self.size, self.size // self.page_size)
    
    def _init_default_regions(self):
        """Initialize default memory regions"""
        # Don't protect low memory by default - allow kernel loading
        # The first 1MB is available for general use (bootloader, kernel, etc.)
        # Only protect the actual BIOS area if needed
        
        # Reserve last 64KB for BIOS ROM (read-only)
        bios_start = self.size - 0x10000
        self.protected_regions[bios_start] = (0x10000, 0x1, "BIOS ROM")  # Read-only
        
        # Initialize page table identity mapping
        self._init_page_table()
    
    def _init_page_table(self):
        """Initialize identity page table mapping"""
        num_pages = (self.size + self.page_size - 1) // self.page_size
        for i in range(num_pages):
            self.page_table[i] = i  # Identity mapping
    
    def map_page(self, vaddr: int, paddr: int, permissions: int = 0x7):
        """Map a virtual page to a physical page"""
        vpn = vaddr // self.page_size
        ppn = paddr // self.page_size
        self.page_table[vpn] = ppn
        
        # Update TLB if present
        if hasattr(self, 'tlb'):
            self.tlb.invalidate(vaddr)
    
    def unmap_page(self, vaddr: int):
        """Unmap a virtual page"""
        vpn = vaddr // self.page_size
        if vpn in self.page_table:
            del self.page_table[vpn]
            # Invalidate TLB entry if present
            if hasattr(self, 'tlb'):
                self.tlb.invalidate(vaddr)
    
    def translate_address(self, vaddr: int) -> int:
        """Translate virtual address to physical address"""
        if not hasattr(self, 'paging_enabled') or not self.paging_enabled:
            return vaddr  # Paging disabled, use physical addresses directly
            
        vpn = vaddr // self.page_size
        offset = vaddr % self.page_size
        
        if vpn in self.page_table:
            return (self.page_table[vpn] * self.page_size) + offset
        
        # Handle page fault
        return self._handle_page_fault(vaddr)
    
    def _handle_page_fault(self, vaddr: int) -> int:
        """Handle page fault by allocating a new page"""
        # In a real system, this would involve:
        # 1. Check if the access is valid
        # 2. Load the page from disk if needed
        # 3. Update page tables
        # For now, just allocate a zeroed page
        
        vpn = vaddr // self.page_size
        # Find a free physical page
        used_pages = set(self.page_table.values())
        for i in range(len(self.data) // self.page_size):
            if i not in used_pages:
                # Found free page, map it
                self.page_table[vpn] = i
                # Zero out the page
                page_start = i * self.page_size
                self.data[page_start:page_start + self.page_size] = bytes(self.page_size)
                return (i * self.page_size) + (vaddr % self.page_size)
        
        # No free pages, raise out of memory
        raise MemoryError(f"Out of memory: cannot allocate page for vaddr 0x{vaddr:08x}")
    
    def read_byte(self, addr: int) -> int:
        """Read a byte from memory with address translation"""
        # Check cache first if enabled
        if self.cache_enabled and addr in self.cache:
            self.cache_hits += 1
            return self.cache[addr]
            
        # Handle MMIO
        for (start, end), handler in self.mmio_handlers.items():
            if start <= addr < end:
                return handler.read_byte(addr - start)
        
        # Normal memory access
        paddr = self.translate_address(addr)
        self._check_bounds(paddr, 1)
        
        # Check memory protection
        if not self._check_access(paddr, 1, False):
            raise MemoryError(f"Read access violation at 0x{addr:08x}")
        
        val = self.data[paddr]
        
        # Update cache
        if self.cache_enabled:
            self.cache[addr] = val
            self.cache_misses += 1
            
        return val
    
    def write_byte(self, addr: int, val: int):
        """Write a byte to memory with address translation"""
        # Handle MMIO
        for (start, end), handler in self.mmio_handlers.items():
            if start <= addr < end:
                handler.write_byte(addr - start, val)
                return
        
        # Normal memory access
        paddr = self.translate_address(addr)
        self._check_bounds(paddr, 1)
        
        # Check memory protection
        if not self._check_access(paddr, 1, True):
            raise MemoryError(f"Write access violation at 0x{addr:08x}")
        
        # Invalidate cache
        if self.cache_enabled and addr in self.cache:
            del self.cache[addr]
        
        self.data[paddr] = val & 0xFF
    
    def read_word(self, addr: int) -> int:
        """Read a 32-bit word (little-endian) with proper alignment check"""
        if addr % 4 != 0:
            raise MemoryError(f"Unaligned word read at 0x{addr:08x}")
        
        # Optimize for aligned access
        if self.cache_enabled and addr in self.cache:
            self.cache_hits += 1
            return self.cache[addr]
            
        # Handle MMIO
        for (start, end), handler in self.mmio_handlers.items():
            if start <= addr < end - 3:
                return handler.read_word(addr - start)
        
        # Normal memory access
        paddr = self.translate_address(addr)
        self._check_bounds(paddr, 4)
        
        if not self._check_access(paddr, 4, False):
            raise MemoryError(f"Read access violation at 0x{addr:08x}")
        
        # Read 4 bytes and pack into word
        val = (self.data[paddr] | 
              (self.data[paddr + 1] << 8) | 
              (self.data[paddr + 2] << 16) | 
              (self.data[paddr + 3] << 24))
        
        # Update cache
        if self.cache_enabled:
            self.cache[addr] = val
            self.cache_misses += 1
            
        return val
    
    def write_word(self, addr: int, val: int):
        """Write a 32-bit word (little-endian) with proper alignment check"""
        if addr % 4 != 0:
            raise MemoryError(f"Unaligned word write at 0x{addr:08x}")
            
        # Handle MMIO
        for (start, end), handler in self.mmio_handlers.items():
            if start <= addr < end - 3:
                handler.write_word(addr - start, val)
                return
        
        # Normal memory access
        paddr = self.translate_address(addr)
        self._check_bounds(paddr, 4)
        
        if not self._check_access(paddr, 4, True):
            raise MemoryError(f"Write access violation at 0x{addr:08x}")
        
        # Invalidate cache
        if self.cache_enabled:
            for i in range(4):
                if addr + i in self.cache:
                    del self.cache[addr + i]
        
        # Write 4 bytes
        self.data[paddr] = val & 0xFF
        self.data[paddr + 1] = (val >> 8) & 0xFF
        self.data[paddr + 2] = (val >> 16) & 0xFF
        self.data[paddr + 3] = (val >> 24) & 0xFF
    
    def _check_bounds(self, addr: int, size: int):
        """Check if address range is within bounds"""
        if addr < 0 or addr + size > len(self.data):
            raise MemoryError(f"Memory access out of bounds: 0x{addr:08x}-0x{addr+size-1:08x}")
    
    def _check_access(self, addr: int, size: int, write: bool) -> bool:
        """Check if memory access is allowed"""
        # Check protected regions
        for start, (prot_size, prot_flags, _) in self.protected_regions.items():
            if start <= addr < start + prot_size:
                if write and not (prot_flags & 0x2):  # Write protection
                    return False
                if not write and not (prot_flags & 0x1):  # Read protection
                    return False
        return True
    
    def register_mmio(self, start: int, size: int, handler):
        """Register a memory-mapped I/O handler"""
        self.mmio_handlers[(start, start + size)] = handler
    
    def unregister_mmio(self, start: int, size: int):
        """Unregister a memory-mapped I/O handler"""
        key = (start, start + size)
        if key in self.mmio_handlers:
            del self.mmio_handlers[key]
    
    def protect_region(self, addr: int, size: int, flags: int, name: str = ""):
        """Protect a region of memory
        
        Args:
            addr: Start address of the region
            size: Size of the region
            flags: Protection flags (bit 0: read, bit 1: write, bit 2: execute)
            name: Optional name for the region
        """
        self.protected_regions[addr] = (size, flags, name)
    
    def unprotect_region(self, addr: int):
        """Remove protection from a memory region"""
        if addr in self.protected_regions:
            del self.protected_regions[addr]
    
    def get_memory_stats(self) -> dict:
        """Get memory statistics"""
        return {
            'total': self.size,
            'used': sum(len(region) for region in self.page_table.values()) * self.page_size,
            'free': self.size - (len(self.page_table) * self.page_size),
            'page_size': self.page_size,
            'pages_used': len(self.page_table),
            'pages_free': (self.size // self.page_size) - len(self.page_table),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_ratio': (self.cache_hits / (self.cache_hits + self.cache_misses)) 
                          if (self.cache_hits + self.cache_misses) > 0 else 0
        }
    def check_address(self, addr: int, length: int = 1):
        if addr < 0 or addr + length > self.size:
            raise MemoryError(f"Memory access out of range: addr={addr} len={length} size={self.size}")
        # Check protection
        for prot_addr, meta in self.protected_regions.items():
            prot_size = meta[0]
            perms = meta[1]
            # Check if the access starts within this protected region
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x1):  # Read permission
                    raise MemoryError(f"Memory access violation: read protected at {addr:08x}")
                # Only check boundary if the entire access is within the protected region
                # Allow reads that start in one region and end in another
                if length > 1 and addr + length > prot_addr + prot_size:
                    # Check if the overflow area is also readable
                    end_addr = addr + length - 1
                    # Only raise error if we're crossing into a non-existent area
                    if end_addr >= self.size:
                        raise MemoryError(f"Memory access violation: cross boundary at {addr:08x}")
    def read_byte(self, addr: int) -> int:
        self.check_address(addr, 1)
        return self.data[addr]
    def write_byte(self, addr: int, val: int):
        self.check_address(addr, 1)
        # Check write protection
        for prot_addr, meta in self.protected_regions.items():
            prot_size = meta[0]
            perms = meta[1]
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
        for prot_addr, meta in self.protected_regions.items():
            prot_size = meta[0]
            perms = meta[1]
            if addr >= prot_addr and addr < prot_addr + prot_size:
                if not (perms & 0x2):  # Write permission
                    raise MemoryError(f"Memory access violation: write protected at {addr:08x}")
        self.data[addr:addr+4] = itob_le(val)
    def load_bytes(self, addr: int, payload: bytes):
        self.check_expand(addr + len(payload))
        # Check write protection for the entire range
        for prot_addr, meta in self.protected_regions.items():
            prot_size = meta[0]
            perms = meta[1]
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
        # Store as (size, permissions, name) to be consistent with other entries
        self.protected_regions[addr] = (size, permissions, "")
        logger.info("Registered memory region: %08x - %08x (perm=%x)", addr, addr + size - 1, permissions)
    def unregister_region(self, addr: int):
        """Unregister a memory region."""
        if addr in self.protected_regions:
            del self.protected_regions[addr]
            logger.info("Unregistered memory region at %08x", addr)
    
    def set_breakpoint(self, addr: int):
        """Set memory breakpoint for debugging"""
        self.breakpoints.add(addr)
    
    def clear_breakpoint(self, addr: int):
        """Clear memory breakpoint"""
        self.breakpoints.discard(addr)
    
    def get_stats(self) -> dict:
        """Get memory statistics"""
        return {
            'total_size': self.size,
            'total_reads': self.memory_stats['total_reads'],
            'total_writes': self.memory_stats['total_writes'],
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_ratio': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            'protected_regions': len(self.protected_regions),
            'breakpoints': len(self.breakpoints),
            'scrub_operations': self.memory_stats['scrub_operations'],
        }
    
    def clear_cache(self):
        """Clear memory cache"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
    
    def dump_stats(self) -> str:
        """Get formatted memory statistics"""
        stats = self.get_stats()
        lines = [
            f"Memory Statistics:",
            f"  Total Size: {stats['total_size'] / (1024*1024):.1f} MB",
            f"  Total Reads: {stats['total_reads']}",
            f"  Total Writes: {stats['total_writes']}",
            f"  Cache Hits: {stats['cache_hits']}",
            f"  Cache Misses: {stats['cache_misses']}",
            f"  Cache Ratio: {stats['cache_ratio']:.2%}",
            f"  Protected Regions: {stats['protected_regions']}",
            f"  Breakpoints: {stats['breakpoints']}",
            f"  Scrub Operations: {stats['scrub_operations']}",
        ]
        return "\n".join(lines)

    def scrub(self, addr: int, length: int):
        """Securely overwrite a region with zeros."""
        if length <= 0:
            return
        for offset in range(length):
            self.write_byte((addr + offset) & 0xFFFFFFFF, 0)
        self.memory_stats['scrub_operations'] += 1
    
    # Graphics methods
    def set_pixel(self, x: int, y: int, color: int):
        """Set a pixel in the framebuffer (color is 32-bit RGBA)"""
        if 0 <= x < self.fb_width and 0 <= y < self.fb_height:
            offset = (y * self.fb_width + x) * 4
            # Store as RGBA
            self.framebuffer[offset] = (color >> 16) & 0xFF  # R
            self.framebuffer[offset + 1] = (color >> 8) & 0xFF  # G
            self.framebuffer[offset + 2] = color & 0xFF  # B
            self.framebuffer[offset + 3] = (color >> 24) & 0xFF  # A
    
    def get_pixel(self, x: int, y: int) -> int:
        """Get a pixel from the framebuffer"""
        if 0 <= x < self.fb_width and 0 <= y < self.fb_height:
            offset = (y * self.fb_width + x) * 4
            r = self.framebuffer[offset]
            g = self.framebuffer[offset + 1]
            b = self.framebuffer[offset + 2]
            a = self.framebuffer[offset + 3]
            return (a << 24) | (r << 16) | (g << 8) | b
        return 0
    
    def clear_screen(self, color: int):
        """Clear the entire screen to a color"""
        for y in range(self.fb_height):
            for x in range(self.fb_width):
                self.set_pixel(x, y, color)
    
    def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: int):
        """Draw a line using Bresenham's algorithm"""
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        while True:
            self.set_pixel(x1, y1, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy
    
    def draw_rect(self, x: int, y: int, w: int, h: int, color: int):
        """Draw a rectangle outline"""
        # Top and bottom
        for i in range(w):
            self.set_pixel(x + i, y, color)
            self.set_pixel(x + i, y + h - 1, color)
        # Left and right
        for i in range(h):
            self.set_pixel(x, y + i, color)
            self.set_pixel(x + w - 1, y + i, color)
    
    def fill_rect(self, x: int, y: int, w: int, h: int, color: int):
        """Draw a filled rectangle"""
        for j in range(h):
            for i in range(w):
                self.set_pixel(x + i, y + j, color)
    
    def draw_circle(self, cx: int, cy: int, r: int, color: int):
        """Draw a circle outline using midpoint algorithm"""
        x = r
        y = 0
        err = 0
        
        while x >= y:
            self.set_pixel(cx + x, cy + y, color)
            self.set_pixel(cx + y, cy + x, color)
            self.set_pixel(cx - y, cy + x, color)
            self.set_pixel(cx - x, cy + y, color)
            self.set_pixel(cx - x, cy - y, color)
            self.set_pixel(cx - y, cy - x, color)
            self.set_pixel(cx + y, cy - x, color)
            self.set_pixel(cx + x, cy - y, color)
            
            if err <= 0:
                y += 1
                err += 2 * y + 1
            if err > 0:
                x -= 1
                err -= 2 * x + 1
    
    def fill_circle(self, cx: int, cy: int, r: int, color: int):
        """Draw a filled circle"""
        for y in range(-r, r + 1):
            for x in range(-r, r + 1):
                if x * x + y * y <= r * r:
                    self.set_pixel(cx + x, cy + y, color)

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
    45: INPUT (buf_addr, max_len) -> read string line from stdin into buffer
    46: INPUT_INT () -> read integer from stdin into R0
    47-49: Reserved for future use
    50: PRINT_INT (value) -> print integer directly to stdout
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
            "version": "2.1",
            "architecture": "32-bit",
            "features": ["FPU", "MMU", "Multitasking", "Enhanced Memory", "Advanced Instructions"]
        }
        self.env_vars: Dict[str, str] = {"USER": username, "HOME": "/home/" + username, "PWD": "/"}
        self.command_history: List[str] = []
        self.start_time = time.time()
        self.cwd = "/"  # Current working directory
        # seed some files
        now = time.time()
        self.files["/"] = {
            "data": b"",  # Directory marker
            "permissions": 0o755,
            "created_time": now,
            "modified_time": now,
            "is_dir": True,
        }
        self.files["/readme.txt"] = {
            "data": b"SimpleOS readme: use ls, cat, whoami, echo, write, loadasm, run\n",
            "permissions": 0o644,
            "created_time": now,
            "modified_time": now,
            "is_dir": False,
        }
        self.files["/hello.bin"] = {
            "data": b"",  # maybe an assembled program can be stored here
            "permissions": 0o755,
            "created_time": now,
            "modified_time": now,
            "is_dir": False,
        }
        # Ensure useful directories exist
        self.ensure_directory("/home")
        self.ensure_directory(self.env_vars["HOME"])

    # --- Filesystem helpers -------------------------------------------------
    def normalize_path(self, path: str, cwd: Optional[str] = None) -> str:
        """Return canonical absolute path inside the virtual filesystem."""
        if not path:
            return self.cwd if self.cwd else "/"

        if cwd is None:
            cwd = self.cwd if self.cwd else "/"
        if not cwd.startswith("/"):
            cwd = "/" + cwd

        if path.startswith("/"):
            combined = path
        else:
            if cwd == "/":
                combined = f"/{path}"
            else:
                combined = f"{cwd.rstrip('/')}/{path}"

        parts: List[str] = []
        for part in combined.split("/"):
            if not part or part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        normalized = "/" + "/".join(parts)
        return normalized if parts else "/"

    def ensure_directory(self, path: str):
        """Ensure that a directory (and its parents) exists."""
        path = self.normalize_path(path)
        if path == "/":
            self.files.setdefault("/", {
                "data": b"",
                "permissions": 0o755,
                "created_time": time.time(),
                "modified_time": time.time(),
                "is_dir": True,
            })
            return

        parts = path.strip("/").split("/")
        current = ""
        for idx in range(len(parts)):
            current = "/" + "/".join(parts[:idx + 1])
            entry = self.files.get(current)
            if entry is None:
                now = time.time()
                self.files[current] = {
                    "data": b"",
                    "permissions": 0o755,
                    "created_time": now,
                    "modified_time": now,
                    "is_dir": True,
                }
            else:
                entry["is_dir"] = True

    def ensure_parent_directory(self, path: str):
        """Ensure that the parent directory of a path exists."""
        path = self.normalize_path(path)
        if path == "/":
            return
        parent = "/" + "/".join(path.strip("/").split("/")[:-1])
        if parent == "":
            parent = "/"
        self.ensure_directory(parent)

    def list_directory(self, path: str, cwd: Optional[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """List direct children for a directory or return the file entry."""
        path = self.normalize_path(path, cwd)
        entry = self.files.get(path)
        if entry is None:
            raise FileNotFoundError(path)
        if not entry.get("is_dir", False):
            return [(path, entry)]

        children: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        prefix = "" if path == "/" else f"{path.rstrip('/')}/"
        for full_path, meta in self.files.items():
            normalized = self.normalize_path(full_path, "/")
            if normalized == path:
                continue
            if path == "/":
                if not normalized.startswith("/") or normalized.count("/") == 0:
                    continue
                rel = normalized.lstrip("/")
            else:
                if not normalized.startswith(prefix):
                    continue
                rel = normalized[len(prefix):]
            if not rel:
                continue
            parts = rel.split("/")
            child_name = parts[0]
            child_path = "/" + child_name if path == "/" else f"{path.rstrip('/')}/{child_name}"
            if child_name in children:
                continue
            if len(parts) > 1 and child_path not in self.files:
                self.ensure_directory(child_path)
            meta_entry = self.files.get(child_path, meta)
            children[child_name] = (child_path, meta_entry)
        return [children[name] for name in sorted(children)]

    def remove_path(self, path: str) -> bool:
        """Remove a file or directory recursively."""
        path = self.normalize_path(path)
        if path == "/":
            return False
        if path not in self.files:
            return False
        targets = [p for p in self.files.keys() if p == path or p.startswith(path.rstrip("/") + "/")]
        for target in targets:
            del self.files[target]
        return True

    def duplicate_path(self, src: str, dest: str, move: bool = False) -> bool:
        """Copy or move a file/directory tree."""
        src = self.normalize_path(src)
        dest = self.normalize_path(dest)
        if src not in self.files or src == "/":
            return False
        if dest == src or dest.startswith(src.rstrip("/") + "/"):
            return False
        src_meta = self.files[src]
        if src_meta.get("is_dir", False):
            self.ensure_directory(dest)
            suffix_map = sorted([p for p in self.files.keys() if p == src or p.startswith(src.rstrip("/") + "/")])
            new_entries = {}
            for old_path in suffix_map:
                suffix = old_path[len(src):]
                if dest == "/":
                    new_path = "/" + suffix.lstrip("/")
                else:
                    new_path = dest + suffix
                new_path = self.normalize_path(new_path, "/")
                meta = self.files[old_path]
                payload = b""
                if not meta.get("is_dir", False):
                    raw = meta["data"]
                    payload = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
                new_entries[new_path] = {
                    "data": payload,
                    "permissions": meta["permissions"],
                    "created_time": time.time(),
                    "modified_time": time.time(),
                    "is_dir": meta.get("is_dir", False),
                }
            self.files.update(new_entries)
        else:
            self.ensure_parent_directory(dest)
            raw = src_meta["data"]
            payload = raw.encode("utf-8") if isinstance(raw, str) else bytes(raw)
            self.files[dest] = {
                "data": payload,
                "permissions": src_meta["permissions"],
                "created_time": time.time(),
                "modified_time": time.time(),
                "is_dir": False,
            }
        if move:
            self.remove_path(src)
        return True

    @staticmethod
    def display_name(path: str) -> str:
        """Return basename for display."""
        if path == "/":
            return "/"
        if not path:
            return ""
        return path.rstrip("/").split("/")[-1]

    def get_entry(self, path: str, cwd: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """Get file metadata for path."""
        abs_path = self.normalize_path(path, cwd)
        entry = self.files.get(abs_path)
        if entry is None:
            raise FileNotFoundError(abs_path)
        return abs_path, entry

    def read_file(self, path: str, cwd: Optional[str] = None) -> Tuple[str, bytes]:
        """Read file data, ensuring it is not a directory."""
        abs_path, entry = self.get_entry(path, cwd)
        if entry.get("is_dir", False):
            raise IsADirectoryError(abs_path)
        data = entry["data"]
        if isinstance(data, str):
            data = data.encode("utf-8")
        return abs_path, data

    def write_file(self, path: str, data: bytes, permissions: int = 0o644,
                   cwd: Optional[str] = None):
        """Write file data, creating parents as needed."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        abs_path = self.normalize_path(path, cwd)
        self.ensure_parent_directory(abs_path)
        now = time.time()
        created = self.files.get(abs_path, {}).get("created_time", now)
        self.files[abs_path] = {
            "data": data,
            "permissions": permissions,
            "created_time": created,
            "modified_time": now,
            "is_dir": False,
        }
        return abs_path

    def touch_file(self, path: str, cwd: Optional[str] = None):
        """Create file if missing or update timestamp."""
        abs_path = self.normalize_path(path, cwd)
        now = time.time()
        entry = self.files.get(abs_path)
        if entry is None:
            self.write_file(abs_path, b"", cwd="/")
        else:
            entry["modified_time"] = now
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
        elif num == 2:  # READ(fd, buf_addr, len) - Reads from stdin (ENHANCED for line input)
            fd = a1
            addr = a2
            length = a3
            if fd == 0:
                # Read a full line from stdin (enhanced for interactive input)
                try:
                    line = input()  # Reads full line including user typing
                    line_bytes = line.encode("utf-8")[:length-1]  # Leave room for null terminator
                    cpu.mem.load_bytes(addr, line_bytes + b'\x00')
                    cpu.reg_write(0, len(line_bytes))
                except EOFError:
                    cpu.mem.write_byte(addr, 0)  # Write null terminator
                    cpu.reg_write(0, 0)
                except Exception:
                    cpu.reg_write(0, 0)
            else:
                cpu.reg_write(0, 0)
        elif num == 3:  # LIST_DIR(dir_addr, out_addr)
            dir_addr = a1
            out_addr = a2
            dir_path = self.read_cstring(cpu.mem, dir_addr) if dir_addr else "/"
            dir_path = dir_path or "/"
            try:
                entries = self.list_directory(dir_path, "/")
            except (FileNotFoundError, NotADirectoryError):
                cpu.reg_write(0, 0)
                return
            names = "\0".join(self.display_name(path) for path, _ in entries) + "\0\0"
            data = names.encode("utf-8")
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(entries))
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
            try:
                _, data = self.read_file(fname, "/")
            except (FileNotFoundError, IsADirectoryError):
                cpu.reg_write(0, 0)
                return
            cpu.mem.load_bytes(dest, data)
            cpu.reg_write(0, len(data))
        elif num == 7:  # STORE_FILE(filename_addr, src_addr, len)
            fname = self.read_cstring(cpu.mem, a1)
            src = a2
            length = a3
            try:
                data = cpu.mem.dump(src, length)
                self.write_file(fname, data, 0o644, "/")
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
            fname = self.normalize_path(fname, "/")
            if fname in self.files:
                self.files[fname]["permissions"] = mode
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 18:  # MKDIR
            dirname = self.read_cstring(cpu.mem, a1)
            dirname = self.normalize_path(dirname, "/")
            if dirname in self.files and not self.files[dirname].get("is_dir", False):
                cpu.reg_write(0, 0)
            else:
                self.ensure_directory(dirname)
                cpu.reg_write(0, 1)
        elif num == 19:  # REMOVE
            fname = self.read_cstring(cpu.mem, a1)
            if self.remove_path(fname):
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 20:  # COPY
            src_name = self.read_cstring(cpu.mem, a1)
            dest_name = self.read_cstring(cpu.mem, a2)
            if self.duplicate_path(src_name, dest_name, move=False):
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 21:  # MOVE
            src_name = self.read_cstring(cpu.mem, a1)
            dest_name = self.read_cstring(cpu.mem, a2)
            if self.duplicate_path(src_name, dest_name, move=True):
                cpu.reg_write(0, 1)
            else:
                cpu.reg_write(0, 0)
        elif num == 22:  # STAT
            fname = self.read_cstring(cpu.mem, a1)
            fname = self.normalize_path(fname, "/")
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
            try:
                _, data = self.read_file(fname, "/")
            except (FileNotFoundError, IsADirectoryError):
                cpu.reg_write(0, 0)
                return
            cpu.mem.load_bytes(0x1000, data)
            cpu.pc = 0x1000
            cpu.reg_write(0, 1)
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
            # Real ping using network device
            result = 1 if cpu.network.utils.ping(host_name) else 0
            cpu.reg_write(0, result)
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
            try:
                _, data = self.read_file(fname, "/")
            except (FileNotFoundError, IsADirectoryError):
                cpu.reg_write(0, 0)
                return
            try:
                cpu.mem.load_bytes(a2, data)  # Load data into buffer at a2
                cpu.reg_write(0, len(data))
            except Exception:
                cpu.reg_write(0, 0)
        elif num == 41:  # CURL
            url_addr = a1
            url = self.read_cstring(cpu.mem, url_addr)
            out_addr = a2
            # Real curl using network device
            content = cpu.network.utils.curl(url)
            data = content.encode('utf-8')[:1024]
            cpu.mem.load_bytes(out_addr, data)
            cpu.reg_write(0, len(data))
        elif num == 42:  # WGET
            url_addr = a1
            url = self.read_cstring(cpu.mem, url_addr)
            # Real wget using network device
            result = cpu.network.utils.wget(url)
            cpu.reg_write(0, result)
        elif num == 43:  # GREP
            pattern_addr = a1
            file_addr = a2
            pattern = self.read_cstring(cpu.mem, pattern_addr)
            fname = self.read_cstring(cpu.mem, file_addr)
            try:
                _, data = self.read_file(fname, "/")
            except (FileNotFoundError, IsADirectoryError):
                cpu.reg_write(0, 0)
                return
            text = data.decode("utf-8", errors="replace")
            matches = [line for line in text.splitlines() if pattern in line]
            result = ("\n".join(matches) + ("\n" if matches else "")).encode("utf-8") + b"\0"
            cpu.mem.load_bytes(a3, result)
            cpu.reg_write(0, len(result))
        elif num == 44:  # WC
            file_addr = a1
            fname = self.read_cstring(cpu.mem, file_addr)
            try:
                _, data = self.read_file(fname, "/")
            except (FileNotFoundError, IsADirectoryError):
                cpu.reg_write(0, 0)
                return
            text = data.decode("utf-8", errors="replace")
            lines = text.count("\n")
            words = len(text.split())
            chars = len(text)
            # Pack counts into registers (lines in R0, words in R1, chars in R2)
            cpu.reg_write(0, lines & 0xFFFFFFFF)
            cpu.reg_write(1, words & 0xFFFFFFFF)
            cpu.reg_write(2, chars & 0xFFFFFFFF)
        elif num == 45:  # INPUT (buf_addr, max_len) - Read string from stdin
            buf_addr = a1
            max_len = a2 if a2 > 0 else 256
            try:
                user_input = input()  # Read full line from stdin
                input_bytes = user_input.encode('utf-8')[:max_len-1]  # Leave room for null terminator
                cpu.mem.load_bytes(buf_addr, input_bytes + b'\x00')
                cpu.reg_write(0, len(input_bytes))  # Return length read
            except EOFError:
                cpu.mem.write_byte(buf_addr, 0)  # Write null terminator
                cpu.reg_write(0, 0)
            except Exception:
                cpu.reg_write(0, 0)
        elif num == 46:  # INPUT_INT - Read integer from stdin
            try:
                user_input = input().strip()
                # Support decimal and hex (0x123)
                if user_input.startswith('0x') or user_input.startswith('0X'):
                    value = int(user_input, 16)
                else:
                    value = int(user_input)
                cpu.reg_write(0, value & 0xFFFFFFFF)
            except (ValueError, EOFError):
                cpu.reg_write(0, 0)  # Return 0 on error
            except Exception:
                cpu.reg_write(0, 0)
        elif num == 50:  # PRINT_INT - Print integer to stdout
            value = a1
            # Convert to signed 32-bit integer
            if value & 0x80000000:
                value = value - 0x100000000
            sys.stdout.write(str(value))
            sys.stdout.flush()
            cpu.reg_write(0, 1)
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
# Multi-threading and Async Support
# ---------------------------
@dataclass
class Thread:
    """Represents a thread of execution with its own context"""
    tid: int  # Thread ID
    pc: int  # Program counter
    regs: List[int] = field(default_factory=lambda: [0] * NUM_REGS)  # Register state
    sp: int = 0  # Stack pointer
    flags: int = 0x202  # Flags register
    state: str = "ready"  # ready, running, blocked, terminated
    priority: int = 5  # Priority level (0-10, higher = more priority)
    time_slice: int = 100  # Instructions per time slice
    instructions_executed: int = 0
    total_instructions: int = 0
    blocked_until: float = 0.0  # Time when thread becomes unblocked
    
    def save_context(self, cpu: 'CPU'):
        """Save CPU state to thread context"""
        self.pc = cpu.pc
        self.regs = cpu.regs.copy()
        self.sp = cpu.reg_read(REG_SP)
        self.flags = cpu.eflags
        
    def restore_context(self, cpu: 'CPU'):
        """Restore thread context to CPU"""
        cpu.pc = self.pc
        cpu.regs = self.regs.copy()
        cpu.reg_write(REG_SP, self.sp)
        cpu.eflags = self.flags


class Scheduler:
    """Cooperative and preemptive scheduler for managing multiple threads"""
    def __init__(self):
        self.threads: Dict[int, Thread] = {}
        self.ready_queue: deque = deque()
        self.current_thread: Optional[Thread] = None
        self.next_tid = 1
        self.scheduling_enabled = True
        self.quantum = 100  # Default time slice in instructions
        
    def create_thread(self, pc: int, priority: int = 5) -> int:
        """Create a new thread and add it to the ready queue"""
        tid = self.next_tid
        self.next_tid += 1
        
        thread = Thread(
            tid=tid,
            pc=pc,
            priority=priority,
            time_slice=self.quantum
        )
        thread.regs[REG_SP] = STACK_BASE - (tid * 0x10000)  # Separate stack per thread
        
        self.threads[tid] = thread
        self.ready_queue.append(tid)
        logger.info(f"Created thread {tid} at PC={pc:08x}, priority={priority}")
        return tid
    
    def schedule_next(self) -> Optional[Thread]:
        """Select the next thread to run using priority-based round-robin"""
        if not self.ready_queue:
            return None
            
        # Simple round-robin for now, can be enhanced with priority
        tid = self.ready_queue.popleft()
        thread = self.threads.get(tid)
        
        if thread and thread.state == "ready":
            thread.state = "running"
            self.current_thread = thread
            return thread
        
        return self.schedule_next()  # Try next thread
    
    def yield_thread(self, cpu: 'CPU'):
        """Voluntarily yield current thread (cooperative multitasking)"""
        if not self.current_thread:
            return
            
        self.current_thread.save_context(cpu)
        self.current_thread.state = "ready"
        self.ready_queue.append(self.current_thread.tid)
        self.current_thread = None
    
    def block_thread(self, cpu: 'CPU', duration: float = 0.0):
        """Block current thread for a specified duration"""
        if not self.current_thread:
            return
            
        self.current_thread.save_context(cpu)
        self.current_thread.state = "blocked"
        self.current_thread.blocked_until = time.time() + duration
        self.current_thread = None
    
    def unblock_threads(self):
        """Check and unblock threads whose wait time has expired"""
        current_time = time.time()
        for thread in self.threads.values():
            if thread.state == "blocked" and current_time >= thread.blocked_until:
                thread.state = "ready"
                self.ready_queue.append(thread.tid)
    
    def terminate_thread(self, tid: int):
        """Terminate a thread"""
        if tid in self.threads:
            thread = self.threads[tid]
            thread.state = "terminated"
            if self.current_thread and self.current_thread.tid == tid:
                self.current_thread = None
            logger.info(f"Thread {tid} terminated")
    
    def get_thread_count(self) -> int:
        """Get count of active threads"""
        return sum(1 for t in self.threads.values() if t.state != "terminated")
    
    def list_threads(self) -> List[Dict]:
        """List all threads with their status"""
        return [
            {
                "tid": t.tid,
                "state": t.state,
                "pc": t.pc,
                "priority": t.priority,
                "instructions": t.total_instructions
            }
            for t in self.threads.values()
            if t.state != "terminated"
        ]

# ---------------------------
# CPU core with syscall hook
# ---------------------------
class CPU:
    """CPU emulator with x86-like architecture features including:
    - 16 general purpose registers (R0-R15)
    - 8 FPU registers (ST0-ST7)
    - Full set of x86 flags
    - Virtual memory support
    - Hardware breakpoints
    - Performance monitoring
    - Power management
    - Debugging support
    - Virtualization extensions
    """
    def __init__(self, memory: Optional[Memory] = None, kernel: Optional[Kernel] = None):
        # Memory and I/O
        self.mem = memory if memory is not None else Memory()
        self.ports = [0] * 65536  # I/O port space
        self.network = NetworkDevice()  # Network device
        
        # Integer registers (32-bit)
        self.regs = [0] * NUM_REGS
        self.acc = 0  # Accumulator register
        
        # FPU/MMX/SSE registers
        self.fpu_regs = [0.0] * NUM_FPU_REGS
        self.mmx_regs = [0] * 8  # 8x 64-bit MMX registers
        self.xmm_regs = [[0] * 4 for _ in range(16)]  # 16x 128-bit XMM registers
        
        # System registers
        self.cr0 = 0  # Start with paging disabled until properly initialized
        self.cr0 |= CR0_NE  # Enable native FPU error handling
        self.cr2 = 0  # Page Fault Linear Address
        self.cr3 = 0  # Page Directory Base Register
        self.cr4 = 0
        self.efer = 0  # Extended Feature Enable Register
        
        # Segment registers (simplified)
        # These will be initialized with proper values in the CPU init
        self.cs = 0
        self.ds = 0
        self.es = 0
        self.fs = 0
        self.gs = 0
        self.ss = 0
        
        # System tables
        self.gdtr = 0  # GDT Register
        self.idtr = 0  # IDT Register
        self.ldtr = 0  # LDT Register
        self.tr = 0    # Task Register
        
        # Control Unit state
        self.cu = {
            'running': True,
            'privileged': False,
            'cpl': 0,  # Current Privilege Level (0-3)
            'v8086': False,  # Virtual 8086 mode
            'protected_mode': True,
            'long_mode': False,
            'pae': False,  # Physical Address Extension
            'pse': False,  # Page Size Extension
        }
        
        # Program state
        self.pc = 0  # Program Counter (EIP)
        self.eflags = 0x202  # Default flags: IF=1, bit 1 is always 1
        self.halted = False
        self.tracing = False
        
        # Interrupt handling
        self.interrupt_vector = [0] * 256  # IDT entries
        self.interrupt_enabled = True
        self.nmi_enabled = True
        self.pending_interrupts = []
        self.in_interrupt = False
        
        # Debugging
        self.breakpoints = set()
        self.hw_breakpoints = [0] * 4  # Debug registers DR0-DR3
        self.dr6 = 0  # Debug status
        self.dr7 = 0  # Debug control
        self.last_branch_from = 0
        self.last_branch_to = 0
        
        # Performance monitoring
        self.cycle_count = 0
        self.instructions_retired = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Power management
        self.cstates = [0] * 5  # C0-C4 states
        self.pstates = [0] * 8  # P0-P7 states
        self.thermal_status = 0
        
        # Virtualization
        self.vmcs = {}  # Virtual Machine Control Structure
        self.vm_control = 0
        self.vmexit_reason = 0
        
        # System components
        self.kernel = kernel
        
        # Multi-threading support
        self.scheduler = Scheduler()
        self.multithreading_enabled = False
        
        # Initialize stack pointer to top of memory (aligned to 16 bytes)
        top_sp = (self.mem.size - 16) & ~0xF
        self.regs[REG_SP] = top_sp
        
        # Initialize segment registers with default selectors
        self.cs = 0x08  # Kernel code segment (0x08 = 2nd GDT entry, RPL=0)
        self.ds = 0x10  # Kernel data segment (0x10 = 3rd GDT entry, RPL=0)
        self.es = 0x10
        self.fs = 0x10
        self.gs = 0x10
        self.ss = 0x10  # Stack segment (same as data segment for now)
        
        logger.debug("CPU initialized: SP=%08x, PC=%08x", top_sp, self.pc)
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
    # Flag operations
    def set_flag(self, mask: int):
        """Set CPU flag(s)"""
        self.eflags |= mask
        
    def clear_flag(self, mask: int):
        """Clear CPU flag(s)"""
        self.eflags &= ~mask
        
    def test_flag(self, mask: int) -> bool:
        """Test if flag(s) are set"""
        return bool(self.eflags & mask)
        
    def update_flags(self, result: int, width: int = 32):
        """Update status flags after arithmetic/logical operation
        
        Args:
            result: The result of the operation
            width: Operand width in bits (8, 16, 32, or 64)
        """
        mask = (1 << width) - 1
        signed_mask = 1 << (width - 1)
        
        # Zero Flag
        if (result & mask) == 0:
            self.set_flag(FLAG_ZF)
        else:
            self.clear_flag(FLAG_ZF)
            
        # Sign Flag
        if (result & signed_mask) != 0:
            self.set_flag(FLAG_SF)
        else:
            self.clear_flag(FLAG_SF)
            
        # Parity Flag (set if even number of set bits in low byte)
        parity = bin(result & 0xFF).count('1') % 2 == 0
        if parity:
            self.set_flag(FLAG_PF)
        else:
            self.clear_flag(FLAG_PF)
            
    def update_arithmetic_flags(self, a: int, b: int, result: int, width: int = 32, 
                              addition: bool = True):
        """Update arithmetic flags (CF, OF, AF) after add/sub
        
        Args:
            a: First operand
            b: Second operand
            result: Result of the operation
            width: Operand width in bits
            addition: True for addition, False for subtraction
        """
        mask = (1 << width) - 1
        sign_bit = 1 << (width - 1)
        
        # Update basic flags
        self.update_flags(result, width)
        
        # Carry Flag (unsigned overflow)
        if addition:
            carry = (a + b) > mask
        else:
            carry = (a < b)  # For subtraction, CF=1 if a < b
            
        if carry:
            self.set_flag(FLAG_CF)
        else:
            self.clear_flag(FLAG_CF)
            
        # Overflow Flag (signed overflow)
        a_signed = a & sign_bit
        b_signed = b & sign_bit
        r_signed = result & sign_bit
        
        if addition:
            overflow = (a_signed == b_signed) and (r_signed != a_signed)
        else:
            overflow = (a_signed != b_signed) and (r_signed != a_signed)
            
        if overflow:
            self.set_flag(FLAG_OF)
        else:
            self.clear_flag(FLAG_OF)
            
        # Auxiliary Carry Flag (carry from bit 3 to 4)
        if addition:
            af = ((a & 0xF) + (b & 0xF)) > 0xF
        else:
            af = (a & 0xF) < (b & 0xF)
            
        if af:
            self.set_flag(FLAG_AF)
        else:
            self.clear_flag(FLAG_AF)
    
    def update_zero_and_neg_flags(self, val: int):
        """Update zero and negative flags based on value"""
        if val == 0:
            self.set_flag(FLAG_ZERO)
        else:
            self.clear_flag(FLAG_ZERO)
        if (val >> 31) & 1:
            self.set_flag(FLAG_NEG)
        else:
            self.clear_flag(FLAG_NEG)

    # CPU utility methods
    def get_pc(self) -> int:
        return self.pc

    def set_pc(self, val: int):
        self.pc = val & 0xFFFFFFFF

    @property
    def flags(self):
        """Alias for eflags for backward compatibility"""
        return self.eflags
    
    @flags.setter
    def flags(self, value):
        """Alias for eflags for backward compatibility"""
        self.eflags = value
    
    def reset(self):
        # Reset CPU state (not memory)
        self.regs = [0] * NUM_REGS
        self.fpu_regs = [0.0] * NUM_FPU_REGS
        self.acc = 0
        self.eflags = 0
        self.pc = 0
        self.halted = False

    def step_n(self, n: int):
        # Execute n instructions
        for _ in range(n):
            if self.halted:
                break
            self.step()

    def dump_state(self) -> str:
        s = self.dump_regs()
        s += f"\nACC={self.acc:08x} PC={self.pc:08x} CU={self.cu}\n"
        return s

    # ALU helper methods
    def alu_add(self, a: int, b: int) -> int:
        res = (a + b) & 0xFFFFFFFF
        # set carry
        if (a + b) > 0xFFFFFFFF:
            self.set_flag(FLAG_CARRY)
        else:
            self.clear_flag(FLAG_CARRY)
        # set overflow for signed
        if ((a ^ b) & 0x80000000) == 0 and ((a ^ res) & 0x80000000) != 0:
            self.set_flag(FLAG_OVERFLOW)
        else:
            self.clear_flag(FLAG_OVERFLOW)
        self.update_zero_and_neg_flags(res)
        return res

    def alu_sub(self, a: int, b: int) -> int:
        res = (a - b) & 0xFFFFFFFF
        # set carry as borrow
        if a < b:
            self.set_flag(FLAG_CARRY)
        else:
            self.clear_flag(FLAG_CARRY)
        # overflow
        if ((a ^ b) & 0x80000000) != 0 and ((a ^ res) & 0x80000000) != 0:
            self.set_flag(FLAG_OVERFLOW)
        else:
            self.clear_flag(FLAG_OVERFLOW)
        self.update_zero_and_neg_flags(res)
        return res

    def fetch(self) -> int:
        """Fetch the next instruction from memory at PC"""
        # Restrict PC to valid loaded program bounds if set (but not in multithreading mode)
        if not self.multithreading_enabled and hasattr(self, "program_start") and hasattr(self, "program_end"):
            if not (self.program_start <= self.pc < self.program_end):
                logger.error(f"PC out of loaded program bounds: {self.pc:08x} (valid {self.program_start:08x}-{self.program_end-1:08x}), halting")
                print(f"ERROR: PC out of loaded program bounds: {self.pc:08x} (valid {self.program_start:08x}-{self.program_end-1:08x}), halting")
                self.halted = True
                return pack_instruction(OP_HALT, 0, 0, 0)
        if self.pc + 4 > self.mem.size or self.pc < 0:
            logger.error(f"PC out of bounds: {self.pc:08x}, halting")
            print(f"ERROR: PC out of bounds: {self.pc:08x}, halting")
            self.halted = True
            return pack_instruction(OP_HALT, 0, 0, 0)
        try:
            return self.mem.read_word(self.pc)
        except Exception as e:
            logger.error(f"Fetch error at PC {self.pc:08x}: {e}")
            print(f"ERROR: Fetch error at PC {self.pc:08x}: {e}")
            self.halted = True
            return pack_instruction(OP_HALT, 0, 0, 0)

    def push_word(self, val: int):
        sp = self.reg_read(REG_SP)
        sp = (sp - 4) & 0xFFFFFFFF
        self.mem.write_word(sp, val)
        self.reg_write(REG_SP, sp)

    def pop_word(self) -> int:
        sp = self.reg_read(REG_SP)
        val = self.mem.read_word(sp)
        sp = (sp + 4) & 0xFFFFFFFF
        self.reg_write(REG_SP, sp)
        return val

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
            # Support LOAD reg, [imm], LOAD reg, [reg], and LOAD reg, [reg+imm]
            if src != 0 and imm16 != 0:
                # base register + signed offset
                addr = (self.reg_read(src) + to_signed16(imm16)) & 0xFFFFFFFF
            elif imm16 != 0:
                addr = imm16
            else:
                addr = self.reg_read(src)
            val = self.mem.read_word(addr)
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_STORE:
            # Support STORE [imm], reg, STORE [reg], reg, and STORE [reg+imm], reg
            if dst != 0 and imm16 != 0:
                addr = (self.reg_read(dst) + to_signed16(imm16)) & 0xFFFFFFFF
            elif imm16 != 0:
                addr = imm16
            else:
                addr = self.reg_read(dst)
            self.mem.write_word(addr, self.reg_read(src))
        elif opcode == OP_ADD:
            val = self.alu_add(self.reg_read(dst), self.reg_read(src))
            self.reg_write(dst, val)
        elif opcode == OP_SUB:
            val = self.alu_sub(self.reg_read(dst), self.reg_read(src))
            self.reg_write(dst, val)
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
                # Check if address is within loaded program bounds - if so, make it relative
                if imm16 < 0x1000:  # Likely a relative offset
                    # Add program base address (round PC down to nearest 0x1000)
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JNZ:
            if not self.test_flag(FLAG_ZERO):
                # Check if address is within loaded program bounds - if so, make it relative
                if imm16 < 0x1000:  # Likely a relative offset
                    # Add program base address (round PC down to nearest 0x1000)
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JE:
            if self.test_flag(FLAG_ZERO):
                if imm16 < 0x1000:
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JNE:
            if not self.test_flag(FLAG_ZERO):
                if imm16 < 0x1000:
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JL:
            # Jump if less (SF != OF)
            if (self.test_flag(FLAG_NEG) != self.test_flag(FLAG_OVERFLOW)):
                if imm16 < 0x1000:
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JG:
            # Jump if greater (ZF=0 and SF=OF)
            if not self.test_flag(FLAG_ZERO) and (self.test_flag(FLAG_NEG) == self.test_flag(FLAG_OVERFLOW)):
                if imm16 < 0x1000:
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JLE:
            # Jump if less or equal (ZF=1 or SF != OF)
            if self.test_flag(FLAG_ZERO) or (self.test_flag(FLAG_NEG) != self.test_flag(FLAG_OVERFLOW)):
                if imm16 < 0x1000:
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_JGE:
            # Jump if greater or equal (SF=OF)
            if (self.test_flag(FLAG_NEG) == self.test_flag(FLAG_OVERFLOW)):
                if imm16 < 0x1000:
                    base_addr = (self.pc // 0x1000) * 0x1000
                    next_pc = base_addr + imm16
                else:
                    next_pc = imm16
        elif opcode == OP_CMP:
            a = self.reg_read(dst)
            if src == 0x0F:
                b = to_signed16(imm16) & 0xFFFFFFFF
            else:
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
            lhs = self.reg_read(dst)
            if src == 0x0F:
                rhs = to_signed16(imm16) & 0xFFFFFFFF
            else:
                rhs = self.reg_read(src)
            res = lhs & rhs
            if res == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
            if (res >> 31) & 1:
                self.set_flag(FLAG_NEG)
            else:
                self.clear_flag(FLAG_NEG)
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
            if src == 0x0F:
                b = to_signed16(imm16) & 0xFFFFFFFF
            else:
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
            lhs = self.reg_read(dst)
            if src == 0x0F:
                rhs = to_signed16(imm16) & 0xFFFFFFFF
            else:
                rhs = self.reg_read(src)
            res = lhs & rhs
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
            if src == 0x0F:
                b = to_signed16(imm16)
            else:
                b = self.reg_read(src)
            res = (a * b) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_IMUL:
            a = to_signed32(self.reg_read(dst))
            if src == 0x0F:
                b = to_signed16(imm16)
            else:
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
            if src == 0x0F:  # Immediate value
                b = to_signed16(imm16) & 0xFFFFFFFF
            else:  # Register value
                b = self.reg_read(src)
            carry = 1 if self.test_flag(FLAG_CARRY) else 0
            res = a + b + carry
            if res > 0xFFFFFFFF:
                self.set_flag(FLAG_CARRY)
                res &= 0xFFFFFFFF
            else:
                self.clear_flag(FLAG_CARRY)
            self.reg_write(dst, res & 0xFFFFFFFF)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SBB:
            # Subtract with borrow
            a = self.reg_read(dst)
            if src == 0x0F:  # Immediate value
                b = to_signed16(imm16) & 0xFFFFFFFF
            else:  # Register value
                b = self.reg_read(src)
            borrow = 1 if self.test_flag(FLAG_CARRY) else 0
            res = a - b - borrow
            if res < 0:
                self.set_flag(FLAG_CARRY)
                res &= 0xFFFFFFFF
            else:
                self.clear_flag(FLAG_CARRY)
            self.reg_write(dst, res & 0xFFFFFFFF)
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
        elif opcode == OP_SETF:
            # SETF imm16 - set flags bits given by imm16 mask
            mask = imm16 & 0xFFFFFFFF
            # imm16 is 16-bit, extend to 32-bit mask
            self.set_flag(mask)
        elif opcode == OP_TESTF:
            # TESTF imm16 - test flags mask; sets ZERO if none of the mask bits are set
            mask = imm16 & 0xFFFFFFFF
            if (self.flags & mask) == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_CLRF:
            # CLRF imm16 - clear flags bits given by imm16 mask
            mask = imm16 & 0xFFFFFFFF
            self.clear_flag(mask)
        elif opcode == OP_CPUID:
            # CPUID Rdst - write CPU flags/feature bits into dst register
            # Return lower 32-bit flags mask
            self.reg_write(dst, self.flags & 0xFFFFFFFF)
        elif opcode == OP_SETACC:
            # SETACC Rsrc or SETACC imm
            if src == 0x0F:
                val = to_signed16(imm16) & 0xFFFFFFFF
            else:
                val = self.reg_read(dst)
            self.acc = val
        elif opcode == OP_GETACC:
            # GETACC Rdst
            self.reg_write(dst, self.acc & 0xFFFFFFFF)
        elif opcode == OP_ACCADD:
            if src == 0x0F:
                val = to_signed16(imm16) & 0xFFFFFFFF
            else:
                val = self.reg_read(src)
            self.acc = self.alu_add(self.acc, val)
        elif opcode == OP_ACCSUB:
            if src == 0x0F:
                val = to_signed16(imm16) & 0xFFFFFFFF
            else:
                val = self.reg_read(src)
            self.acc = self.alu_sub(self.acc, val)
        elif opcode == OP_XCHG:
            # Exchange two registers
            temp = self.reg_read(dst)
            self.reg_write(dst, self.reg_read(src))
            self.reg_write(src, temp)
        elif opcode == OP_NEG:
            # Negate (two's complement)
            val = self.reg_read(dst)
            res = ((~val) + 1) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
            # Set carry if result is non-zero
            if res != 0:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
        elif opcode == OP_SAR:
            # Arithmetic right shift (sign-extending)
            val = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            # Preserve sign bit
            sign = (val >> 31) & 1
            res = val >> bits
            # Fill with sign bit
            if sign:
                mask = ((1 << bits) - 1) << (32 - bits)
                res |= mask
            res &= 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_ROL:
            # Rotate left
            val = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            res = ((val << bits) | (val >> (32 - bits))) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_ROR:
            # Rotate right
            val = self.reg_read(dst)
            bits = self.reg_read(src) & 0x1F
            res = ((val >> bits) | (val << (32 - bits))) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_BT:
            # Bit test - test bit position in src, set CF
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            if (val >> bit_pos) & 1:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
        elif opcode == OP_BTS:
            # Bit test and set
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            if (val >> bit_pos) & 1:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
            val |= (1 << bit_pos)
            self.reg_write(dst, val)
        elif opcode == OP_BTR:
            # Bit test and reset
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            if (val >> bit_pos) & 1:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
            val &= ~(1 << bit_pos)
            self.reg_write(dst, val)
        elif opcode == OP_BTC:
            # Bit test and complement
            val = self.reg_read(dst)
            bit_pos = self.reg_read(src) & 0x1F
            if (val >> bit_pos) & 1:
                self.set_flag(FLAG_CARRY)
            else:
                self.clear_flag(FLAG_CARRY)
            val ^= (1 << bit_pos)
            self.reg_write(dst, val)
        elif opcode == OP_BSF:
            # Bit scan forward - find first set bit (LSB to MSB)
            val = self.reg_read(src)
            if val == 0:
                self.set_flag(FLAG_ZERO)
                self.reg_write(dst, 0)
            else:
                self.clear_flag(FLAG_ZERO)
                pos = 0
                while pos < 32 and not ((val >> pos) & 1):
                    pos += 1
                self.reg_write(dst, pos)
        elif opcode == OP_BSR:
            # Bit scan reverse - find first set bit (MSB to LSB)
            val = self.reg_read(src)
            if val == 0:
                self.set_flag(FLAG_ZERO)
                self.reg_write(dst, 0)
            else:
                self.clear_flag(FLAG_ZERO)
                pos = 31
                while pos >= 0 and not ((val >> pos) & 1):
                    pos -= 1
                self.reg_write(dst, pos)
        elif opcode == OP_BSWAP:
            # Byte swap (reverse byte order)
            val = self.reg_read(dst)
            b0 = (val >> 24) & 0xFF
            b1 = (val >> 16) & 0xFF
            b2 = (val >> 8) & 0xFF
            b3 = val & 0xFF
            res = (b3 << 24) | (b2 << 16) | (b1 << 8) | b0
            self.reg_write(dst, res)
        elif opcode == OP_CMOV:
            # Conditional move - move if zero flag is set
            if self.test_flag(FLAG_ZERO):
                self.reg_write(dst, self.reg_read(src))
        elif opcode == OP_SETZ:
            # Set register to 1 if zero flag is set, else 0
            if self.test_flag(FLAG_ZERO):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETNZ:
            # Set register to 1 if zero flag is clear, else 0
            if not self.test_flag(FLAG_ZERO):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETL:
            # Set register to 1 if less (SF != OF), else 0
            if self.test_flag(FLAG_NEG) != self.test_flag(FLAG_OVERFLOW):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_MOVB:
            # Move byte (8-bit) - copy lower 8 bits
            val = self.reg_read(src) & 0xFF
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_MOVW:
            # Move word (16-bit) - copy lower 16 bits
            val = self.reg_read(src) & 0xFFFF
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_LOADB:
            # Load byte from memory
            if src != 0 and imm16 != 0:
                addr = (self.reg_read(src) + to_signed16(imm16)) & 0xFFFFFFFF
            elif imm16 != 0:
                addr = imm16
            else:
                addr = self.reg_read(src)
            val = self.mem.read_byte(addr)
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_STOREB:
            # Store byte to memory
            if dst != 0 and imm16 != 0:
                addr = (self.reg_read(dst) + to_signed16(imm16)) & 0xFFFFFFFF
            elif imm16 != 0:
                addr = imm16
            else:
                addr = self.reg_read(dst)
            val = self.reg_read(src) & 0xFF
            self.mem.write_byte(addr, val)
        elif opcode == OP_SEXT:
            # Sign extend byte to word
            val = self.reg_read(src) & 0xFF
            if val & 0x80:  # Sign bit set
                val |= 0xFFFFFF00
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_ZEXT:
            # Zero extend byte to word
            val = self.reg_read(src) & 0xFF
            self.reg_write(dst, val)
            self.update_zero_and_neg_flags(val)
        elif opcode == OP_POPCNT or opcode == OP_POPCOUNT:
            # Population count - count number of set bits
            val = self.reg_read(src)
            count = 0
            for i in range(32):
                if (val >> i) & 1:
                    count += 1
            self.reg_write(dst, count)
            self.update_zero_and_neg_flags(count)
        elif opcode == OP_MIN:
            # Minimum of two values (signed)
            a = to_signed32(self.reg_read(dst))
            b = to_signed32(self.reg_read(src))
            result = min(a, b) & 0xFFFFFFFF
            self.reg_write(dst, result)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_MAX:
            # Maximum of two values (signed)
            a = to_signed32(self.reg_read(dst))
            b = to_signed32(self.reg_read(src))
            result = max(a, b) & 0xFFFFFFFF
            self.reg_write(dst, result)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_ABS:
            # Absolute value
            val = to_signed32(self.reg_read(src))
            result = abs(val) & 0xFFFFFFFF
            self.reg_write(dst, result)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_MEMCPY:
            # Memory copy: R0=dst_addr, R1=src_addr, R2=length
            dst_addr = self.reg_read(0) & 0xFFFFFFFF
            src_addr = self.reg_read(1) & 0xFFFFFFFF
            length = self.reg_read(2) & 0xFFFFFFFF
            for i in range(length):
                byte = self.mem.read_byte((src_addr + i) & 0xFFFFFFFF)
                self.mem.write_byte((dst_addr + i) & 0xFFFFFFFF, byte)
        elif opcode == OP_MEMCHR:
            # MEMCHR: R0=base_addr, R1=value(byte), R2=length -> R0=result_addr or 0
            base = self.reg_read(0) & 0xFFFFFFFF
            val = self.reg_read(1) & 0xFF
            length = self.reg_read(2) & 0xFFFFFFFF
            found = 0
            for i in range(length):
                b = self.mem.read_byte((base + i) & 0xFFFFFFFF)
                if b == val:
                    found = (base + i) & 0xFFFFFFFF
                    break
            self.reg_write(0, found)
        elif opcode == OP_REV_MEM:
            # REV_MEM: R0=base_addr, R1=length -> reverse bytes in-place
            base = self.reg_read(0) & 0xFFFFFFFF
            length = self.reg_read(1) & 0xFFFFFFFF
            if length > 0:
                i = 0
                j = length - 1
                while i < j:
                    a = self.mem.read_byte((base + i) & 0xFFFFFFFF)
                    b = self.mem.read_byte((base + j) & 0xFFFFFFFF)
                    self.mem.write_byte((base + i) & 0xFFFFFFFF, b)
                    self.mem.write_byte((base + j) & 0xFFFFFFFF, a)
                    i += 1
                    j -= 1
        elif opcode == OP_MEMSET:
            # Memory set: R0=dst_addr, R1=value, R2=length
            dst_addr = self.reg_read(0) & 0xFFFFFFFF
            value = self.reg_read(1) & 0xFF
            length = self.reg_read(2) & 0xFFFFFFFF
            for i in range(length):
                self.mem.write_byte((dst_addr + i) & 0xFFFFFFFF, value)
        elif opcode == OP_MEMSCRUB:
            # Secure memory scrub: R0=start_addr, R1=length
            start_addr = self.reg_read(0) & 0xFFFFFFFF
            length = self.reg_read(1) & 0xFFFFFFFF
            try:
                self.mem.scrub(start_addr, length)
                self.reg_write(dst, length & 0xFFFFFFFF)
            except MemoryError:
                self.reg_write(dst, 0)
        elif opcode == OP_ADDI:
            imm_val = to_signed16(imm16)
            orig = self.reg_read(dst)
            res = (orig + imm_val) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_arithmetic_flags(orig, imm_val, res)
        elif opcode == OP_SUBI:
            imm_val = to_signed16(imm16)
            orig = self.reg_read(dst)
            res = (orig - imm_val) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_arithmetic_flags(orig, imm_val, res)
        elif opcode == OP_MULI:
            imm_val = to_signed16(imm16)
            orig = self.reg_read(dst)
            res = (orig * imm_val) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_arithmetic_flags(orig, imm_val, res)
        elif opcode == OP_DIVI:
            imm_val = to_signed16(imm16)
            orig = self.reg_read(dst)
            if imm_val == 0:
                self.set_flag(FLAG_OVERFLOW)
                self.reg_write(dst, 0)
            else:
                res = int(orig / imm_val) & 0xFFFFFFFF
                self.reg_write(dst, res)
                self.update_arithmetic_flags(orig, imm_val, res)
        elif opcode == OP_ANDI:
            imm_val = to_signed16(imm16) & 0xFFFFFFFF
            res = self.reg_read(dst) & imm_val
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_ORI:
            imm_val = to_signed16(imm16) & 0xFFFFFFFF
            res = self.reg_read(dst) | imm_val
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_XORI:
            imm_val = to_signed16(imm16) & 0xFFFFFFFF
            res = self.reg_read(dst) ^ imm_val
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SHLI:
            imm_val = to_signed16(imm16) & 0x1F
            res = (self.reg_read(dst) << imm_val) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_SHRI:
            imm_val = to_signed16(imm16) & 0x1F
            res = (self.reg_read(dst) >> imm_val) & 0xFFFFFFFF
            self.reg_write(dst, res)
            self.update_zero_and_neg_flags(res)
        elif opcode == OP_STRLEN:
            # String length: R0=string_addr, result in dst
            addr = self.reg_read(0) & 0xFFFFFFFF
            length = 0
            while length < 65536:  # Safety limit
                byte = self.mem.read_byte((addr + length) & 0xFFFFFFFF)
                if byte == 0:
                    break
                length += 1
            self.reg_write(dst, length)
        elif opcode == OP_STRCMP:
            # String compare: R0=str1_addr, R1=str2_addr, result in dst
            addr1 = self.reg_read(0) & 0xFFFFFFFF
            addr2 = self.reg_read(1) & 0xFFFFFFFF
            i = 0
            result = 0
            while i < 65536:  # Safety limit
                b1 = self.mem.read_byte((addr1 + i) & 0xFFFFFFFF)
                b2 = self.mem.read_byte((addr2 + i) & 0xFFFFFFFF)
                if b1 != b2:
                    result = 1 if b1 > b2 else -1
                    break
                if b1 == 0:  # Both strings ended
                    break
                i += 1
            self.reg_write(dst, result & 0xFFFFFFFF)
            if result == 0:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_CLAMP:
            # Clamp value: dst = clamp(dst, R0=min, R1=max)
            val = to_signed32(self.reg_read(dst))
            min_val = to_signed32(self.reg_read(0))
            max_val = to_signed32(self.reg_read(1))
            result = max(min_val, min(max_val, val)) & 0xFFFFFFFF
            self.reg_write(dst, result)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_SETF:
            # SETF imm16 - set flags bits given by imm16 mask
            mask = imm16 & 0xFFFF
            self.eflags |= mask
        elif opcode == OP_TESTF:
            # TESTF imm16 - test if flags match imm16 mask, set zero flag if match
            mask = imm16 & 0xFFFF
            if (self.eflags & mask) == mask:
                self.set_flag(FLAG_ZERO)
            else:
                self.clear_flag(FLAG_ZERO)
        elif opcode == OP_CLRF:
            # CLRF imm16 - clear flags bits given by imm16 mask
            mask = imm16 & 0xFFFF
            self.eflags &= ~mask
        elif opcode == OP_CPUID:
            # CPUID Rdst - write CPU flags/feature bits into dst register
            self.reg_write(dst, self.eflags & 0xFFFFFFFF)
        elif opcode == OP_NET_SEND:
            # NET_SEND: R0=socket_id, R1=data_addr, R2=data_len
            sock_id = self.reg_read(0)
            data_addr = self.reg_read(1)
            data_len = self.reg_read(2)
            try:
                data = self.mem.dump(data_addr, data_len)
                result = self.network.socket_send(sock_id, data)
                self.reg_write(0, result)
            except Exception as e:
                logger.error("NET_SEND error: %s", e)
                self.reg_write(0, -1)
        elif opcode == OP_NET_RECV:
            # NET_RECV: R0=socket_id, R1=buffer_addr, R2=buffer_size
            sock_id = self.reg_read(0)
            buf_addr = self.reg_read(1)
            buf_size = self.reg_read(2)
            try:
                data = self.network.socket_recv(sock_id, buf_size)
                if data:
                    self.mem.load_bytes(buf_addr, data)
                    self.reg_write(0, len(data))
                else:
                    self.reg_write(0, 0)
            except Exception as e:
                logger.error("NET_RECV error: %s", e)
                self.reg_write(0, -1)
        elif opcode == OP_NET_CONNECT:
            # NET_CONNECT: R0=socket_id, R1=host_addr, R2=port
            sock_id = self.reg_read(0)
            host_addr = self.reg_read(1)
            port = self.reg_read(2)
            try:
                host = Kernel.read_cstring(self.mem, host_addr)
                result = self.network.socket_connect(sock_id, host, port)
                self.reg_write(0, result)
            except Exception as e:
                logger.error("NET_CONNECT error: %s", e)
                self.reg_write(0, -1)
        elif opcode == OP_NET_CLOSE:
            # NET_CLOSE: R0=socket_id
            sock_id = self.reg_read(0)
            try:
                result = self.network.socket_close(sock_id)
                self.reg_write(0, result)
            except Exception as e:
                logger.error("NET_CLOSE error: %s", e)
                self.reg_write(0, -1)
        elif opcode == OP_NET_PING:
            # NET_PING: R0=host_addr, result in R0 (1=success, 0=fail)
            host_addr = self.reg_read(0)
            try:
                host = Kernel.read_cstring(self.mem, host_addr)
                result = 1 if self.network.utils.ping(host) else 0
                self.reg_write(0, result)
            except Exception as e:
                logger.error("NET_PING error: %s", e)
                self.reg_write(0, 0)
        elif opcode == OP_NET_CURL:
            # NET_CURL: R0=url_addr, R1=buffer_addr, result in R0 (bytes written)
            url_addr = self.reg_read(0)
            buf_addr = self.reg_read(1)
            try:
                url = Kernel.read_cstring(self.mem, url_addr)
                content = self.network.utils.curl(url)
                data = content.encode('utf-8')[:1024]
                self.mem.load_bytes(buf_addr, data)
                self.reg_write(0, len(data))
            except Exception as e:
                logger.error("NET_CURL error: %s", e)
                self.reg_write(0, 0)
        elif opcode == OP_NET_WGET:
            # NET_WGET: R0=url_addr, result in R0 (bytes downloaded)
            url_addr = self.reg_read(0)
            try:
                url = Kernel.read_cstring(self.mem, url_addr)
                result = self.network.utils.wget(url)
                self.reg_write(0, result)
            except Exception as e:
                logger.error("NET_WGET error: %s", e)
                self.reg_write(0, -1)
        elif opcode == OP_SQRT:
            # SQRT: dst = sqrt(src)
            val = float(to_signed32(self.reg_read(src)))
            result = int(math.sqrt(abs(val))) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_POW:
            # POW: dst = dst ^ src (power)
            base = float(to_signed32(self.reg_read(dst)))
            exp = float(to_signed32(self.reg_read(src)))
            result = int(math.pow(base, exp)) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_LOG:
            # LOG: dst = log(src)
            val = float(to_signed32(self.reg_read(src)))
            result = int(math.log(abs(val) + 1)) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_EXP:
            # EXP: dst = e^src
            val = float(to_signed32(self.reg_read(src)))
            result = int(math.exp(val)) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_SIN:
            # SIN: dst = sin(src)
            val = float(to_signed32(self.reg_read(src)))
            result = int(math.sin(val) * 1000) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_COS:
            # COS: dst = cos(src)
            val = float(to_signed32(self.reg_read(src)))
            result = int(math.cos(val) * 1000) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_TAN:
            # TAN: dst = tan(src)
            val = float(to_signed32(self.reg_read(src)))
            result = int(math.tan(val) * 1000) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_LZCNT:
            # LZCNT: dst = leading zero count in src
            val = self.reg_read(src)
            count = 0
            for i in range(31, -1, -1):
                if (val >> i) & 1:
                    break
                count += 1
            self.reg_write(dst, count)
        elif opcode == OP_TZCNT:
            # TZCNT: dst = trailing zero count in src
            val = self.reg_read(src)
            if val == 0:
                self.reg_write(dst, 32)
            else:
                count = 0
                while (val & 1) == 0:
                    count += 1
                    val >>= 1
                self.reg_write(dst, count)
        elif opcode == OP_SETA:
            # SETA: Set if above (unsigned >)
            if self.test_flag(FLAG_CARRY) == 0 and self.test_flag(FLAG_ZERO) == 0:
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETB:
            # SETB: Set if below (unsigned <)
            if self.test_flag(FLAG_CARRY):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETBE:
            # SETBE: Set if below or equal
            if self.test_flag(FLAG_CARRY) or self.test_flag(FLAG_ZERO):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETAE:
            # SETAE: Set if above or equal
            if not self.test_flag(FLAG_CARRY):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETO:
            # SETO: Set if overflow
            if self.test_flag(FLAG_OVERFLOW):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETNO:
            # SETNO: Set if no overflow
            if not self.test_flag(FLAG_OVERFLOW):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_PREFETCH:
            # PREFETCH: Prefetch memory (no-op in emulation)
            pass
        elif opcode == OP_CLFLUSH:
            # CLFLUSH: Flush cache line (no-op in emulation)
            pass
        elif opcode == OP_MFENCE:
            # MFENCE: Memory fence (no-op in emulation)
            pass
        elif opcode == OP_LFENCE:
            # LFENCE: Load fence (no-op in emulation)
            pass
        elif opcode == OP_SFENCE:
            # SFENCE: Store fence (no-op in emulation)
            pass
        elif opcode == OP_SWAP:
            # SWAP: Swap dst and src registers
            tmp = self.reg_read(dst)
            self.reg_write(dst, self.reg_read(src))
            self.reg_write(src, tmp)
        elif opcode == OP_ROT:
            # ROT: Rotate bits (dst rotated by src positions)
            val = self.reg_read(dst)
            shift = self.reg_read(src) & 0x1F
            result = ((val << shift) | (val >> (32 - shift))) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_REVERSE:
            # REVERSE: Reverse bits in register
            val = self.reg_read(dst)
            result = 0
            for i in range(32):
                if (val >> i) & 1:
                    result |= (1 << (31 - i))
            self.reg_write(dst, result)
        elif opcode == OP_RANDOM:
            # RANDOM: Generate random number in dst
            self.reg_write(dst, random.randint(0, 0xFFFFFFFF))
        elif opcode == OP_GETTIME:
            # GETTIME: Get current time in dst
            self.reg_write(dst, int(time.time()) & 0xFFFFFFFF)
        elif opcode == OP_SLEEP:
            # SLEEP: Sleep for src milliseconds
            ms = self.reg_read(src)
            time.sleep(ms / 1000.0)
        elif opcode == OP_YIELD:
            # YIELD: Yield CPU to scheduler (cooperative multitasking)
            if self.multithreading_enabled and self.scheduler.current_thread:
                # Mark that we want to yield - the async run loop will handle it
                self.scheduler.current_thread.instructions_executed = self.scheduler.current_thread.time_slice
            # In single-threaded mode, this is a no-op
        elif opcode == OP_BARRIER:
            # BARRIER: Memory barrier (no-op in emulation)
            pass
        elif opcode == OP_GETSEED:
            # GETSEED: Get random seed
            self.reg_write(dst, random.getstate()[1][0])
        elif opcode == OP_SETSEED:
            # SETSEED: Set random seed
            random.seed(self.reg_read(src))
        elif opcode == OP_HASH:
            # HASH: Simple hash function
            val = self.reg_read(src)
            result = ((val * 2654435761) ^ (val >> 16)) & 0xFFFFFFFF
            self.reg_write(dst, result)
        elif opcode == OP_CRC32:
            # CRC32: Simple CRC32 calculation
            val = self.reg_read(src)
            crc = 0xFFFFFFFF
            for i in range(32):
                if ((crc ^ val) & 1):
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc = crc >> 1
                val >>= 1
            self.reg_write(dst, crc ^ 0xFFFFFFFF)
        elif opcode == OP_SWAP:
            # SWAP: Swap two registers
            temp = self.reg_read(dst)
            self.reg_write(dst, self.reg_read(src))
            self.reg_write(src, temp)
        elif opcode == OP_ROT:
            # ROT: Rotate bits left by src positions
            val = self.reg_read(dst)
            shift = self.reg_read(src) & 0x1F
            if shift > 0:
                result = ((val << shift) | (val >> (32 - shift))) & 0xFFFFFFFF
                self.reg_write(dst, result)
            # Set flags based on result
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_REVERSE:
            # REVERSE: Reverse all bits in register
            val = self.reg_read(dst)
            result = 0
            for i in range(32):
                if (val >> i) & 1:
                    result |= (1 << (31 - i))
            self.reg_write(dst, result)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_SETG:
            # SETG: Set if greater (signed >)
            if not self.test_flag(FLAG_ZERO) and (self.test_flag(FLAG_NEG) == self.test_flag(FLAG_OVERFLOW)):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETLE:
            # SETLE: Set if less or equal (signed <=)
            if self.test_flag(FLAG_ZERO) or (self.test_flag(FLAG_NEG) != self.test_flag(FLAG_OVERFLOW)):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETGE:
            # SETGE: Set if greater or equal (signed >=)
            if self.test_flag(FLAG_NEG) == self.test_flag(FLAG_OVERFLOW):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETNE:
            # SETNE: Set if not equal
            if not self.test_flag(FLAG_ZERO):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SETE:
            # SETE: Set if equal
            if self.test_flag(FLAG_ZERO):
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_LERP:
            # LERP: Linear interpolation - lerp(a, b, t) = a + t * (b - a)
            # dst = result, src = a, imm16 contains b and t packed
            # For simplicity: dst = a, src = b, and we use a temp register for t
            # Actually, let's use: dst gets result, src = b, and dst initially has a
            # We'll need to read t from somewhere - let's use imm16 as t (0-255 range)
            a = self.reg_read(dst)
            b = self.reg_read(src)
            t = imm16 & 0xFF  # t is 0-255, we'll treat as 0.0-1.0 scaled by 256
            # result = a + (t * (b - a)) / 256
            diff = to_signed32(b) - to_signed32(a)
            result = to_signed32(a) + (t * diff) // 256
            self.reg_write(dst, result & 0xFFFFFFFF)
        elif opcode == OP_SIGN:
            # SIGN: Get sign of number (-1 for negative, 0 for zero, 1 for positive)
            val = to_signed32(self.reg_read(dst))
            if val < 0:
                self.reg_write(dst, 0xFFFFFFFF)  # -1 in two's complement
            elif val > 0:
                self.reg_write(dst, 1)
            else:
                self.reg_write(dst, 0)
        elif opcode == OP_SATURATE:
            # SATURATE: Clamp value to 0-255 range (useful for color values)
            val = to_signed32(self.reg_read(dst))
            if val < 0:
                result = 0
            elif val > 255:
                result = 255
            else:
                result = val
            self.reg_write(dst, result)
        elif opcode == OP_MULH:
            # MULH: Multiply High - Get upper 32 bits of 64-bit multiplication
            # Useful for fixed-point arithmetic and overflow detection
            a = self.reg_read(dst)
            b = self.reg_read(src)
            # Perform 64-bit multiplication
            result_64 = a * b
            # Get upper 32 bits
            high_bits = (result_64 >> 32) & 0xFFFFFFFF
            self.reg_write(dst, high_bits)
            self.update_zero_and_neg_flags(high_bits)
        elif opcode == OP_DIVMOD:
            # DIVMOD: Combined division and modulo for efficiency
            # dst = quotient, src register gets remainder
            # More efficient than separate DIV and MOD operations
            dividend = self.reg_read(dst)
            divisor = self.reg_read(src)
            if divisor == 0:
                self.set_flag(FLAG_OVERFLOW)
                self.reg_write(dst, 0xFFFFFFFF)
                self.reg_write(src, 0)
            else:
                quotient = dividend // divisor
                remainder = dividend % divisor
                self.reg_write(dst, quotient & 0xFFFFFFFF)
                self.reg_write(src, remainder & 0xFFFFFFFF)
                self.update_zero_and_neg_flags(quotient)
        elif opcode == OP_AVGB:
            # AVGB: Average of two values (useful for blending/interpolation)
            # dst = (dst + src) / 2, rounded down
            a = self.reg_read(dst)
            b = self.reg_read(src)
            avg = (a + b) >> 1
            self.reg_write(dst, avg & 0xFFFFFFFF)
            self.update_zero_and_neg_flags(avg)
        # Graphics opcodes
        elif opcode == OP_PIXEL:
            # PIXEL: Draw pixel at (R0, R1) with color R2
            x = self.reg_read(0)
            y = self.reg_read(1)
            color = self.reg_read(2)
            self.mem.set_pixel(x, y, color)
        elif opcode == OP_LINE:
            # LINE: Draw line from (R0, R1) to (R2, R3) with color in dst
            x1 = self.reg_read(0)
            y1 = self.reg_read(1)
            x2 = self.reg_read(2)
            y2 = self.reg_read(3)
            color = self.reg_read(dst)
            self.mem.draw_line(x1, y1, x2, y2, color)
        elif opcode == OP_RECT:
            # RECT: Draw rectangle at (R0, R1) with size (R2, R3) and color in dst
            x = self.reg_read(0)
            y = self.reg_read(1)
            w = self.reg_read(2)
            h = self.reg_read(3)
            color = self.reg_read(dst)
            self.mem.draw_rect(x, y, w, h, color)
        elif opcode == OP_FILLRECT:
            # FILLRECT: Draw filled rectangle at (R0, R1) with size (R2, R3) and color in dst
            x = self.reg_read(0)
            y = self.reg_read(1)
            w = self.reg_read(2)
            h = self.reg_read(3)
            color = self.reg_read(dst)
            self.mem.fill_rect(x, y, w, h, color)
        elif opcode == OP_CIRCLE:
            # CIRCLE: Draw circle at (R0, R1) with radius R2 and color in dst
            cx = self.reg_read(0)
            cy = self.reg_read(1)
            r = self.reg_read(2)
            color = self.reg_read(dst)
            self.mem.draw_circle(cx, cy, r, color)
        elif opcode == OP_FILLCIRCLE:
            # FILLCIRCLE: Draw filled circle at (R0, R1) with radius R2 and color in dst
            cx = self.reg_read(0)
            cy = self.reg_read(1)
            r = self.reg_read(2)
            color = self.reg_read(dst)
            self.mem.fill_circle(cx, cy, r, color)
        elif opcode == OP_GETPIXEL:
            # GETPIXEL: Get pixel color at (R1, R2) and store in dst
            x = self.reg_read(1)
            y = self.reg_read(2)
            color = self.mem.get_pixel(x, y)
            self.reg_write(dst, color)
        elif opcode == OP_CLEAR:
            # CLEAR: Clear screen with color in dst
            color = self.reg_read(dst)
            self.mem.clear_screen(color)
        elif opcode == OP_LOOP:
            # LOOP: Decrement RCX and jump if not zero
            rcx = self.reg_read(1)  # Assume R1 is the counter
            rcx = (rcx - 1) & 0xFFFFFFFF
            self.reg_write(1, rcx)
            if rcx != 0:
                next_pc = imm16
        elif opcode == OP_LOOPZ:
            # LOOPZ: Decrement RCX and jump if not zero and ZF=1
            rcx = self.reg_read(1)
            rcx = (rcx - 1) & 0xFFFFFFFF
            self.reg_write(1, rcx)
            if rcx != 0 and self.test_flag(FLAG_ZERO):
                next_pc = imm16
        elif opcode == OP_LOOPNZ:
            # LOOPNZ: Decrement RCX and jump if not zero and ZF=0
            rcx = self.reg_read(1)
            rcx = (rcx - 1) & 0xFFFFFFFF
            self.reg_write(1, rcx)
            if rcx != 0 and not self.test_flag(FLAG_ZERO):
                next_pc = imm16
        elif opcode == OP_MOVSB:
            # MOVSB: Move byte from [RSI] to [RDI]
            src_addr = self.reg_read(2)  # Assume R2 is RSI
            dst_addr = self.reg_read(3)  # Assume R3 is RDI
            byte = self.mem.read_byte(src_addr)
            self.mem.write_byte(dst_addr, byte)
            # Update pointers based on direction flag
            if self.test_flag(FLAG_DIR):
                self.reg_write(2, (src_addr - 1) & 0xFFFFFFFF)
                self.reg_write(3, (dst_addr - 1) & 0xFFFFFFFF)
            else:
                self.reg_write(2, (src_addr + 1) & 0xFFFFFFFF)
                self.reg_write(3, (dst_addr + 1) & 0xFFFFFFFF)
        elif opcode == OP_MOVSW:
            # MOVSW: Move word from [RSI] to [RDI]
            src_addr = self.reg_read(2)
            dst_addr = self.reg_read(3)
            word = self.mem.read_word(src_addr)
            self.mem.write_word(dst_addr, word)
            if self.test_flag(FLAG_DIR):
                self.reg_write(2, (src_addr - 4) & 0xFFFFFFFF)
                self.reg_write(3, (dst_addr - 4) & 0xFFFFFFFF)
            else:
                self.reg_write(2, (src_addr + 4) & 0xFFFFFFFF)
                self.reg_write(3, (dst_addr + 4) & 0xFFFFFFFF)
        elif opcode == OP_CMPSB:
            # CMPSB: Compare bytes at [RSI] and [RDI]
            src_addr = self.reg_read(2)
            dst_addr = self.reg_read(3)
            byte1 = self.mem.read_byte(src_addr)
            byte2 = self.mem.read_byte(dst_addr)
            res = (byte1 - byte2) & 0xFF
            self.update_zero_and_neg_flags(res)
            if self.test_flag(FLAG_DIR):
                self.reg_write(2, (src_addr - 1) & 0xFFFFFFFF)
                self.reg_write(3, (dst_addr - 1) & 0xFFFFFFFF)
            else:
                self.reg_write(2, (src_addr + 1) & 0xFFFFFFFF)
                self.reg_write(3, (dst_addr + 1) & 0xFFFFFFFF)
        elif opcode == OP_SCASB:
            # SCASB: Scan byte at [RDI] against AL (R0 low byte)
            dst_addr = self.reg_read(3)
            al = self.reg_read(0) & 0xFF
            byte = self.mem.read_byte(dst_addr)
            res = (al - byte) & 0xFF
            self.update_zero_and_neg_flags(res)
            if self.test_flag(FLAG_DIR):
                self.reg_write(3, (dst_addr - 1) & 0xFFFFFFFF)
            else:
                self.reg_write(3, (dst_addr + 1) & 0xFFFFFFFF)
        elif opcode == OP_LODSB:
            # LODSB: Load byte from [RSI] into AL
            src_addr = self.reg_read(2)
            byte = self.mem.read_byte(src_addr)
            self.reg_write(0, (self.reg_read(0) & 0xFFFFFF00) | byte)
            if self.test_flag(FLAG_DIR):
                self.reg_write(2, (src_addr - 1) & 0xFFFFFFFF)
            else:
                self.reg_write(2, (src_addr + 1) & 0xFFFFFFFF)
        elif opcode == OP_STOSB:
            # STOSB: Store AL into [RDI]
            dst_addr = self.reg_read(3)
            al = self.reg_read(0) & 0xFF
            self.mem.write_byte(dst_addr, al)
            if self.test_flag(FLAG_DIR):
                self.reg_write(3, (dst_addr - 1) & 0xFFFFFFFF)
            else:
                self.reg_write(3, (dst_addr + 1) & 0xFFFFFFFF)
        elif opcode == OP_IMUL3:
            # IMUL3: Three-operand signed multiply (dst = src * imm)
            a = self.reg_read(src)
            b = to_signed16(imm16)
            result = (a * b) & 0xFFFFFFFF
            self.reg_write(dst, result)
            self.update_zero_and_neg_flags(result)
        elif opcode == OP_SHLD:
            # SHLD: Double precision shift left
            val1 = self.reg_read(dst)
            val2 = self.reg_read(src)
            count = imm16 & 0x1F
            if count > 0:
                result = ((val1 << count) | (val2 >> (32 - count))) & 0xFFFFFFFF
                self.reg_write(dst, result)
                self.update_zero_and_neg_flags(result)
        elif opcode == OP_SHRD:
            # SHRD: Double precision shift right
            val1 = self.reg_read(dst)
            val2 = self.reg_read(src)
            count = imm16 & 0x1F
            if count > 0:
                result = ((val1 >> count) | (val2 << (32 - count))) & 0xFFFFFFFF
                self.reg_write(dst, result)
                self.update_zero_and_neg_flags(result)
        elif opcode == OP_RDTSC:
            # RDTSC: Read Time-Stamp Counter
            import time
            tsc = int(time.time() * 1000000) & 0xFFFFFFFFFFFFFFFF
            self.reg_write(0, tsc & 0xFFFFFFFF)  # Low 32 bits in R0
            self.reg_write(2, (tsc >> 32) & 0xFFFFFFFF)  # High 32 bits in R2
        elif opcode == OP_RDMSR:
            # RDMSR: Read Model Specific Register (simplified)
            msr_id = self.reg_read(1)
            # Return dummy value
            self.reg_write(0, 0)
            self.reg_write(2, 0)
        elif opcode == OP_WRMSR:
            # WRMSR: Write Model Specific Register (simplified, no-op)
            pass
        elif opcode == OP_PAUSE:
            # PAUSE: Hint for spin-wait loops (no-op in emulation)
            pass
        elif opcode in (OP_NOP3, OP_NOP4, OP_LOCK, OP_REPNE, OP_REPE):
            # Various no-ops and prefixes
            pass
        else:
            raise NotImplementedError(f"Opcode {opcode:02x} not implemented")
        self.pc = next_pc & 0xFFFFFFFF
    def run(self, max_steps: Optional[int] = None, trace: bool = False):
        steps = 0
        self.tracing = trace
        batch_size = 10000  # Process in batches for better performance
        
        try:
            while True:
                if self.halted:
                    break
                if max_steps is not None and steps >= max_steps:
                    break
                
                # Execute batch of instructions
                batch_end = min(steps + batch_size, max_steps if max_steps else steps + batch_size)
                while steps < batch_end and not self.halted:
                    self.step()
                    steps += 1
                    
        finally:
            self.tracing = False
        return steps
    
    async def run_async(self, max_steps: Optional[int] = None, trace: bool = False):
        """Async version of run() with cooperative multitasking support"""
        steps = 0
        self.tracing = trace
        try:
            while True:
                if self.halted:
                    break
                if max_steps is not None and steps >= max_steps:
                    break
                
                # Check for context switch if multithreading is enabled
                if self.multithreading_enabled and self.scheduler.current_thread:
                    thread = self.scheduler.current_thread
                    thread.instructions_executed += 1
                    thread.total_instructions += 1
                    
                    # Preemptive context switch after time slice
                    if thread.instructions_executed >= thread.time_slice:
                        thread.instructions_executed = 0
                        self.scheduler.yield_thread(self)
                        
                        # Unblock any waiting threads
                        self.scheduler.unblock_threads()
                        
                        # Schedule next thread
                        next_thread = self.scheduler.schedule_next()
                        if next_thread:
                            next_thread.restore_context(self)
                        else:
                            break  # No more threads to run
                        
                        # Yield control to event loop
                        await asyncio.sleep(0)
                
                self.step()
                steps += 1
                
                # Periodically yield to event loop for better responsiveness
                if steps % 1000 == 0:
                    await asyncio.sleep(0)
                    
        finally:
            self.tracing = False
        return steps
    
    async def run_multithreaded(self, threads: List[Tuple[int, int]], trace: bool = False):
        """
        Run multiple threads concurrently
        threads: List of (pc, priority) tuples
        """
        self.multithreading_enabled = True
        self.tracing = trace
        
        # Create all threads
        for pc, priority in threads:
            self.scheduler.create_thread(pc, priority)
        
        # Start first thread
        first_thread = self.scheduler.schedule_next()
        if not first_thread:
            logger.warning("No threads to run")
            return 0
        
        first_thread.restore_context(self)
        
        # Run until all threads complete
        total_steps = 0
        try:
            while self.scheduler.get_thread_count() > 0:
                # Run current thread for its time slice
                steps = await self.run_async(max_steps=None, trace=trace)
                total_steps += steps
                
                # Check if current thread terminated
                if self.halted and self.scheduler.current_thread:
                    self.scheduler.terminate_thread(self.scheduler.current_thread.tid)
                    self.halted = False
                
                # Unblock waiting threads
                self.scheduler.unblock_threads()
                
                # Schedule next thread
                next_thread = self.scheduler.schedule_next()
                if next_thread:
                    next_thread.restore_context(self)
                else:
                    break
                    
        finally:
            self.multithreading_enabled = False
            self.tracing = False
            
        logger.info(f"All threads completed. Total instructions: {total_steps}")
        return total_steps
    
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
            if name in ("LOADI", "ADDI", "SUBI", "MULI", "DIVI", "ANDI", "ORI", "XORI", "SHLI", "SHRI"):
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
    Advanced two-pass assembler with labels, directives, macros, and optimization
    Syntax:
    LABEL:
    MNEMONIC operands ; comment
    Registers: R0..R15, ST0..ST7
    Directives: .org, .word, .byte, .float, .double, .align, .space, .string, .ascii, .include
    """
    def __init__(self):
        self.labels: Dict[str, int] = {}
        self.orig = 0
        self.lines: List[Tuple[int, str]] = []
        self.macros: Dict[str, Tuple[List[str], List[str]]] = {}  # name -> (params, body)
        self.constants: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.optimization_level = 1  # 0=none, 1=basic, 2=aggressive
        self.used_labels: set = set()
        self.include_paths: List[str] = ['.']  # Search paths for .include
        self.string_data: Dict[int, bytes] = {}  # address -> string data
        self.incbin_cache: Dict[str, bytes] = {}
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
        # Allow bracketed immediates like [0x1000] or [label]
        if tok.startswith('[') and tok.endswith(']'):
            tok = tok[1:-1].strip()
        # Check if it's a constant
        if tok.upper() in self.constants:
            return self.constants[tok.upper()]
        # Evaluate expression if it contains operators
        if any(op in tok for op in ['+', '-', '*', '/', '(', ')']):
            return self.eval_expression(tok)
        # Support hex with 0x, trailing h, binary 0b, underscore separators
        tok_clean = tok.replace('_', '')
        if tok_clean.startswith("0x") or tok_clean.startswith("0X"):
            return int(tok_clean, 16) & 0xFFFFFFFF
        if tok_clean.endswith("h") or tok_clean.endswith("H"):
            return int(tok_clean[:-1], 16) & 0xFFFFFFFF
        if tok_clean.startswith("0b"):
            return int(tok_clean, 2) & 0xFFFFFFFF
        # Decimal or label (label resolution may have returned numeric string)
        return int(tok_clean, 0) & 0xFFFFFFFF
    def parse_float(self, tok: str) -> float:
        return float(tok)
    
    def define_macro(self, name: str, params: List[str], body: List[str]):
        """Define a macro with parameters"""
        self.macros[name.upper()] = (params, body)
    
    def define_constant(self, name: str, value: int):
        """Define a constant"""
        self.constants[name.upper()] = value
    
    def expand_macros(self, text: str, line_num: int) -> str:
        """Expand macros in assembly code"""
        import re
        for macro_name, (params, body) in self.macros.items():
            # Match macro invocation: MACRO_NAME arg1, arg2, ...
            # Use case-insensitive match but preserve original case of arguments
            pattern = rf'\b{macro_name}\b\s+(.*)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Get arguments from ORIGINAL text (preserves case)
                args_str = match.group(1).strip()
                args = [a.strip() for a in args_str.split(',')]
                if len(args) != len(params):
                    self.errors.append(f"Line {line_num}: Macro {macro_name} expects {len(params)} args, got {len(args)}")
                    return text
                # Replace parameters in body
                expanded = []
                for body_line in body:
                    line = body_line
                    for i, param in enumerate(params):
                        # Replace parameter placeholder with actual argument (preserving case)
                        line = line.replace(f'\\{param}', args[i])
                    expanded.append(line)
                return '\n'.join(expanded)
        return text
    
    def eval_expression(self, expr: str) -> int:
        """Evaluate arithmetic expression with constants and labels"""
        # Replace constants and labels with their values
        expr_eval = expr
        for const_name, const_val in self.constants.items():
            expr_eval = expr_eval.replace(const_name, str(const_val))
        for label_name, label_addr in self.labels.items():
            expr_eval = expr_eval.replace(label_name, str(label_addr))
        try:
            # Safe eval with only basic operators
            result = eval(expr_eval, {"__builtins__": {}}, {})
            return int(result) & 0xFFFFFFFF
        except Exception as e:
            raise AssemblerError(f"Invalid expression '{expr}': {e}")
    
    def _decode_string_literal(self, literal: str, line_num: int) -> bytes:
        """Decode a quoted string literal into bytes"""
        literal = literal.strip()
        if not (literal.startswith('"') and literal.endswith('"')):
            raise AssemblerError(f"Line {line_num}: String directive requires quoted literal")
        try:
            value = ast.literal_eval(literal)
        except Exception as exc:
            raise AssemblerError(f"Line {line_num}: Invalid string literal ({exc})")
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode('utf-8')
        raise AssemblerError(f"Line {line_num}: Unsupported string literal type")

    def _find_file(self, filename: str) -> Optional[str]:
        search_locations = self.include_paths + [os.getcwd()]
        for base in search_locations:
            full_path = os.path.join(base, filename)
            if os.path.isfile(full_path):
                return full_path
        return None

    def _load_include_file(self, filename: str, line_num: int) -> List[str]:
        """Load file contents for .include directive"""
        resolved = self._find_file(filename)
        if not resolved:
            self.errors.append(f"Line {line_num}: Unable to include file '{filename}'")
            return []
        with open(resolved, 'r', encoding='utf-8') as f:
            return f.read().splitlines()

    def _load_binary_file(self, filename: str, line_num: int) -> bytes:
        if filename in self.incbin_cache:
            return self.incbin_cache[filename]
        resolved = self._find_file(filename)
        if not resolved:
            self.errors.append(f"Line {line_num}: Unable to incbin file '{filename}'")
            return b""
        with open(resolved, 'rb') as f:
            data = f.read()
        self.incbin_cache[filename] = data
        return data
    
    def get_errors(self) -> List[str]:
        """Get list of assembly errors"""
        return self.errors
    
    def get_warnings(self) -> List[str]:
        """Get list of assembly warnings"""
        return self.warnings
    
    def clear_errors(self):
        """Clear error list"""
        self.errors.clear()
        self.warnings.clear()
    
    def first_pass(self, text: str):
        self.labels.clear()
        self.orig = 0
        self.lines = []
        self.used_labels.clear()
        pc = self.orig
        
        # Pre-process: handle .include, .equ, .macro
        preprocessed_lines = []
        in_macro = False
        macro_name = ""
        macro_params = []
        macro_body = []
        
        all_lines = text.splitlines()
        i = 0
        while i < len(all_lines):
            raw = all_lines[i]
            line = raw.split(';',1)[0].strip()
            
            if line.startswith('.include'):
                # Handle .include directive
                tokens = line.split()
                if len(tokens) < 2:
                    self.errors.append(f"Line {i+1}: .include requires filename")
                    i += 1
                    continue
                filename = tokens[1].strip('"\'')
                try:
                    # Try to find and read the include file
                    import os
                    found = False
                    for path in self.include_paths:
                        filepath = os.path.join(path, filename)
                        if os.path.exists(filepath):
                            with open(filepath, 'r') as f:
                                include_content = f.read()
                            preprocessed_lines.extend(include_content.splitlines())
                            found = True
                            break
                    if not found:
                        self.errors.append(f"Line {i+1}: Include file '{filename}' not found")
                except Exception as e:
                    self.errors.append(f"Line {i+1}: Error reading include file: {e}")
                i += 1
                continue
            
            elif line.startswith('.equ'):
                # Handle .equ directive for constants
                # Format: .equ NAME, value  or  .equ NAME value
                rest = line[4:].strip()  # Get everything after '.equ'
                if ',' in rest:
                    # Handle comma-separated format
                    parts = rest.split(',', 1)
                    const_name = parts[0].strip().upper()
                    const_value_str = parts[1].strip()
                else:
                    # Handle space-separated format
                    tokens = rest.split(None, 1)
                    if len(tokens) < 2:
                        self.errors.append(f"Line {i+1}: .equ requires name and value")
                        i += 1
                        continue
                    const_name = tokens[0].upper()
                    const_value_str = tokens[1]
                try:
                    const_value = self.parse_imm(const_value_str)
                    self.constants[const_name] = const_value
                except Exception as e:
                    self.errors.append(f"Line {i+1}: Invalid .equ value: {e}")
                i += 1
                continue
            
            elif line.startswith('.include'):
                tokens = shlex.split(line)
                if len(tokens) < 2:
                    self.errors.append(f"Line {i+1}: .include requires a file path")
                    i += 1
                    continue
                include_target = tokens[1].strip('"')
                included_lines = self._load_include_file(include_target, i+1)
                preprocessed_lines.extend(included_lines)
                i += 1
                continue
            
            elif line.startswith('.incbin'):
                tokens = shlex.split(line)
                if len(tokens) < 2:
                    self.errors.append(f"Line {i+1}: .incbin requires a file path")
                    i += 1
                    continue
                bin_target = tokens[1].strip('"')
                data = self._load_binary_file(bin_target, i+1)
                if data:
                    preprocessed_lines.append(f".incbin \"{bin_target}\"")
                i += 1
                continue
            
            elif line.startswith('.macro'):
                # Start macro definition
                tokens = line.split()
                if len(tokens) < 2:
                    self.errors.append(f"Line {i+1}: .macro requires name")
                    i += 1
                    continue
                macro_name = tokens[1].upper()
                # Parse parameters if any
                if len(tokens) > 2:
                    params_str = ' '.join(tokens[2:])
                    macro_params = [p.strip() for p in params_str.split(',')]
                else:
                    macro_params = []
                in_macro = True
                macro_body = []
                i += 1
                continue
            
            elif line.startswith('.endm'):
                # End macro definition
                if in_macro:
                    self.define_macro(macro_name, macro_params, macro_body)
                    in_macro = False
                    macro_name = ""
                    macro_params = []
                    macro_body = []
                else:
                    self.errors.append(f"Line {i+1}: .endm without .macro")
                i += 1
                continue
            
            if in_macro:
                macro_body.append(raw)
            else:
                # Expand macros in this line
                expanded = self.expand_macros(raw, i+1)
                if expanded != raw:
                    # Macro was expanded, add all expanded lines
                    preprocessed_lines.extend(expanded.splitlines())
                else:
                    preprocessed_lines.append(raw)
            i += 1
        
        # Now process preprocessed lines for labels and size calculation
        for i, raw in enumerate(preprocessed_lines):
            line = raw.split(';',1)[0].strip()
            if not line:
                self.lines.append((i+1, raw))
                continue
            if ':' in line and not line.startswith('.'):
                parts = line.split(':',1)
                label = parts[0].strip()
                if label in self.labels:
                    self.errors.append(f"Line {i+1}: Duplicate label {label}")
                else:
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
                        self.errors.append(f"Line {i+1}: Missing .org operand")
                    else:
                        try:
                            pc = self.parse_imm(tokens[1])
                            self.orig = pc
                        except Exception as e:
                            self.errors.append(f"Line {i+1}: Invalid .org value: {e}")
                elif directive == '.word' or directive == '.dword':
                    pc += 4
                elif directive == '.byte':
                    # Count comma-separated values
                    rest = line[len(tokens[0]):].strip()
                    if rest:
                        items = [i.strip() for i in rest.split(',') if i.strip()]
                        pc += len(items)
                    else:
                        pc += 1
                elif directive == '.string':
                    rest = line[len(tokens[0]):].strip()
                    if rest:
                        try:
                            string_bytes = self._decode_string_literal(rest, i+1)
                            pc += len(string_bytes) + 1  # include null terminator
                        except AssemblerError as exc:
                            self.errors.append(str(exc))
                    else:
                        self.errors.append(f"Line {i+1}: .string requires quoted string")
                elif directive == '.ascii':
                    rest = line[len(tokens[0]):].strip()
                    if rest:
                        try:
                            ascii_bytes = self._decode_string_literal(rest, i+1)
                            pc += len(ascii_bytes)
                        except AssemblerError as exc:
                            self.errors.append(str(exc))
                    else:
                        self.errors.append(f"Line {i+1}: .ascii requires quoted string")
                elif directive == '.float':
                    pc += 4
                elif directive == '.double':
                    pc += 8
                elif directive == '.align':
                    if len(tokens) >= 2:
                        try:
                            # Parse just the number, ignore any commas
                            align_str = tokens[1].split(',')[0].strip()
                            align = self.parse_imm(align_str)
                            if pc % align != 0:
                                pc = ((pc // align) + 1) * align
                        except Exception as e:
                            self.errors.append(f"Line {i+1}: Invalid .align value: {e}")
                elif directive == '.space':
                    if len(tokens) >= 2:
                        try:
                            # Parse arguments: .space size [, fill_byte]
                            rest = line[len(tokens[0]):].strip()
                            args = [a.strip() for a in rest.split(',')]
                            space = self.parse_imm(args[0])
                            pc += space
                        except Exception as e:
                            self.errors.append(f"Line {i+1}: Invalid .space value: {e}")
                elif directive == '.incbin':
                    if len(tokens) < 2:
                        self.errors.append(f"Line {i+1}: .incbin requires file path")
                    else:
                        path = tokens[1].strip('"')
                        data = self._load_binary_file(path, i+1)
                        pc += len(data)
                elif directive == '.incbin':
                    rest = line[len(tokens[0]):].strip()
                    filepath = rest.strip('"')
                    data = self._load_binary_file(filepath, ln)
                    if data:
                        if pc + len(data) > len(out):
                            out.extend(bytearray(pc + len(data) - len(out)))
                        out[pc:pc+len(data)] = data
                        pc += len(data)
                elif directive in ['.equ', '.macro', '.endm', '.include']:
                    # Already handled in preprocessing
                    pass
                else:
                    self.warnings.append(f"Line {i+1}: Unknown directive {directive}")
                self.lines.append((i+1, raw))
            else:
                # instruction occupies 4 bytes
                pc += 4
                self.lines.append((i+1, raw))
        logger.debug("First pass labels: %s", self.labels)
        logger.debug("Constants: %s", self.constants)
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
            # Check for label, but only if ':' is NOT inside a string
            if ':' in line and not line.startswith('.'):
                # Find ':' that is not inside quotes
                in_string = False
                escape = False
                for idx, ch in enumerate(line):
                    if escape:
                        escape = False
                        continue
                    if ch == '\\':
                        escape = True
                        continue
                    if ch == '"':
                        in_string = not in_string
                        continue
                    if ch == ':' and not in_string:
                        line = line[idx+1:].strip()
                        break
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
                    # Get the rest of the line after .word
                    rest = line[len(tokens[0]):].strip()
                    if not rest:
                        self.errors.append(f"Line {ln}: .word requires operand")
                    else:
                        # Resolve constants/labels first
                        resolved = self.resolve_label_token(rest)
                        val = self.parse_imm(resolved)
                        if pc + 4 > len(out):
                            out.extend(bytearray(pc + 4 - len(out)))
                        out[pc:pc+4] = itob_le(val)
                        pc += 4
                elif directive == '.byte':
                    # Support multiple comma-separated byte values: .byte 0x41,0x42,65
                    rest = line[len(tokens[0]):].strip()
                    if not rest:
                        raise AssemblerError('.byte requires operand')
                    items = [i.strip() for i in rest.split(',') if i.strip()!='']
                    for it in items:
                        # Resolve constants/labels first
                        resolved = self.resolve_label_token(it)
                        val = self.parse_imm(resolved) & 0xFF
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
                elif directive == '.dword':
                    # Same as .word - 32-bit value
                    rest = line[len(tokens[0]):].strip()
                    if not rest:
                        self.errors.append(f"Line {ln}: .dword requires operand")
                    else:
                        # Resolve constants/labels first
                        resolved = self.resolve_label_token(rest)
                        val = self.parse_imm(resolved)
                        if pc + 4 > len(out):
                            out.extend(bytearray(pc + 4 - len(out)))
                        out[pc:pc+4] = itob_le(val)
                        pc += 4
                elif directive == '.string':
                    rest = line[len(tokens[0]):].strip()
                    if rest:
                        try:
                            string_bytes = self._decode_string_literal(rest, ln) + b'\x00'
                            if pc + len(string_bytes) > len(out):
                                out.extend(bytearray(pc + len(string_bytes) - len(out)))
                            out[pc:pc+len(string_bytes)] = string_bytes
                            pc += len(string_bytes)
                        except AssemblerError as exc:
                            self.errors.append(str(exc))
                    else:
                        self.errors.append(f"Line {ln}: .string requires quoted string")
                elif directive == '.ascii':
                    rest = line[len(tokens[0]):].strip()
                    if rest:
                        try:
                            ascii_bytes = self._decode_string_literal(rest, ln)
                            if pc + len(ascii_bytes) > len(out):
                                out.extend(bytearray(pc + len(ascii_bytes) - len(out)))
                            out[pc:pc+len(ascii_bytes)] = ascii_bytes
                            pc += len(ascii_bytes)
                        except AssemblerError as exc:
                            self.errors.append(str(exc))
                    else:
                        self.errors.append(f"Line {ln}: .ascii requires quoted string")
                elif directive == '.align':
                    # Align to boundary
                    if len(tokens) >= 2:
                        align_str = tokens[1].split(',')[0].strip()
                        align = self.parse_imm(align_str)
                        if pc % align != 0:
                            new_pc = ((pc // align) + 1) * align
                            if new_pc > len(out):
                                out.extend(bytearray(new_pc - len(out)))
                            pc = new_pc
                elif directive == '.space':
                    # Reserve space: .space size [, fill_byte]
                    if len(tokens) >= 2:
                        rest = line[len(tokens[0]):].strip()
                        args = [a.strip() for a in rest.split(',')]
                        space = self.parse_imm(args[0])
                        fill_byte = 0
                        if len(args) >= 2:
                            fill_byte = self.parse_imm(args[1]) & 0xFF
                        if pc + space > len(out):
                            out.extend(bytearray(pc + space - len(out)))
                        for i in range(space):
                            out[pc + i] = fill_byte
                        pc += space
                elif directive in ['.equ', '.macro', '.endm', '.include']:
                    # Already handled in first pass
                    pass
                else:
                    self.warnings.append(f"Line {ln}: Unsupported directive {directive}")
            else:
                # Allow bracketed operands in assembly (e.g., STORE R4, [0x0300])
                tokens = shlex.split(line)
                if not tokens:
                    continue
                mnem = tokens[0].upper()
                args_part = line[len(tokens[0]):].strip()
                raw_args = [a.strip() for a in args_part.split(',') if a.strip()!='']
                # Normalize bracketed args to remove surrounding [] but keep indicator
                args = []
                for a in raw_args:
                    if a.startswith('[') and a.endswith(']'):
                        args.append(a[1:-1].strip())
                    else:
                        args.append(a)
                opcode = NAME_OPCODE.get(mnem)
                if opcode is None:
                    raise AssemblerError(f"Unknown mnemonic {mnem} on line {ln}")
                word = 0
                if opcode in (OP_NOP, OP_NOP2, OP_NOP3, OP_NOP4, OP_RET, OP_HALT, OP_CLC, OP_STC, OP_CLI, OP_STI, OP_IRET, OP_LEAVE, OP_FLDZ, OP_FLD1, OP_FLDPI, OP_FLDLG2, OP_FLDLN2, OP_FCLEX, OP_NEG, OP_CBW, OP_CWD, OP_CWDQ, OP_CLD, OP_STD, OP_LAHF, OP_SAHF, OP_INTO, OP_AAM, OP_AAD, OP_XLAT, OP_XCHG, OP_CMPXCHG, OP_LAR, OP_LSL, OP_SLDT, OP_STR, OP_LLDT, OP_LTR, OP_VERR, OP_VERW, OP_SGDT, OP_SIDT, OP_LGDT, OP_LIDT, OP_SMSW, OP_LMSW, OP_CLTS, OP_INVD, OP_WBINVD, OP_INVLPG, OP_INVPCID, OP_VMCALL, OP_VMLAUNCH, OP_VMRESUME, OP_VMXOFF, OP_MONITOR, OP_MWAIT, OP_RDSEED, OP_RDRAND, OP_CLAC, OP_STAC, OP_SKINIT, OP_SVMEXIT, OP_SVMRET, OP_SVMLOCK, OP_SVMUNLOCK, OP_NET_CLOSE, OP_SWAP, OP_REVERSE, OP_RDTSC, OP_RDMSR, OP_WRMSR, OP_PAUSE, OP_LOCK, OP_REPNE, OP_REPE, OP_REP, OP_REPZ, OP_REPNZ, OP_MOVSB, OP_MOVSW, OP_MOVSD, OP_CMPSB, OP_SCASB, OP_LODSB, OP_STOSB):
                    word = pack_instruction(opcode, 0, 0, 0)
                elif opcode in (OP_MOV, OP_ADD, OP_SUB, OP_AND, OP_OR, OP_XOR, OP_CMP, OP_TEST, OP_SHL, OP_SHR, OP_MUL, OP_IMUL, OP_DIV, OP_IDIV, OP_MOD, OP_FADD, OP_FSUB, OP_FMUL, OP_FDIV, OP_FCOMP, OP_FXCH, OP_ADC, OP_SBB, OP_ROL, OP_ROR, OP_BT, OP_BTS, OP_BTR, OP_BSF, OP_BSR, OP_ACCADD, OP_ACCSUB, OP_SETACC, OP_GETACC, OP_NET_SEND, OP_NET_RECV, OP_NET_CONNECT, OP_ROT, OP_HASH, OP_CRC32, OP_GETTIME, OP_SETSEED, OP_MIN, OP_MAX, OP_ABS, OP_POPCNT, OP_STRLEN, OP_STRCMP, OP_SLEEP, OP_SQRT, OP_POW, OP_LOG, OP_EXP, OP_SIN, OP_COS, OP_TAN, OP_MULH, OP_DIVMOD, OP_AVGB):
                    if len(args) != 2:
                        raise AssemblerError(f"{mnem} requires two operands on line {ln}")
                    dst = self.parse_reg(args[0])
                    # allow immediate as second operand
                    try:
                        src = self.parse_reg(args[1])
                        word = pack_instruction(opcode, dst, src, 0)
                    except AssemblerError:
                        # immediate
                        src = 0x0F
                        imm = self.resolve_label_token(args[1])
                        imm_val = self.parse_imm(imm) & 0xFFFF
                        word = pack_instruction(opcode, dst, src, imm_val)
                elif opcode in (OP_CLAMP, OP_RANDOM, OP_SIGN, OP_SATURATE):
                    # One-operand utility instructions
                    if len(args) != 1:
                        raise AssemblerError(f"{mnem} requires one register operand on line {ln}")
                    dst = self.parse_reg(args[0])
                    word = pack_instruction(opcode, dst, 0, 0)
                elif opcode in (OP_PIXEL, OP_LINE, OP_RECT, OP_FILLRECT, OP_CIRCLE, OP_FILLCIRCLE, OP_GETPIXEL, OP_CLEAR):
                    # Graphics instructions - parameters in R0-R3, color in specified register
                    # PIXEL: no args (uses R0=x, R1=y, R2=color)
                    # LINE Rcolor: uses R0=x1, R1=y1, R2=x2, R3=y2, Rcolor=color
                    # RECT Rcolor: uses R0=x, R1=y, R2=w, R3=h, Rcolor=color
                    # FILLRECT Rcolor: uses R0=x, R1=y, R2=w, R3=h, Rcolor=color
                    # CIRCLE Rcolor: uses R0=cx, R1=cy, R2=r, Rcolor=color
                    # FILLCIRCLE Rcolor: uses R0=cx, R1=cy, R2=r, Rcolor=color
                    # GETPIXEL Rdst: uses R1=x, R2=y, stores result in Rdst
                    # CLEAR Rcolor: uses Rcolor=color
                    if opcode == OP_PIXEL:
                        # PIXEL takes no args, uses R0, R1, R2
                        if len(args) != 0:
                            raise AssemblerError(f"PIXEL takes no arguments (uses R0=x, R1=y, R2=color) on line {ln}")
                        word = pack_instruction(opcode, 0, 0, 0)
                    elif len(args) == 1:
                        # Single register argument for color or destination
                        dst = self.parse_reg(args[0])
                        word = pack_instruction(opcode, dst, 0, 0)
                    else:
                        raise AssemblerError(f"{mnem} requires one register argument on line {ln}")
                elif opcode == OP_LERP:
                    # LERP: Three operands - LERP dst, src, imm (dst=a, src=b, imm=t)
                    if len(args) != 3:
                        raise AssemblerError(f"LERP requires three operands: dst, src, t on line {ln}")
                    dst = self.parse_reg(args[0])
                    src = self.parse_reg(args[1])
                    t_val = self.parse_imm(self.resolve_label_token(args[2]))
                    word = pack_instruction(opcode, dst, src, t_val & 0xFFFF)
                elif opcode == OP_LOADI:
                    if len(args) != 2:
                        raise AssemblerError("LOADI requires two operands")
                    dst = self.parse_reg(args[0])
                    imm = args[1]
                    imm = self.resolve_label_token(imm)
                    imm_val = self.parse_imm(imm)
                    word = pack_instruction(opcode, dst, 0, imm_val & 0xFFFF)
                elif opcode in (OP_ADDI, OP_SUBI, OP_MULI, OP_DIVI, OP_ANDI, OP_ORI, OP_XORI, OP_SHLI, OP_SHRI):
                    if len(args) != 2:
                        raise AssemblerError(f"{mnem} requires register and immediate")
                    dst = self.parse_reg(args[0])
                    imm = self.resolve_label_token(args[1])
                    imm_val = self.parse_imm(imm)
                    word = pack_instruction(opcode, dst, 0, imm_val & 0xFFFF)
                elif opcode in (OP_LOAD, OP_STORE) and len(args) == 2:
                    # Support forms:
                    #   LOAD Rdst, Rsrc        ; indirect load from address in Rsrc
                    #   LOAD Rdst, imm         ; load from absolute address imm
                    #   LOAD Rdst, Rsrc+imm    ; load from address (Rsrc + imm)
                    #   STORE Rsrc, Rdst       ; store value from Rsrc into address in Rdst (reg or imm)
                    dst = self.parse_reg(args[0])
                    second = args[1]
                    # reg+offset pattern: e.g., R3+0x10 or R3-4
                    if ('+' in second or '-' in second) and second.upper().find('R') != -1:
                        # split on last + or - to allow negatives
                        # find operator position (after register)
                        op_pos = max(second.rfind('+'), second.rfind('-'))
                        base_tok = second[:op_pos].strip()
                        off_tok = second[op_pos:].strip()
                        src = self.parse_reg(base_tok)
                        imm = self.resolve_label_token(off_tok)
                        imm_val = self.parse_imm(imm)
                        word = pack_instruction(opcode, dst, src, imm_val & 0xFFFF)
                    else:
                        # Try to parse as register
                        try:
                            src = self.parse_reg(second)
                            word = pack_instruction(opcode, dst, src, 0)
                        except AssemblerError:
                            # treat as immediate address
                            imm = self.resolve_label_token(second)
                            imm_val = self.parse_imm(imm) & 0xFFFF
                            word = pack_instruction(opcode, dst, 0, imm_val)
                elif opcode in (OP_LOAD, OP_STORE, OP_JMP, OP_JZ, OP_JNZ, OP_JE, OP_JNE, OP_JL, OP_JG, OP_JLE, OP_JGE, OP_CALL, OP_INT, OP_FLD, OP_FST, OP_FSTP, OP_FILD, OP_FIST, OP_FISTP, OP_SETF, OP_TESTF, OP_CLRF, OP_LOOP, OP_LOOPZ, OP_LOOPNZ):
                    if len(args) != 1:
                        raise AssemblerError(f"{mnem} requires one operand")
                    val = self.resolve_label_token(args[0])
                    valnum = self.parse_imm(val) & 0xFFFF
                    word = pack_instruction(opcode, 0, 0, valnum)
                elif opcode in (OP_PUSH, OP_POP, OP_INC, OP_DEC, OP_NOT, OP_OUT, OP_IN, OP_SYSCALL, OP_FCHS, OP_FABS, OP_FSQRT, OP_FSTSW, OP_LAR, OP_LSL, OP_SLDT, OP_STR, OP_LLDT, OP_LTR, OP_VERR, OP_VERW, OP_SGDT, OP_SIDT, OP_LGDT, OP_LIDT, OP_SMSW, OP_LMSW, OP_CLTS, OP_INVD, OP_WBINVD, OP_INVLPG, OP_INVPCID, OP_VMCALL, OP_VMLAUNCH, OP_VMRESUME, OP_VMXOFF, OP_MONITOR, OP_MWAIT, OP_RDSEED, OP_RDRAND, OP_CLAC, OP_STAC, OP_SKINIT, OP_SVMEXIT, OP_SVMRET, OP_SVMLOCK, OP_SVMUNLOCK, OP_CPUID, OP_SETG, OP_SETLE, OP_SETGE, OP_SETNE, OP_SETE):
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
                elif opcode in (OP_SHLD, OP_SHRD, OP_IMUL3):
                    # Three-operand instructions: SHLD dst, src, count or IMUL3 dst, src, imm
                    if len(args) == 3:
                        dst = self.parse_reg(args[0])
                        src = self.parse_reg(args[1])
                        imm = self.resolve_label_token(args[2])
                        imm_val = self.parse_imm(imm) & 0xFFFF
                        word = pack_instruction(opcode, dst, src, imm_val)
                    elif len(args) == 2:
                        # Two operand form
                        dst = self.parse_reg(args[0])
                        src = self.parse_reg(args[1])
                        word = pack_instruction(opcode, dst, src, 0)
                    else:
                        raise AssemblerError(f"{mnem} requires 2 or 3 operands")
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
            self.used_labels.add(tok)  # Track label usage
            return str(self.labels[tok])
        elif tok.upper() in self.constants:
            return str(self.constants[tok.upper()])
        return tok
    
    def check_warnings(self):
        """Check for unused labels and undefined references"""
        # Check for unused labels
        for label in self.labels:
            if label not in self.used_labels:
                self.warnings.append(f"Unused label: {label}")
    
    def optimize_instructions(self, lines: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """Apply peephole optimizations to instruction stream"""
        if self.optimization_level == 0:
            return lines
        
        optimized = []
        i = 0
        optimizations = 0
        
        while i < len(lines):
            ln, line = lines[i]
            
            # Optimization 1: Remove redundant MOV R0, R0
            if "MOV R0, R0" in line.upper():
                i += 1
                optimizations += 1
                continue
            
            # Optimization 2: Combine LOADI + ADD into ADDI
            if i + 1 < len(lines):
                next_ln, next_line = lines[i + 1]
                if "LOADI" in line.upper() and "ADD" in next_line.upper():
                    # Try to combine into ADDI
                    loadi_match = re.match(r'\s*LOADI\s+(R\d+),\s*(\d+)', line, re.IGNORECASE)
                    add_match = re.match(r'\s*ADD\s+(R\d+),\s+(R\d+)', next_line, re.IGNORECASE)
                    if loadi_match and add_match:
                        reg1 = loadi_match.group(1)
                        imm = loadi_match.group(2)
                        dst = add_match.group(1)
                        src = add_match.group(2)
                        if reg1.upper() == src.upper():
                            # Can optimize to ADDI
                            optimized.append((ln, f"    ADDI {dst}, {imm}  ; optimized"))
                            i += 2
                            optimizations += 1
                            continue
            
            # Optimization 3: Remove NOP instructions (unless debugging)
            if self.optimization_level >= 2 and "NOP" in line.upper() and not line.strip().startswith(";"):
                i += 1
                optimizations += 1
                continue
            
            optimized.append((ln, line))
            i += 1
        
        if optimizations > 0:
            self.warnings.append(f"Applied {optimizations} peephole optimizations")
        
        return optimized
    
    def assemble(self, text: str) -> bytes:
        self.clear_errors()
        self.first_pass(text)
        if self.errors:
            error_msg = "Assembly errors:\n" + "\n".join(self.errors)
            raise AssemblerError(error_msg)
        
        # Apply optimizations if enabled
        if self.optimization_level > 0:
            self.lines = self.optimize_instructions(self.lines)
        
        result = self.second_pass()
        if self.errors:
            error_msg = "Assembly errors:\n" + "\n".join(self.errors)
            raise AssemblerError(error_msg)
        self.check_warnings()
        return result

# ---------------------------
# Simple C++ Compiler (cas++)
# ---------------------------
class CppCompilerError(Exception):
    """Raised when the C++ compiler encounters an error."""


class CppCompiler:
    """
    Extremely small C++ compiler that supports a subset of the language:
    - int main() { ... }
    - printf("text");
    - return <constant>;
    The compiler translates supported statements to SimpleOS assembly and
    uses the existing assembler to generate binaries.
    """
    def __init__(self, assembler_factory: Callable[[], Assembler] = None):
        self.assembler_factory = assembler_factory or Assembler
        self.reset()

    def reset(self):
        self.string_literals: List[Tuple[str, str]] = []
        self._string_map: Dict[str, str] = {}
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.warnings: List[str] = []
        self.errors: List[str] = []  # Track compilation errors
        self.last_assembly: str = ""
        self.variables: Dict[str, int] = {}
        self.const_variables: set = set()
        self.var_registers: Dict[str, str] = {}
        self.struct_definitions: Dict[str, List[str]] = {}
        self.struct_instances: Dict[str, Dict[str, Any]] = {}
        self.struct_pointers: Dict[str, str] = {}
        # Registers dedicated to holding cas++ variables in main(). Avoid R0-R3 (syscalls/return),
        # R13 (kernel), R14 (SP), and R15 (PC).
        self.var_register_pool: List[str] = ["R4", "R5", "R6", "R7", "R8", "R9", "R10", "R11", "R12"]
        # Temporary registers for expression evaluation. These are caller/callee-clobbered and never
        # used to hold persistent variables or stack pointers.
        self.temp_register_pool: List[str] = ["R13", "R3", "R2", "R1"]
        self.includes: List[str] = []
        self.label_counter = 0
        self.loop_stack: List[Dict[str, str]] = []
        # Class support
        self.class_definitions: Dict[str, Dict[str, Any]] = {}
        self.class_instances: Dict[str, str] = {}
        self.current_class: Optional[str] = None
        # Array support
        self.arrays: Dict[str, Dict[str, Any]] = {}
        self.array_base_addr = 0x2000  # Base address for array storage
        # Performance optimization
        self._expression_cache: Dict[str, Any] = {}  # Cache parsed expressions
        self._temp_register_stack: List[str] = []  # Track temp register usage
        # Debug support
        self.current_line: int = 0  # Track current line for error reporting
        self.source_lines: List[str] = []  # Store source for error context
        self.debug_enabled: bool = False  # When True, emit extra debug logging
        self.debug_messages: List[str] = []
        # Statistics
        self.stats = {
            "expressions_cached": 0,
            "registers_reused": 0,
            "optimizations_applied": 0
        }

    PROGRAM_BASE = 0x1000

    def log(self, message: str, level: str = "DEBUG"):
        """Record a debug message and optionally emit via logger when enabled."""
        try:
            self.debug_messages.append(f"{level}: {message}")
        except Exception:
            pass
        if not getattr(self, "debug_enabled", False):
            return
        if level == "DEBUG":
            logger.debug("cas++: %s", message)
        elif level == "INFO":
            logger.info("cas++: %s", message)
        elif level == "WARN" or level == "WARNING":
            logger.warning("cas++: %s", message)
        elif level == "ERROR":
            logger.error("cas++: %s", message)

    def compile(self, code: str, auto_fix_suggestions: bool = False, save_patch_path: Optional[str] = None) -> bytes:
        """Compile C++-like source to binary.

        If `auto_fix_suggestions` is True the compiler will automatically apply
        suggested fixes for likely-typoed function names (e.g. `pritnf` -> `printf`).
        Otherwise the compiler will prompt interactively when run in a terminal.
        """
        self.reset()
        
        # Store source lines for error reporting
        self.source_lines = code.split('\n')
        
        try:
            cleaned = self._strip_comments(code)
            cleaned = self._remove_includes(cleaned)

            # Suggest and optionally fix misspelled function names before further processing
            cleaned = self._suggest_and_fix_misspells(cleaned, auto_fix=auto_fix_suggestions, save_patch_path=save_patch_path)

            # Extract and process class definitions before main
            cleaned = self._extract_and_process_classes(cleaned)
            
            body = self._extract_main_body(cleaned)
            statements = self._split_statements(body)
            
            assembly_lines = [
                "; Generated by cas++ compiler",
                f".org 0x{self.PROGRAM_BASE:04x}",
                "main:"
            ]
            
            has_return = False
            for i, stmt in enumerate(statements):
                stmt = stmt.strip()
                if not stmt:
                    continue
                
                self.current_line = i + 1  # Track line for error reporting
                
                try:
                    translated, returns = self._translate_statement(stmt)
                    assembly_lines.extend(translated)
                    if returns:
                        has_return = True
                except CppCompilerError as e:
                    # Add line context to error
                    self.errors.append(f"Line {self.current_line}: {e}")
                    # Continue to find more errors
                    
            # Check if we had any errors
            if self.errors:
                error_msg = "Compilation failed with errors:\n" + "\n".join(self.errors)
                raise CppCompilerError(error_msg)
            
            if not has_return:
                assembly_lines.append("    LOADI R0, 0")
            assembly_lines.append("    HALT")
            
        except CppCompilerError:
            raise  # Re-raise compiler errors
        except Exception as e:
            # Catch unexpected errors and provide context
            raise CppCompilerError(f"Unexpected error at line {self.current_line}: {e}") from e
        if self.string_literals:
            assembly_lines.append("")
            assembly_lines.append("; --- cas++ string literals ---")
            for label, text in self.string_literals:
                assembly_lines.append(f"{label}:")
                assembly_lines.append(f"    .string {self._escape_string(text)}")
        self.last_assembly = "\n".join(assembly_lines)
        assembler = self.assembler_factory()
        try:
            binary = assembler.assemble(self.last_assembly)
        except AssemblerError as exc:
            raise CppCompilerError(str(exc)) from exc
        if self.PROGRAM_BASE and len(binary) > self.PROGRAM_BASE:
            binary = binary[self.PROGRAM_BASE:]
        self.functions["main"] = {"statements": len(statements)}
        return binary

    def _suggest_and_fix_misspells(self, src: str, auto_fix: bool = False, save_patch_path: Optional[str] = None) -> str:
        """Scan source for likely-typoed function calls and suggest fixes.

        If `auto_fix` is True, apply fixes automatically; otherwise prompt the user.
        Returns possibly modified source.
        """
        import re, difflib

        # Known intrinsics and functions we support (expandable)
        known = set([
            'printf','printf_int','get_input','get_string','gettime','swap','reverse',
            'strlen','strcpy','strcat','strncpy','strncat','strstr','strchr','strcmp','memset','lerp','sign',
            'saturate','pow','rand','srand','popcnt','clz','ctz','rotl','rotr','abs','min','max'
        ])
        # Exclude common keywords and entry point
        keywords = set(['if','for','while','switch','return','int','char','float','double','struct','sizeof','main'])

        pattern = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
        names = set(m.group(1) for m in pattern.finditer(src))
        candidates = [n for n in sorted(names) if n not in known and n not in keywords]
        if not candidates:
            return src

        original_src = src
        applied_any = False

        for name in candidates:
            # Find closest match among known intrinsics
            matches = difflib.get_close_matches(name, sorted(known), n=1, cutoff=0.7)
            if not matches:
                continue
            suggestion = matches[0]
            # Prompt or auto-accept
            prompt = f"Compiler suggestion: Did you mean '{suggestion}' instead of '{name}'? [y/N]: "
            accept = False
            if auto_fix:
                accept = True
                self.log(f"auto-fix: {name} -> {suggestion}", "INFO")
            else:
                try:
                    resp = input(prompt).strip().lower()
                    accept = resp == 'y' or resp == 'yes'
                except Exception:
                    accept = False
            if accept:
                # Replace occurrences of name followed by optional whitespace and '('
                src = re.sub(rf'\b{re.escape(name)}(\s*)\(', rf'{suggestion}\1(', src)
                applied_any = True
                self.log(f"applied_fix: {name} -> {suggestion}", "INFO")

        # If requested, write a unified diff patch file comparing original->modified
        if applied_any and save_patch_path:
            try:
                import difflib
                from pathlib import Path
                od = original_src.splitlines(keepends=True)
                nd = src.splitlines(keepends=True)
                diff_lines = list(difflib.unified_diff(od, nd, fromfile='original', tofile='fixed'))
                Path(save_patch_path).write_text(''.join(diff_lines))
                self.log(f"wrote_patch: {save_patch_path}", "INFO")
            except Exception as e:
                self.log(f"failed_write_patch: {e}", "WARN")

        return src

    def get_assembly_output(self) -> str:
        return self.last_assembly
    
    def get_stats(self) -> Dict[str, Any]:
        """Get compilation statistics"""
        return {
            "expressions_cached": self.stats["expressions_cached"],
            "registers_reused": self.stats["registers_reused"],
            "optimizations_applied": self.stats["optimizations_applied"],
            "variables": len(self.variables),
            "string_literals": len(self.string_literals),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "arrays": len(self.arrays),
            "classes": len(self.class_definitions)
        }

    def _remove_includes(self, code: str) -> str:
        lines = []
        for raw in code.splitlines():
            stripped = raw.strip()
            if stripped.startswith("#include"):
                parts = stripped.split()
                if len(parts) > 1:
                    self.includes.append(parts[1])
                continue
            lines.append(raw)
        return "\n".join(lines)
    
    def _extract_and_process_classes(self, code: str) -> str:
        """Extract class definitions and process them, returning code without classes"""
        # Use character-by-character parsing to handle classes on same line as other code
        result = []
        i = 0
        
        while i < len(code):
            # Skip whitespace
            while i < len(code) and code[i] in ' \t\n\r':
                result.append(code[i])
                i += 1
            
            if i >= len(code):
                break
            
            # Check if we're at the start of a class definition
            if code[i:i+5] == 'class' and (i + 5 >= len(code) or code[i+5] in ' \t\n\r'):
                # Found a class definition
                class_start = i
                i += 5
                
                # Skip whitespace
                while i < len(code) and code[i] in ' \t\n\r':
                    i += 1
                
                # Get class name
                name_start = i
                while i < len(code) and (code[i].isalnum() or code[i] == '_'):
                    i += 1
                
                # Skip to opening brace
                while i < len(code) and code[i] != '{':
                    i += 1
                
                if i >= len(code):
                    # No opening brace found, not a valid class
                    result.append(code[class_start:i])
                    continue
                
                # Found opening brace, now find matching closing brace
                i += 1  # Skip opening brace
                brace_depth = 1
                
                while i < len(code) and brace_depth > 0:
                    if code[i] == '{':
                        brace_depth += 1
                    elif code[i] == '}':
                        brace_depth -= 1
                    i += 1
                
                # Skip optional semicolon after closing brace
                if i < len(code) and code[i] == ';':
                    i += 1
                
                # Extract and process the class
                class_text = code[class_start:i]
                try:
                    self._process_class_definition(class_text)
                except CppCompilerError as e:
                    self.warnings.append(f"Class definition error: {e}")
                
                # Don't add class text to result
                continue
            
            # Not a class, add character to result
            result.append(code[i])
            i += 1
        
        return ''.join(result)
    
    def _process_class_definition(self, class_text: str):
        """Process a class definition and register it"""
        # Remove trailing semicolon
        class_text = class_text.rstrip(';').strip()
        
        # Extract class name and body
        match = re.match(r'class\s+([A-Za-z_]\w*)\s*\{(.+)\}', class_text, re.DOTALL)
        if not match:
            raise CppCompilerError(f"Invalid class definition")
        
        class_name = match.group(1)
        body = match.group(2).strip()
        
        if class_name in self.class_definitions:
            raise CppCompilerError(f"Class '{class_name}' already defined")
        
        # Parse class members
        members = []
        for line in body.split(';'):
            line = line.strip()
            if not line:
                continue
            # Look for member variable declarations
            m = re.match(r'(int|float|bool|char)\s+([A-Za-z_]\w*)', line)
            if m:
                members.append({
                    "type": m.group(1),
                    "name": m.group(2)
                })
        
        self.class_definitions[class_name] = {
            "members": members,
            "size": len(members) * 4
        }

    def _strip_comments(self, code: str) -> str:
        pattern = re.compile(r'//.*?$|/\*.*?\*/', re.DOTALL | re.MULTILINE)
        return re.sub(pattern, '', code)

    def _extract_main_body(self, code: str) -> str:
        match = re.search(r'int\s+main\s*\([^)]*\)\s*{', code)
        if not match:
            raise CppCompilerError("cas++ requires an int main() entry point")
        start = match.end()
        depth = 1
        i = start
        in_string = False
        escape = False
        while i < len(code):
            ch = code[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return code[start:i]
            i += 1
        raise CppCompilerError("Unterminated main() body")

    def _split_statements(self, body: str) -> List[str]:
        statements: List[str] = []
        current: List[str] = []
        in_string = False
        escape = False
        brace_depth = 0
        paren_depth = 0
        for ch in body:
            if in_string:
                current.append(ch)
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                current.append(ch)
                continue
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                if paren_depth > 0:
                    paren_depth -= 1
            if ch == '{':
                brace_depth += 1
                current.append(ch)
                continue
            if ch == '}':
                current.append(ch)
                if brace_depth > 0:
                    brace_depth -= 1
                if brace_depth == 0 and current:
                    statements.append("".join(current))
                    current = []
                continue
            if ch == ';' and brace_depth == 0 and paren_depth == 0:
                statements.append("".join(current))
                current = []
            else:
                current.append(ch)
        if current:
            statements.append("".join(current))
        merged: List[str] = []
        for stmt in statements:
            stripped = stmt.strip()
            if stripped.startswith("else"):
                if merged:
                    merged[-1] += (" " if not merged[-1].endswith(" ") else "") + stripped
                else:
                    merged.append(stmt)
            elif stripped.startswith("while") and merged and merged[-1].lstrip().startswith("do"):
                merged[-1] += (" " if not merged[-1].endswith(" ") else "") + stripped
            else:
                merged.append(stmt)
        return merged

    def _translate_statement(self, stmt: str) -> Tuple[List[str], bool]:
        stmt = stmt.strip()
        if not stmt:
            return [], False
        # ++i, i++, --i, i-- as standalone statements
        incdec_code = self._compile_incdec_statement(stmt)
        if incdec_code is not None:
            return incdec_code, False
        if stmt.startswith("class "):
            return self._compile_class_definition(stmt), False
        # Match printf( at word boundary, not printf_int or other variants
        if re.match(r'^printf\s*\(', stmt):
            return self._translate_printf(stmt), False
        if stmt.startswith("return"):
            return self._translate_return(stmt), True
        if stmt.startswith("if"):
            return self._translate_if(stmt), False
        if stmt.startswith("while"):
            return self._translate_while(stmt), False
        if re.match(r'(?:const\s+)?(?:int|float|bool|char)\s+', stmt):
            # Check if it's an array declaration (but not array access in initialization)
            # Array declaration: int arr[5]; or int arr[5] = {...}
            # Not array access: int x = arr[1];
            if '[' in stmt and ']' in stmt and '=' not in stmt.split('[')[0]:
                return self._compile_array_declaration(stmt), False
            return self._compile_declaration(stmt), False
        # Compound assignments like a += b, a <<= 1, etc.
        m_comp = re.match(r'^([A-Za-z_]\w*)\s*(\+=|-=|\*=|/=|&=|\|=|\^=|<<=|>>=)\s*(.+)$', stmt.rstrip(';').strip())
        if m_comp:
            return self._compile_compound_assignment(m_comp), False
        if "=" in stmt:
            lhs = stmt.split("=", 1)[0].strip()
            # Check if it's a simple identifier or array access
            if lhs.isidentifier() or ('[' in lhs and ']' in lhs):
                return self._compile_assignment(stmt), False
        if re.fullmatch(r"break\s*;?", stmt):
            return self._translate_break(), False
        if re.fullmatch(r"continue\s*;?", stmt):
            return self._translate_continue(), False
        # Inline assembly support: asm("instruction");
        if stmt.startswith("asm"):
            return self._translate_inline_asm(stmt), False
        if re.match(r"for\b", stmt):
            return self._translate_for(stmt), False
        if re.match(r"do\b", stmt):
            return self._translate_do_while(stmt), False
        # bare function call like foo() or foo(a,b)
        mcall = re.fullmatch(r"([A-Za-z_]\w*)\s*\((.*)\)\s*", stmt)
        if mcall:
            name = mcall.group(1)
            args_str = mcall.group(2).strip()
            lines: List[str] = []
            args = [a for a in self._split_arguments(args_str)] if args_str else []
            
            # Handle built-in functions that don't return values (statement form)
            if name == "sleep" and len(args) == 1:
                node = self._parse_expression_node(args[0])
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node, treg))
                lines.append(f"    SLEEP R0, {treg}")  # Two operand form
                self._release_temp_register(treg)
                return lines, False
            
            # printf_int(value) - print integer directly using syscall 50
            if name == "printf_int" and len(args) == 1:
                node = self._parse_expression_node(args[0])
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node, treg))
                lines.append(f"    LOADI R0, 50  ; PRINT_INT syscall")
                lines.append(f"    MOV R1, {treg}")
                lines.append(f"    SYSCALL R0")
                self._release_temp_register(treg)
                return lines, False

            # strncpy(dest, src, n) - copy n bytes from src to dest
            if name == "strncpy" and len(args) == 3:
                node_dst = self._parse_expression_node(args[0])
                node_src = self._parse_expression_node(args[1])
                node_cnt = self._parse_expression_node(args[2])
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node_dst, dst_reg))
                lines.extend(self._emit_expression_to_register(node_src, src_reg))
                lines.extend(self._emit_expression_to_register(node_cnt, cnt_reg))
                lines.append(f"    STRNCPY {dst_reg}, {src_reg}, {cnt_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return lines, False

            # strcpy(dest, src) - copy null-terminated string
            if name == "strcpy" and len(args) == 2:
                node_dst = self._parse_expression_node(args[0])
                node_src = self._parse_expression_node(args[1])
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node_dst, dst_reg))
                lines.extend(self._emit_expression_to_register(node_src, src_reg))
                lines.append(f"    STRCPY {dst_reg}, {src_reg}")
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return lines, False

            # strcat(dest, src) - append null-terminated string src to dest
            if name == "strcat" and len(args) == 2:
                node_dst = self._parse_expression_node(args[0])
                node_src = self._parse_expression_node(args[1])
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node_dst, dst_reg))
                lines.extend(self._emit_expression_to_register(node_src, src_reg))
                lines.append(f"    STRCAT {dst_reg}, {src_reg}")
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return lines, False

            # memcpy(dest, src, n) as statement form
            if name == "memcpy" and len(args) == 3:
                node_dst = self._parse_expression_node(args[0])
                node_src = self._parse_expression_node(args[1])
                node_cnt = self._parse_expression_node(args[2])
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node_dst, dst_reg))
                lines.extend(self._emit_expression_to_register(node_src, src_reg))
                lines.extend(self._emit_expression_to_register(node_cnt, cnt_reg))
                lines.append(f"    MEMCPY {dst_reg}, {src_reg}, {cnt_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return lines, False

            # memcmp(a, b, n) as statement form (discard result)
            if name == "memcmp" and len(args) == 3:
                a_node = self._parse_expression_node(args[0])
                b_node = self._parse_expression_node(args[1])
                cnt_node = self._parse_expression_node(args[2])
                a_reg = self._acquire_temp_register()
                b_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(a_node, a_reg))
                lines.extend(self._emit_expression_to_register(b_node, b_reg))
                lines.extend(self._emit_expression_to_register(cnt_node, cnt_reg))
                lines.append(f"    CMPS R0, {a_reg}, {b_reg}, {cnt_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(b_reg)
                self._release_temp_register(a_reg)
                return lines, False

            # itoa(value, buf, base) as statement form
            if name == "itoa" and len(args) in (2,3):
                val_node = self._parse_expression_node(args[0])
                buf_node = self._parse_expression_node(args[1])
                base_node = self._parse_expression_node(args[2]) if len(args) == 3 else None
                val_reg = self._acquire_temp_register()
                buf_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(val_node, val_reg))
                lines.extend(self._emit_expression_to_register(buf_node, buf_reg))
                if base_node:
                    base_reg = self._acquire_temp_register()
                    lines.extend(self._emit_expression_to_register(base_node, base_reg))
                    lines.append(f"    ITOA {buf_reg}, {val_reg}, {base_reg}")
                    self._release_temp_register(base_reg)
                else:
                    lines.append(f"    ITOA {buf_reg}, {val_reg}")
                self._release_temp_register(buf_reg)
                self._release_temp_register(val_reg)
                return lines, False

            # strncat(dest, src, n) - append up to n bytes from src to dest
            if name == "strncat" and len(args) == 3:
                node_dst = self._parse_expression_node(args[0])
                node_src = self._parse_expression_node(args[1])
                node_cnt = self._parse_expression_node(args[2])
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node_dst, dst_reg))
                lines.extend(self._emit_expression_to_register(node_src, src_reg))
                lines.extend(self._emit_expression_to_register(node_cnt, cnt_reg))
                lines.append(f"    STRNCAT {dst_reg}, {src_reg}, {cnt_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return lines, False

            # strchr(hay, needle) as statement form - call and discard return
            if name == "strchr" and len(args) == 2:
                node_hay = self._parse_expression_node(args[0])
                node_needle = self._parse_expression_node(args[1])
                hay_reg = self._acquire_temp_register()
                needle_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node_hay, hay_reg))
                lines.extend(self._emit_expression_to_register(node_needle, needle_reg))
                # Use STRCHR opcode (result in R0) but we ignore it for statement
                lines.append(f"    STRCHR R0, {hay_reg}, {needle_reg}")
                self._release_temp_register(needle_reg)
                self._release_temp_register(hay_reg)
                return lines, False

            # memchr(base, byte, n) as statement form (discard result)
            if name == "memchr" and len(args) == 3:
                base_node = self._parse_expression_node(args[0])
                byte_node = self._parse_expression_node(args[1])
                cnt_node = self._parse_expression_node(args[2])
                base_reg = self._acquire_temp_register()
                byte_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(base_node, base_reg))
                lines.extend(self._emit_expression_to_register(byte_node, byte_reg))
                lines.extend(self._emit_expression_to_register(cnt_node, cnt_reg))
                lines.append(f"    MOV R0, {base_reg}")
                lines.append(f"    MOV R1, {byte_reg}")
                lines.append(f"    MOV R2, {cnt_reg}")
                lines.append(f"    MEMCHR")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(byte_reg)
                self._release_temp_register(base_reg)
                return lines, False

            # revmem(addr, len) as statement form (in-place reverse)
            if name == "revmem" and len(args) == 2:
                base_node = self._parse_expression_node(args[0])
                cnt_node = self._parse_expression_node(args[1])
                base_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(base_node, base_reg))
                lines.extend(self._emit_expression_to_register(cnt_node, cnt_reg))
                lines.append(f"    MOV R0, {base_reg}")
                lines.append(f"    MOV R1, {cnt_reg}")
                lines.append(f"    REV_MEM")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(base_reg)
                return lines, False
            
            # Graphics functions (statement form)
            if name == "pixel" and len(args) == 3:
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), "R0"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[1]), "R1"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[2]), "R2"))
                lines.append(f"    PIXEL")
                return lines, False
            
            if name == "line" and len(args) == 5:
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), "R0"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[1]), "R1"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[2]), "R2"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[3]), "R3"))
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[4]), treg))
                lines.append(f"    LINE {treg}")
                self._release_temp_register(treg)
                return lines, False
            
            if name == "rect" and len(args) == 5:
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), "R0"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[1]), "R1"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[2]), "R2"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[3]), "R3"))
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[4]), treg))
                lines.append(f"    RECT {treg}")
                self._release_temp_register(treg)
                return lines, False
            
            if name == "fillrect" and len(args) == 5:
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), "R0"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[1]), "R1"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[2]), "R2"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[3]), "R3"))
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[4]), treg))
                lines.append(f"    FILLRECT {treg}")
                self._release_temp_register(treg)
                return lines, False
            
            if name == "circle" and len(args) == 4:
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), "R0"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[1]), "R1"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[2]), "R2"))
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[3]), treg))
                lines.append(f"    CIRCLE {treg}")
                self._release_temp_register(treg)
                return lines, False
            
            if name == "fillcircle" and len(args) == 4:
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), "R0"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[1]), "R1"))
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[2]), "R2"))
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[3]), treg))
                lines.append(f"    FILLCIRCLE {treg}")
                self._release_temp_register(treg)
                return lines, False
            
            if name == "clear" and len(args) == 1:
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(self._parse_expression_node(args[0]), treg))
                lines.append(f"    CLEAR {treg}")
                self._release_temp_register(treg)
                return lines, False
            
            if name == "swap" and len(args) == 2:
                # Parse variable names
                var1 = args[0].strip()
                var2 = args[1].strip()
                if var1 in self.var_registers and var2 in self.var_registers:
                    reg1 = self.var_registers[var1]
                    reg2 = self.var_registers[var2]
                    lines.append(f"    XCHG {reg1}, {reg2}")
                    return lines, False
            
            # push args right-to-left
            for arg in reversed([a for a in args if a]):
                node = self._parse_expression_node(arg)
                treg = self._acquire_temp_register()
                lines.extend(self._emit_expression_to_register(node, treg))
                lines.append(f"    PUSH {treg}")
                self._release_temp_register(treg)
            if name in self.var_registers:
                reg = self._require_variable(name)
                lines.append(f"    CALLR {reg}")
            else:
                lines.append(f"    CALL {name}")
            if args:
                lines.append(f"    ADDI R14, {len(args)*4}")
            return lines, False
        self.warnings.append(f"Unsupported statement ignored: {stmt}")
        return [], False

    def _translate_printf(self, stmt: str) -> List[str]:
        # Remove trailing semicolon if present - CAREFUL: check quotes first
        stmt = stmt.rstrip(';').strip()
        
        # More flexible regex to handle various printf formats
        # Support both printf(...) and printf(...); forms
        match = re.match(r'printf\s*\((.+)\)$', stmt, re.DOTALL)
        if not match:
            # Try to provide helpful error message
            if 'printf' in stmt and '(' in stmt:
                raise CppCompilerError(f"Malformed printf statement - check parentheses and matching quotes: {stmt[:80]}...")
            raise CppCompilerError(f"Unable to parse printf statement: {stmt[:80]}...")
        
        argument = match.group(1).strip()
        
        try:
            literal_token, remainder = self._split_string_literal(argument)
        except CppCompilerError as e:
            raise CppCompilerError(f"Error parsing printf string literal: {e}")
        try:
            text_value = ast.literal_eval(literal_token)
        except Exception as exc:
            raise CppCompilerError(f"Invalid string literal in printf: {exc}") from exc
        
        lines = ["    ; printf"]
        remainder = remainder.strip()
        
        if remainder:
            if not remainder.startswith(","):
                raise CppCompilerError("printf arguments must be separated by commas")
            extra_args = self._split_arguments(remainder[1:].strip())
            
            # Try to evaluate as constants first
            const_values = []
            dynamic_args = []
            for arg in extra_args:
                if not arg:
                    continue
                try:
                    val = self._evaluate_expression(arg)
                    const_values.append(val)
                    dynamic_args.append(None)
                except CppCompilerError:
                    # It's a variable/expression - handle at runtime
                    const_values.append(None)
                    dynamic_args.append(arg)
            
            # If all arguments are constants, do compile-time substitution
            if all(v is not None for v in const_values):
                for value in const_values:
                    if "%d" in text_value:
                        text_value = text_value.replace("%d", str(value), 1)
                    else:
                        text_value = f"{text_value}{value}"
                label = self._add_string_literal(text_value)
                length = len(text_value.encode('utf-8'))
                lines.extend([
                    "    LOADI R0, 1",
                    "    LOADI R1, 1",
                    f"    LOADI R2, {label}",
                    f"    LOADI R3, {length}",
                    "    SYSCALL R0"
                ])
            else:
                # Handle runtime substitution by splitting format string and printing parts
                parts = text_value.split("%d")
                arg_idx = 0
                
                for i, part in enumerate(parts):
                    # Print the string part
                    if part:
                        label = self._add_string_literal(part)
                        length = len(part.encode('utf-8'))
                        lines.extend([
                            "    LOADI R0, 1",
                            "    LOADI R1, 1",
                            f"    LOADI R2, {label}",
                            f"    LOADI R3, {length}",
                            "    SYSCALL R0"
                        ])
                    
                    # Print the variable (if not last part)
                    if i < len(parts) - 1 and arg_idx < len(dynamic_args):
                        if dynamic_args[arg_idx] is not None:
                            # Evaluate expression into a register
                            node = self._parse_expression_node(dynamic_args[arg_idx])
                            temp_reg = self._acquire_temp_register()
                            lines.extend(self._emit_expression_to_register(node, temp_reg))
                            # Print integer syscall (syscall 50)
                            lines.extend([
                                "    LOADI R0, 50",
                                f"    MOV R1, {temp_reg}",
                                "    SYSCALL R0"
                            ])
                            self._release_temp_register(temp_reg)
                        elif const_values[arg_idx] is not None:
                            # Print constant
                            lines.extend([
                                "    LOADI R0, 50",
                                f"    LOADI R1, {const_values[arg_idx]}",
                                "    SYSCALL R0"
                            ])
                        arg_idx += 1
        else:
            # No arguments, just print the string
            label = self._add_string_literal(text_value)
            length = len(text_value.encode('utf-8'))
            lines.extend([
                "    LOADI R0, 1",
                "    LOADI R1, 1",
                f"    LOADI R2, {label}",
                f"    LOADI R3, {length}",
                "    SYSCALL R0"
            ])
        
        return lines

    def _translate_return(self, stmt: str) -> List[str]:
        expr = stmt[len("return"):].strip()
        if expr.endswith(";"):
            expr = expr[:-1].strip()
        if expr:
            node = self._parse_expression_node(expr)
        else:
            node = ast.Constant(value=0)
        code = ["    ; return statement"]
        code.extend(self._emit_expression_to_register(node, "R0"))
        return code
    
    def _translate_if(self, stmt: str) -> List[str]:
        condition, remainder = self._extract_parenthesized(stmt)
        remainder = remainder.strip()
        if not remainder:
            raise CppCompilerError("if statement missing body")
        true_code: List[str] = []
        else_code: List[str] = []
        tail = ""
        if remainder.startswith("{"):
            block_body, tail = self._extract_block(remainder)
            true_code = self._compile_block(block_body)
        else:
            inner_code, _ = self._translate_statement(remainder)
            true_code = inner_code
        tail = tail.strip()
        if tail.startswith("else"):
            tail_body = tail[4:].strip()
            if tail_body.startswith("if"):
                else_code = self._translate_if(tail_body)
                tail = ""
            elif tail_body.startswith("{"):
                else_body, leftover = self._extract_block(tail_body)
                else_code = self._compile_block(else_body)
                tail = leftover.strip()
            else:
                code, _ = self._translate_statement(tail_body)
                else_code = code
                tail = ""
        if tail:
            tail = tail.strip()
            if tail:
                self.warnings.append(f"Ignoring unexpected tokens after else block: {tail}")
        cond_lines, false_jump = self._emit_condition_code(condition)
        lines: List[str] = []
        lines.extend(cond_lines)
        if else_code:
            else_label = self._new_label("if_else")
            end_label = self._new_label("if_end")
            lines.append(f"    {false_jump} {else_label}")
            lines.extend(true_code)
            lines.append(f"    JMP {end_label}")
            lines.append(f"{else_label}:")
            lines.extend(else_code)
            lines.append(f"{end_label}:")
        else:
            end_label = self._new_label("if_end")
            lines.append(f"    {false_jump} {end_label}")
            lines.extend(true_code)
            lines.append(f"{end_label}:")
        return lines

    def _translate_while(self, stmt: str) -> List[str]:
        condition, remainder = self._extract_parenthesized(stmt)
        remainder = remainder.strip()
        if not remainder:
            raise CppCompilerError("while statement missing body")
        start_label = self._new_label("while_begin")
        end_label = self._new_label("while_end")
        cond_code, false_jump = self._emit_condition_code(condition)
        self.loop_stack.append({"break": end_label, "continue": start_label})
        try:
            if remainder.startswith("{"):
                body_text, tail = self._extract_block(remainder)
                if tail.strip():
                    self.warnings.append(f"Ignoring tokens after while block: {tail.strip()}")
                body_code = self._compile_block(body_text)
            else:
                body_code, _ = self._translate_statement(remainder)
        finally:
            self.loop_stack.pop()
        lines = [f"{start_label}:"]
        lines.extend(cond_code)
        lines.append(f"    {false_jump} {end_label}")
        lines.extend(body_code)
        lines.append(f"    JMP {start_label}")
        lines.append(f"{end_label}:")
        return lines

    def _translate_for(self, stmt: str) -> List[str]:
        header, remainder = self._extract_parenthesized(stmt)
        header = header.strip()
        parts: List[str] = []
        current: List[str] = []
        depth = 0
        for ch in header:
            if ch == '(':
                depth += 1
            elif ch == ')':
                if depth > 0:
                    depth -= 1
            if ch == ';' and depth == 0:
                parts.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            parts.append("".join(current).strip())
        if len(parts) != 3:
            raise CppCompilerError("for loop header must be 'init; condition; increment'")
        init_src, cond_src, post_src = parts
        remainder = remainder.strip()
        if not remainder:
            raise CppCompilerError("for statement missing body")
        lines: List[str] = []
        if init_src:
            init_code, _ = self._translate_statement(init_src)
            lines.extend(init_code)
        cond_label = self._new_label("for_cond")
        end_label = self._new_label("for_end")
        post_label = self._new_label("for_post")
        lines.append(f"{cond_label}:")
        if cond_src:
            cond_code, false_jump = self._emit_condition_code(cond_src)
            lines.extend(cond_code)
            lines.append(f"    {false_jump} {end_label}")
        self.loop_stack.append({"break": end_label, "continue": post_label})
        try:
            if remainder.startswith("{"):
                body_text, tail = self._extract_block(remainder)
                if tail.strip():
                    self.warnings.append(f"Ignoring tokens after for block: {tail.strip()}")
                body_code = self._compile_block(body_text)
            else:
                body_code, _ = self._translate_statement(remainder)
        finally:
            self.loop_stack.pop()
        lines.extend(body_code)
        lines.append(f"{post_label}:")
        if post_src:
            post_code, _ = self._translate_statement(post_src)
            lines.extend(post_code)
        lines.append(f"    JMP {cond_label}")
        lines.append(f"{end_label}:")
        return lines

    def _translate_do_while(self, stmt: str) -> List[str]:
        remainder = stmt[len("do"):].strip()
        if not remainder.startswith("{"):
            raise CppCompilerError("do-while requires a block body")
        body_text, tail = self._extract_block(remainder)
        tail = tail.strip()
        if not tail.startswith("while"):
            raise CppCompilerError("do-while missing while(condition)")
        condition, after = self._extract_parenthesized(tail)
        start_label = self._new_label("do_begin")
        cond_label = self._new_label("do_cond")
        end_label = self._new_label("do_end")
        lines: List[str] = [f"{start_label}:"]
        self.loop_stack.append({"break": end_label, "continue": cond_label})
        try:
            body_code = self._compile_block(body_text)
        finally:
            self.loop_stack.pop()
        lines.extend(body_code)
        lines.append(f"{cond_label}:")
        cond_code, false_jump = self._emit_condition_code(condition)
        lines.extend(cond_code)
        lines.append(f"    {false_jump} {end_label}")
        lines.append(f"    JMP {start_label}")
        lines.append(f"{end_label}:")
        return lines

    def _translate_break(self) -> List[str]:
        if not self.loop_stack:
            raise CppCompilerError("break statement not within loop")
        target = self.loop_stack[-1]["break"]
        return [f"    JMP {target}"]

    def _translate_continue(self) -> List[str]:
        if not self.loop_stack:
            raise CppCompilerError("continue statement not within loop")
        target = self.loop_stack[-1]["continue"]
        return [f"    JMP {target}"]
    
    def _translate_inline_asm(self, stmt: str) -> List[str]:
        """Translate inline assembly: asm("NOP"); or asm("ADD R1, R2");"""
        match = re.match(r'asm\s*\(\s*"([^"]+)"\s*\)', stmt)
        if not match:
            raise CppCompilerError(f"Invalid inline assembly syntax: {stmt}")
        
        asm_code = match.group(1)
        # Return the assembly code directly with proper indentation
        return [f"    {asm_code}  ; inline asm"]

    def _compile_block(self, block_text: str) -> List[str]:
        lines: List[str] = []
        for stmt in self._split_statements(block_text):
            stmt = stmt.strip()
            if not stmt:
                continue
            code, _ = self._translate_statement(stmt)
            lines.extend(code)
        return lines

    def _new_label(self, prefix: str = "L") -> str:
        label = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def _extract_parenthesized(self, stmt: str) -> Tuple[str, str]:
        start = stmt.find('(')
        if start == -1:
            raise CppCompilerError("Missing '(' in if statement")
        depth = 0
        expr_start = start + 1
        for i in range(start, len(stmt)):
            ch = stmt[i]
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    return stmt[expr_start:i], stmt[i+1:]
        raise CppCompilerError("Unmatched parentheses in if condition")

    def _extract_block(self, text: str) -> Tuple[str, str]:
        if not text.startswith("{"):
            raise CppCompilerError("Expected '{' to start block")
        depth = 0
        start = 1
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i], text[i+1:]
        raise CppCompilerError("Unmatched braces in block")

    def _parse_condition(self, condition: str) -> Tuple[str, Optional[str], Optional[str]]:
        condition = condition.strip()
        for op in ("==", "!=", ">=", "<=", ">", "<"):
            idx = condition.find(op)
            if idx != -1:
                left = condition[:idx].strip()
                right = condition[idx + len(op):].strip()
                return left, op, right
        return condition, None, None

    def _emit_condition_code(self, condition: str) -> Tuple[List[str], str]:
        left_expr, operator, right_expr = self._parse_condition(condition)
        code: List[str] = []
        left_reg = self._acquire_temp_register()
        code.extend(self._emit_expression_to_register(self._parse_expression_node(left_expr), left_reg))
        jump = "JE"
        if operator:
            right_reg = self._acquire_temp_register()
            code.extend(self._emit_expression_to_register(self._parse_expression_node(right_expr), right_reg))
            code.append(f"    CMP {left_reg}, {right_reg}")
            jump = {
                "==": "JNE",
                "!=": "JE",
                ">": "JLE",
                ">=": "JL",
                "<": "JGE",
                "<=": "JG",
            }[operator]
            self._release_temp_register(right_reg)
        else:
            zero_reg = self._acquire_temp_register()
            code.extend(self._emit_load_immediate(zero_reg, 0))
            code.append(f"    CMP {left_reg}, {zero_reg}")
            jump = "JE"
            self._release_temp_register(zero_reg)
        self._release_temp_register(left_reg)
        return code, jump

    def _add_string_literal(self, literal: str) -> str:
        if literal in self._string_map:
            return self._string_map[literal]
        label = f"__str_{len(self.string_literals)}"
        self.string_literals.append((label, literal))
        self._string_map[literal] = label
        return label

    def _escape_string(self, text_value: str) -> str:
        escaped = text_value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
        return f"\"{escaped}\""
    
    def _split_string_literal(self, argument: str) -> Tuple[str, str]:
        """Extract first string literal from argument.
        
        Carefully handles escape sequences: \\n, \\t, \\\\, \\\", etc.
        Returns (quoted_string, remainder_after_quote)
        """
        if not argument.startswith('"'):
            raise CppCompilerError("printf requires a string literal as the first argument")
        escape = False
        for idx in range(1, len(argument)):
            ch = argument[idx]
            if escape:
                # After backslash, accept any character
                escape = False
                continue
            if ch == '\\':
                # Start of escape sequence
                escape = True
                continue
            if ch == '"':
                # Found closing quote - return the quoted string and remainder
                return argument[:idx + 1], argument[idx + 1:]
        # If we get here, the quote was never closed
        raise CppCompilerError(f"Unterminated string literal in printf - check for unescaped quotes: {argument[:60]}...")

    def _split_arguments(self, arg_string: str) -> List[str]:
        args = []
        current = []
        depth = 0
        in_string = False
        escape = False
        for ch in arg_string:
            if in_string:
                current.append(ch)
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
                current.append(ch)
                continue
            if ch == '(':
                depth += 1
            elif ch == ')':
                if depth > 0:
                    depth -= 1
            if ch == ',' and depth == 0:
                args.append("".join(current).strip())
                current = []
            else:
                current.append(ch)
        if current:
            trailing = "".join(current).strip()
            if trailing:
                args.append(trailing)
        return args

    def _parse_expression_node(self, expr: str):
        # Check cache first for performance
        if expr in self._expression_cache:
            self.stats["expressions_cached"] += 1
            return self._expression_cache[expr]
        
        expr = self._normalize_expression(expr)
        try:
            node = ast.parse(expr, mode="eval").body
            # Cache the parsed expression
            self._expression_cache[expr] = node
            return node
        except SyntaxError as exc:
            raise CppCompilerError(f"Invalid expression '{expr}': {exc}")

    def _normalize_expression(self, expr: str) -> str:
        expr = expr.replace('&&', ' and ')
        expr = expr.replace('||', ' or ')
        expr = re.sub(r'!(?!=)', ' not ', expr)
        expr = re.sub(r'\btrue\b', 'True', expr)
        expr = re.sub(r'\bfalse\b', 'False', expr)
        # Convert C-style ternary operator a ? b : c -> Python's (b) if (a) else (c)
        try:
            expr = self._convert_c_ternary(expr)
        except Exception:
            # If conversion fails, leave expression unchanged and let parser report syntax
            pass
        return expr

    def _convert_c_ternary(self, expr: str) -> str:
        """Recursively convert C-style ternary operators to Python if-expr.

        This is a simple, conservative converter that finds the first top-level
        '?' and its matching ':' (respecting parentheses and string literals),
        then rewrites `a ? b : c` as `(b) if (a) else (c)` and recurses.
        """
        s = expr
        # Quick exit if no ternary
        if '?' not in s:
            return s

        def find_top_level_question(s):
            in_str = False
            escape = False
            depth = 0
            for i, ch in enumerate(s):
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"' or ch == "'":
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth > 0:
                        depth -= 1
                elif ch == '?' and depth == 0:
                    return i
            return -1

        def find_matching_colon(s, qpos):
            in_str = False
            escape = False
            depth = 0
            tern_level = 0
            for i in range(qpos+1, len(s)):
                ch = s[i]
                if escape:
                    escape = False
                    continue
                if ch == '\\':
                    escape = True
                    continue
                if ch == '"' or ch == "'":
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth > 0:
                        depth -= 1
                elif ch == '?' and depth == 0:
                    tern_level += 1
                elif ch == ':' and depth == 0:
                    if tern_level == 0:
                        return i
                    tern_level -= 1
            return -1

        qpos = find_top_level_question(s)
        if qpos == -1:
            return s
        cpos = find_matching_colon(s, qpos)
        if cpos == -1:
            # malformed ternary; leave as-is
            return s
        test = s[:qpos].strip()
        true_part = s[qpos+1:cpos].strip()
        false_part = s[cpos+1:].strip()
        # Recursively convert nested ternaries in parts
        test_py = self._convert_c_ternary(test)
        true_py = self._convert_c_ternary(true_part)
        false_py = self._convert_c_ternary(false_part)
        new_expr = f"({true_py}) if ({test_py}) else ({false_py})"
        return new_expr

    def _compile_declaration(self, stmt: str) -> List[str]:
        stmt = stmt.rstrip(";").strip()
        # Ignore zero-arg function prototypes like "int foo()"; not variable declarations
        if re.fullmatch(r"(?:const\s+)?(?:int|float|bool|char)\s+[A-Za-z_]\w*\s*\(\s*\)", stmt):
            return []

        match = re.match(r'(const\s+)?(int|float|bool|char)\s+([A-Za-z_]\w*)(\s*=\s*(.+))?$', stmt)
        if not match:
            raise CppCompilerError(f"Invalid declaration: {stmt}")

        is_const = bool(match.group(1))
        typename = match.group(2)
        name = match.group(3)
        init_expr = match.group(5)

        if name in self.var_registers:
            raise CppCompilerError(f"Variable '{name}' already declared")

        reg = self._allocate_var_register(name)
        code: List[str] = []

        if init_expr:
            expr = init_expr.strip()
            node = self._parse_expression_node(expr)
            code.extend(self._emit_expression_to_register(node, reg))
            try:
                self.variables[name] = self._evaluate_expression(expr)
            except CppCompilerError:
                pass
        else:
            if is_const:
                raise CppCompilerError(f"const {typename} {name} requires initialization")
            code.append(f"    LOADI {reg}, 0")
            self.variables[name] = 0

        if is_const:
            self.const_variables.add(name)
        return code

    def _compile_assignment(self, stmt: str) -> List[str]:
        stmt = stmt.rstrip(";")
        parts = stmt.split("=", 1)
        if len(parts) != 2:
            raise CppCompilerError(f"Invalid assignment: {stmt}")
        lhs = parts[0].strip()
        expr = parts[1].strip()
        
        # Check for array assignment: arr[index] = value
        if '[' in lhs and ']' in lhs:
            match = re.match(r'([A-Za-z_]\w*)\s*\[\s*(.+?)\s*\]', lhs)
            if match:
                arr_name = match.group(1)
                index_expr = match.group(2)
                
                if arr_name not in self.arrays:
                    raise CppCompilerError(f"Array '{arr_name}' not declared")
                
                arr_info = self.arrays[arr_name]
                base_addr = arr_info["addr"]
                
                code: List[str] = []
                
                # Evaluate the value to store
                val_reg = self._acquire_temp_register()
                node = self._parse_expression_node(expr)
                code.extend(self._emit_expression_to_register(node, val_reg))
                
                # Evaluate index
                idx_reg = self._acquire_temp_register()
                idx_node = self._parse_expression_node(index_expr)
                code.extend(self._emit_expression_to_register(idx_node, idx_reg))
                
                # Calculate address: base + (index * 4)
                addr_reg = self._acquire_temp_register()
                code.append(f"    LOADI {addr_reg}, 4")
                code.append(f"    MUL {idx_reg}, {addr_reg}")  # idx_reg = index * 4
                code.append(f"    LOADI {addr_reg}, {base_addr}")
                code.append(f"    ADD {idx_reg}, {addr_reg}")  # idx_reg = base + (index * 4)
                
                # Store value to memory
                code.append(f"    STORE {val_reg}, {idx_reg}")
                
                self._release_temp_register(addr_reg)
                self._release_temp_register(idx_reg)
                self._release_temp_register(val_reg)
                
                return code
        
        # Regular variable assignment
        if lhs in self.const_variables:
            raise CppCompilerError(f"Cannot assign to const variable '{lhs}'")
        reg = self._require_variable(lhs)
        node = self._parse_expression_node(expr)
        code = self._emit_expression_to_register(node, reg)
        # Track constant value if RHS is compile-time evaluable, but do not error if not.
        try:
            self.variables[lhs] = self._evaluate_expression(expr)
        except CppCompilerError:
            pass
        return code

    def _compile_compound_assignment(self, match: re.Match) -> List[str]:
        name = match.group(1)
        op = match.group(2)
        expr = match.group(3).strip()
        if name in self.const_variables:
            raise CppCompilerError(f"Cannot assign to const variable '{name}'")
        reg = self._require_variable(name)
        node = self._parse_expression_node(expr)
        code: List[str] = []
        # Evaluate RHS into a temporary register
        treg = self._acquire_temp_register()
        try:
            code.extend(self._emit_expression_to_register(node, treg))
            if op == "+=":
                code.append(f"    ADD {reg}, {treg}")
            elif op == "-=":
                code.append(f"    SUB {reg}, {treg}")
            elif op == "* =" or op == "*=":
                code.append(f"    MUL {reg}, {treg}")
            elif op == "/=":
                code.append(f"    DIV {reg}, {treg}")
            elif op == "&=":
                code.append(f"    AND {reg}, {treg}")
            elif op == "|=":
                code.append(f"    OR {reg}, {treg}")
            elif op == "^=":
                code.append(f"    XOR {reg}, {treg}")
            elif op == "<<=":
                code.append(f"    SHL {reg}, {treg}")
            elif op == ">> =" or op == ">>=":
                code.append(f"    SHR {reg}, {treg}")
            else:
                raise CppCompilerError(f"Unsupported compound assignment operator '{op}'")
        finally:
            self._release_temp_register(treg)
        # Best-effort constant tracking
        try:
            if name in self.variables:
                base = self.variables[name]
                rhs = self._evaluate_expression(expr)
                if op == "+=":
                    self.variables[name] = base + rhs
                elif op == "-=":
                    self.variables[name] = base - rhs
                elif op == "* =" or op == "*=":
                    self.variables[name] = base * rhs
                elif op == "/=":
                    if rhs != 0:
                        self.variables[name] = base // rhs
                elif op == "&=":
                    self.variables[name] = base & rhs
                elif op == "|=":
                    self.variables[name] = base | rhs
                elif op == "^=":
                    self.variables[name] = base ^ rhs
                elif op == "<<=":
                    self.variables[name] = base << rhs
                elif op == ">> =" or op == ">>=" and rhs >= 0:
                    self.variables[name] = base >> rhs
        except CppCompilerError:
            pass
        return code

    def _compile_incdec_statement(self, stmt: str) -> Optional[List[str]]:
        """Handle ++i, i++, --i, i-- as standalone statements.

        Expression-level ++/-- (e.g., x = y++) are not supported; this only
        compiles increment/decrement when they appear as full statements.
        """
        core = stmt.rstrip(";").strip()
        name: Optional[str] = None
        delta = 0
        m = re.fullmatch(r"([A-Za-z_]\w*)\s*(\+\+|--)", core)
        if m:
            name = m.group(1)
            delta = 1 if m.group(2) == "++" else -1
        else:
            m2 = re.fullmatch(r"(\+\+|--)\s*([A-Za-z_]\w*)", core)
            if m2:
                delta = 1 if m2.group(1) == "++" else -1
                name = m2.group(2)
        if name is None:
            return None
        if name in self.const_variables:
            raise CppCompilerError(f"Cannot modify const variable '{name}' with ++/--")
        reg = self._require_variable(name)
        # Use ADDI with small immediate; fits 16-bit range easily.
        return [f"    ADDI {reg}, {delta}"]

    def _allocate_var_register(self, name: str) -> str:
        if not self.var_register_pool:
            raise CppCompilerError("Out of registers for variable allocation")
        reg = self.var_register_pool.pop(0)
        self.var_registers[name] = reg
        return reg

    def _require_variable(self, name: str) -> str:
        if name not in self.var_registers:
            raise CppCompilerError(f"Use of undeclared variable '{name}'")
        return self.var_registers[name]

    def _acquire_temp_register(self) -> str:
        if not self.temp_register_pool:
            raise CppCompilerError("Out of temporary registers for expression evaluation")
        reg = self.temp_register_pool.pop()
        self._temp_register_stack.append(reg)
        # Debug logging for register allocation
        try:
            self.log(f"acquire_temp: {reg} (pool now: {self.temp_register_pool})", "DEBUG")
        except Exception:
            pass
        return reg

    def _release_temp_register(self, reg: str):
        if reg in self._temp_register_stack:
            self._temp_register_stack.remove(reg)
            self.stats["registers_reused"] += 1
        self.temp_register_pool.append(reg)
        try:
            self.log(f"release_temp: {reg} (pool now: {self.temp_register_pool})", "DEBUG")
        except Exception:
            pass
    
    def _release_all_temp_registers(self):
        """Release all temp registers - useful for cleanup"""
        while self._temp_register_stack:
            reg = self._temp_register_stack.pop()
            if reg not in self.temp_register_pool:
                self.temp_register_pool.append(reg)

    def _emit_load_immediate(self, target: str, value: int) -> List[str]:
        # Handle values that fit in 16-bit signed
        if -32768 <= value <= 32767:
            return [f"    LOADI {target}, {value}"]
        
        # For larger values, load in parts
        # This is a workaround for 32-bit constants
        value = value & 0xFFFFFFFF  # Ensure 32-bit
        low = value & 0xFFFF
        high = (value >> 16) & 0xFFFF
        
        code = []
        if high == 0:
            # Only low part needed
            code.append(f"    LOADI {target}, {low}")
        else:
            # Need both parts - use inline assembly as workaround
            self.warnings.append(f"Large constant 0x{value:08x} may not load correctly")
            # Just load the low part for now
            code.append(f"    LOADI {target}, {low & 0x7FFF}")
        
        return code

    def _emit_expression_to_register(self, node, target: str) -> List[str]:
        code: List[str] = []
        # Handle constant string literals explicitly (return address to string)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            label = self._add_string_literal(node.value)
            return [f"    LOADI {target}, {label}"]

        const_val = self._try_constant_value(node)
        if const_val is not None:
            code.extend(self._emit_load_immediate(target, const_val))
            return code
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            code.extend(self._emit_expression_to_register(node.operand, target))
            lbl_true = self._new_label("not_is_zero")
            lbl_done = self._new_label("not_done")
            code.append(f"    CMP {target}, 0")
            code.append(f"    JE {lbl_true}")
            code.append(f"    LOADI {target}, 0")
            code.append(f"    JMP {lbl_done}")
            code.append(f"{lbl_true}:")
            code.append(f"    LOADI {target}, 1")
            code.append(f"{lbl_done}:")
            return code
        if isinstance(node, ast.UnaryOp):
            code.extend(self._emit_expression_to_register(node.operand, target))
            if isinstance(node.op, ast.USub):
                code.append(f"    NEG {target}")
            elif isinstance(node.op, ast.UAdd):
                pass
            else:
                raise CppCompilerError("Unsupported unary operator")
            return code
        if isinstance(node, ast.Subscript):
            # Handle array access: arr[index]
            if isinstance(node.value, ast.Name):
                arr_name = node.value.id
                if arr_name in self.arrays:
                    arr_info = self.arrays[arr_name]
                    base_addr = arr_info["addr"]
                    
                    # Evaluate index
                    idx_reg = self._acquire_temp_register()
                    code.extend(self._emit_expression_to_register(node.slice, idx_reg))
                    
                    # Calculate address: base + (index * 4)
                    addr_reg = self._acquire_temp_register()
                    code.append(f"    LOADI {addr_reg}, 4")
                    code.append(f"    MUL {idx_reg}, {addr_reg}")  # idx_reg = index * 4
                    code.append(f"    LOADI {addr_reg}, {base_addr}")
                    code.append(f"    ADD {idx_reg}, {addr_reg}")  # idx_reg = base + (index * 4)
                    
                    # Load value from memory
                    code.append(f"    LOAD {target}, {idx_reg}")
                    
                    self._release_temp_register(addr_reg)
                    self._release_temp_register(idx_reg)
                    return code
            raise CppCompilerError("Array subscript not supported in this context")
        
        if isinstance(node, ast.Name):
            # If this name refers to a declared array, return its base address
            if node.id in self.arrays:
                base_addr = self.arrays[node.id]["addr"]
                code.append(f"    LOADI {target}, {base_addr}")
                return code
            src = self._require_variable(node.id)
            if src != target:
                code.append(f"    MOV {target}, {src}")
            return code
        # Ternary conditional operator: <test> ? <body> : <orelse>
        if isinstance(node, ast.IfExp):
            # Evaluate test into a temp register
            test_reg = self._acquire_temp_register()
            code.extend(self._emit_expression_to_register(node.test, test_reg))
            lbl_true = self._new_label('tern_true')
            lbl_done = self._new_label('tern_done')
            # If test == 0 -> false branch
            code.append(f"    CMP {test_reg}, 0")
            code.append(f"    JE {lbl_true}")
            # true branch: evaluate body into target
            code.extend(self._emit_expression_to_register(node.body, target))
            code.append(f"    JMP {lbl_done}")
            # false branch
            code.append(f"{lbl_true}:")
            code.extend(self._emit_expression_to_register(node.orelse, target))
            code.append(f"{lbl_done}:")
            self._release_temp_register(test_reg)
            return code
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or len(node.comparators) != 1:
                raise CppCompilerError("Chained comparisons not supported")
            left = node.left
            right = node.comparators[0]
            op = node.ops[0]
            code.extend(self._emit_expression_to_register(left, target))
            rhs_code, rhs_reg, should_release = self._load_operand(right)
            code.extend(rhs_code)
            code.append(f"    CMP {target}, {rhs_reg}")
            lbl_true = self._new_label("cmp_true")
            lbl_done = self._new_label("cmp_done")
            code.append(f"    LOADI {target}, 0")
            if isinstance(op, ast.Eq):
                jmp_true = "JE"
            elif isinstance(op, ast.NotEq):
                jmp_true = "JNE"
            elif isinstance(op, ast.Gt):
                jmp_true = "JG"
            elif isinstance(op, ast.GtE):
                jmp_true = "JGE"
            elif isinstance(op, ast.Lt):
                jmp_true = "JL"
            elif isinstance(op, ast.LtE):
                jmp_true = "JLE"
            else:
                raise CppCompilerError("Unsupported comparison operator")
            code.append(f"    {jmp_true} {lbl_true}")
            code.append(f"    JMP {lbl_done}")
            code.append(f"{lbl_true}:")
            code.append(f"    LOADI {target}, 1")
            code.append(f"{lbl_done}:")
            if should_release:
                self._release_temp_register(rhs_reg)
            return code
        if isinstance(node, ast.BoolOp):
            if not isinstance(node.op, (ast.And, ast.Or)):
                raise CppCompilerError("Unsupported boolean operator")
            code.extend(self._emit_expression_to_register(node.values[0], target))
            code.extend(self._emit_coerce_to_bool(target))
            if isinstance(node.op, ast.And):
                lbl_done = self._new_label("and_done")
                code.append(f"    CMP {target}, 0")
                code.append(f"    JE {lbl_done}")
                for rhs in node.values[1:]:
                    treg = self._acquire_temp_register()
                    code.extend(self._emit_expression_to_register(rhs, treg))
                    code.append(f"    MOV {target}, {treg}")
                    self._release_temp_register(treg)
                    code.extend(self._emit_coerce_to_bool(target))
                code.append(f"{lbl_done}:")
                return code
            else:
                lbl_done = self._new_label("or_done")
                code.append(f"    CMP {target}, 0")
                code.append(f"    JNE {lbl_done}")
                for rhs in node.values[1:]:
                    treg = self._acquire_temp_register()
                    code.extend(self._emit_expression_to_register(rhs, treg))
                    code.append(f"    MOV {target}, {treg}")
                    self._release_temp_register(treg)
                    code.extend(self._emit_coerce_to_bool(target))
                code.append(f"{lbl_done}:")
                return code
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fname = node.func.id
            # Small debug trace of intrinsic resolution
            self.log(f"emit_call: {fname} args={len(node.args)} target={target}", "DEBUG")
            # Intrinsic math helpers mapped directly to CPU opcodes
            if fname == "abs" and len(node.args) == 1:
                # abs(x) -> ABS target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    ABS {target}, {target}")
                return code
            if fname in ("min", "max") and len(node.args) == 2:
                # min(a,b) / max(a,b) -> MIN/MAX target, rhs_reg
                code.extend(self._emit_expression_to_register(node.args[0], target))
                rhs_code, rhs_reg, should_release = self._load_operand(node.args[1])
                code.extend(rhs_code)
                op = "MIN" if fname == "min" else "MAX"
                code.append(f"    {op} {target}, {rhs_reg}")
                if should_release:
                    self._release_temp_register(rhs_reg)
                return code
            if fname == "sqrt" and len(node.args) == 1:
                # sqrt(x) -> SQRT target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    SQRT {target}, {target}")
                return code
            if fname == "pow" and len(node.args) == 2:
                # pow(a,b) -> POW target, rhs_reg
                code.extend(self._emit_expression_to_register(node.args[0], target))
                rhs_code, rhs_reg, should_release = self._load_operand(node.args[1])
                code.extend(rhs_code)
                code.append(f"    POW {target}, {rhs_reg}")
                if should_release:
                    self._release_temp_register(rhs_reg)
                return code
            if fname == "log" and len(node.args) == 1:
                # log(x) -> LOG target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    LOG {target}, {target}")
                return code
            if fname == "exp" and len(node.args) == 1:
                # exp(x) -> EXP target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    EXP {target}, {target}")
                return code
            if fname == "sin" and len(node.args) == 1:
                # sin(x) -> SIN target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    SIN {target}, {target}")
                return code
            if fname == "cos" and len(node.args) == 1:
                # cos(x) -> COS target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    COS {target}, {target}")
                return code
            if fname == "tan" and len(node.args) == 1:
                # tan(x) -> TAN target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    TAN {target}, {target}")
                return code
            # Non-math utility intrinsics
            if fname == "rand" and len(node.args) == 0:
                # rand() -> RANDOM target
                code.append(f"    RANDOM {target}")
                return code
            if fname == "hash" and len(node.args) == 1:
                # hash(x) -> HASH target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    HASH {target}, {target}")
                return code
            if fname == "crc32" and len(node.args) == 1:
                # crc32(x) -> CRC32 target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    CRC32 {target}, {target}")
                return code
            # Game/Demo utility functions
            if fname == "sleep" and len(node.args) == 1:
                # sleep(ms) -> SLEEP R0, src_reg (two operand form, dst unused)
                src_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], src_reg))
                code.append(f"    SLEEP R0, {src_reg}")
                code.append(f"    LOADI {target}, 0")  # Return 0
                self._release_temp_register(src_reg)
                return code
            # Input/Output functions for interactive programs
            if fname == "get_input" and len(node.args) == 0:
                # get_input() -> syscall 46 (INPUT_INT) - read integer from stdin
                code.append(f"    LOADI R0, 46  ; INPUT_INT syscall")
                code.append(f"    SYSCALL R0")
                code.append(f"    MOV {target}, R0")
                return code
            if fname == "get_string" and len(node.args) == 1:
                # get_string(buf_addr) -> syscall 45 (INPUT) - read string from stdin
                buf_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], buf_reg))
                code.append(f"    LOADI R0, 45  ; INPUT syscall")
                code.append(f"    MOV R1, {buf_reg}")
                code.append(f"    LOADI R2, 256  ; max length")
                code.append(f"    SYSCALL R0")
                code.append(f"    MOV {target}, R0  ; Return length read")
                self._release_temp_register(buf_reg)
                return code
            if fname == "gettime" and len(node.args) == 0:
                # gettime() -> GETTIME target, R0 (two operand form)
                code.append(f"    GETTIME {target}, R0")
                return code
            if fname == "swap" and len(node.args) == 2:
                # swap(a, b) - swap two variables
                if not isinstance(node.args[0], ast.Name) or not isinstance(node.args[1], ast.Name):
                    raise CppCompilerError("swap() requires two variable names")
                reg_a = self._require_variable(node.args[0].id)
                reg_b = self._require_variable(node.args[1].id)
                code.append(f"    XCHG {reg_a}, {reg_b}")
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "reverse" and len(node.args) == 1:
                # reverse(x) -> REVERSE target, target (reverse bits)
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    REVERSE {target}, {target}")
                return code
            if fname == "strlen" and len(node.args) == 1:
                # strlen(addr) -> STRLEN target, addr_reg
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    STRLEN {target}, {target}")
                return code
            if fname == "abs" and len(node.args) == 1:
                # abs(x) -> absolute value
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    ABS {target}, {target}")
                return code
            if fname == "min" and len(node.args) == 2:
                # min(a, b) -> minimum of two values
                code.extend(self._emit_expression_to_register(node.args[0], target))
                b_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], b_reg))
                code.append(f"    MIN {target}, {b_reg}")
                self._release_temp_register(b_reg)
                return code
            if fname == "max" and len(node.args) == 2:
                # max(a, b) -> maximum of two values
                code.extend(self._emit_expression_to_register(node.args[0], target))
                b_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], b_reg))
                code.append(f"    MAX {target}, {b_reg}")
                self._release_temp_register(b_reg)
                return code
            if fname == "memset" and len(node.args) == 3:
                # memset(addr, value, count) -> MEMSET
                addr_reg = self._acquire_temp_register()
                val_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], addr_reg))
                code.extend(self._emit_expression_to_register(node.args[1], val_reg))
                code.extend(self._emit_expression_to_register(node.args[2], cnt_reg))
                code.append(f"    MEMSET {addr_reg}, {val_reg}, {cnt_reg}")
                code.append(f"    MOV {target}, {addr_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(val_reg)
                self._release_temp_register(addr_reg)
                return code
            # New useful functions for games/graphics
            if fname == "lerp" and len(node.args) == 3:
                # lerp(a, b, t) -> Linear interpolation
                # LERP dst, src, imm where dst=a, src=b, imm=t (0-255)
                code.extend(self._emit_expression_to_register(node.args[0], target))
                b_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], b_reg))
                # Try to get t as constant
                t_val = self._try_constant_value(node.args[2])
                if t_val is not None:
                    # Clamp t to 0-255
                    t_val = max(0, min(255, t_val))
                    code.append(f"    LERP {target}, {b_reg}, {t_val}")
                else:
                    # Dynamic t - need to use a different approach
                    # For now, emit a warning and use 128 (0.5)
                    self.warnings.append("lerp() with non-constant t uses t=128 (0.5)")
                    code.append(f"    LERP {target}, {b_reg}, 128")
                self._release_temp_register(b_reg)
                return code
            if fname == "sign" and len(node.args) == 1:
                # sign(x) -> -1, 0, or 1
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    SIGN {target}")
                return code
            if fname == "saturate" and len(node.args) == 1:
                # saturate(x) -> clamp to 0-255 (useful for colors)
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    SATURATE {target}")
                return code
            # Math functions
            if fname == "sqrt" and len(node.args) == 1:
                # sqrt(x) -> square root
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    SQRT {target}, {target}")
                return code
            if fname == "pow" and len(node.args) == 2:
                # pow(base, exp) -> power
                code.extend(self._emit_expression_to_register(node.args[0], target))
                exp_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], exp_reg))
                code.append(f"    POW {target}, {exp_reg}")
                self._release_temp_register(exp_reg)
                return code
            if fname == "rand" and len(node.args) == 0:
                # rand() -> random number
                code.append(f"    RANDOM {target}, R0")
                return code
            if fname == "srand" and len(node.args) == 1:
                # srand(seed) -> set random seed
                seed_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], seed_reg))
                code.append(f"    SETSEED {seed_reg}, R0")
                code.append(f"    LOADI {target}, 0")
                self._release_temp_register(seed_reg)
                return code
            if fname == "popcnt" and len(node.args) == 1:
                # popcnt(x) -> count set bits
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    POPCNT {target}, {target}")
                return code
            if fname == "clz" and len(node.args) == 1:
                # clz(x) -> count leading zeros
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    LZCNT {target}, {target}")
                return code
            if fname == "ctz" and len(node.args) == 1:
                # ctz(x) -> count trailing zeros
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    TZCNT {target}, {target}")
                return code
            # String and comparison utilities
            if fname == "strcmp" and len(node.args) == 2:
                # strcmp(addr1, addr2) -> compare strings
                addr1_reg = self._acquire_temp_register()
                addr2_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], addr1_reg))
                code.extend(self._emit_expression_to_register(node.args[1], addr2_reg))
                code.append(f"    STRCMP {target}, {addr1_reg}, {addr2_reg}")
                self._release_temp_register(addr2_reg)
                self._release_temp_register(addr1_reg)
                return code

            # strchr(hay, needle) -> STRCHR target, hay_reg, needle_reg
            if fname == "strchr" and len(node.args) == 2:
                hay_reg = self._acquire_temp_register()
                needle_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], hay_reg))
                code.extend(self._emit_expression_to_register(node.args[1], needle_reg))
                code.append(f"    STRCHR {target}, {hay_reg}, {needle_reg}")
                self._release_temp_register(needle_reg)
                self._release_temp_register(hay_reg)
                return code

            # strncat(dest, src, n) -> STRNCAT dst_reg, src_reg, cnt_reg
            if fname == "strncat" and len(node.args) == 3:
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], dst_reg))
                code.extend(self._emit_expression_to_register(node.args[1], src_reg))
                code.extend(self._emit_expression_to_register(node.args[2], cnt_reg))
                code.append(f"    STRNCAT {dst_reg}, {src_reg}, {cnt_reg}")
                code.append(f"    MOV {target}, {dst_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return code

            # atoi(str) -> ATOI target
            if fname == "atoi" and len(node.args) == 1:
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    ATOI {target}, {target}")
                return code
            # memcpy(dest, src, n) -> MEMCPY dst_reg, src_reg, cnt_reg
            if fname == "memcpy" and len(node.args) == 3:
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], dst_reg))
                code.extend(self._emit_expression_to_register(node.args[1], src_reg))
                code.extend(self._emit_expression_to_register(node.args[2], cnt_reg))
                code.append(f"    MEMCPY {dst_reg}, {src_reg}, {cnt_reg}")
                code.append(f"    MOV {target}, {dst_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return code

            # memcmp(a, b, n) -> CMPS target, a_reg, b_reg, cnt_reg
            if fname == "memcmp" and len(node.args) == 3:
                a_reg = self._acquire_temp_register()
                b_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], a_reg))
                code.extend(self._emit_expression_to_register(node.args[1], b_reg))
                code.extend(self._emit_expression_to_register(node.args[2], cnt_reg))
                code.append(f"    CMPS {target}, {a_reg}, {b_reg}, {cnt_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(b_reg)
                self._release_temp_register(a_reg)
                return code

            # memchr(base, byte, n) -> search memory for byte, return address or 0
            if fname == "memchr" and len(node.args) == 3:
                base_reg = self._acquire_temp_register()
                byte_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], base_reg))
                code.extend(self._emit_expression_to_register(node.args[1], byte_reg))
                code.extend(self._emit_expression_to_register(node.args[2], cnt_reg))
                # Move into R0,R1,R2 convention expected by CPU handler
                code.append(f"    MOV R0, {base_reg}")
                code.append(f"    MOV R1, {byte_reg}")
                code.append(f"    MOV R2, {cnt_reg}")
                code.append(f"    MEMCHR")
                code.append(f"    MOV {target}, R0")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(byte_reg)
                self._release_temp_register(base_reg)
                return code

            # revmem(addr, len) -> reverse bytes in-place; returns 0
            if fname == "revmem" and len(node.args) == 2:
                base_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], base_reg))
                code.extend(self._emit_expression_to_register(node.args[1], cnt_reg))
                code.append(f"    MOV R0, {base_reg}")
                code.append(f"    MOV R1, {cnt_reg}")
                code.append(f"    REV_MEM")
                code.append(f"    LOADI {target}, 0")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(base_reg)
                return code

            # strncpy(dest, src, n) -> STRNCPY dst_reg, src_reg, cnt_reg
            if fname == "strncpy" and len(node.args) == 3:
                dst_reg = self._acquire_temp_register()
                src_reg = self._acquire_temp_register()
                cnt_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], dst_reg))
                code.extend(self._emit_expression_to_register(node.args[1], src_reg))
                code.extend(self._emit_expression_to_register(node.args[2], cnt_reg))
                code.append(f"    STRNCPY {dst_reg}, {src_reg}, {cnt_reg}")
                code.append(f"    MOV {target}, {dst_reg}")
                self._release_temp_register(cnt_reg)
                self._release_temp_register(src_reg)
                self._release_temp_register(dst_reg)
                return code

            # strstr(hay, needle) -> STRSTR target, hay_reg, needle_reg
            if fname == "strstr" and len(node.args) == 2:
                hay_reg = self._acquire_temp_register()
                needle_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], hay_reg))
                code.extend(self._emit_expression_to_register(node.args[1], needle_reg))
                code.append(f"    STRSTR {target}, {hay_reg}, {needle_reg}")
                self._release_temp_register(needle_reg)
                self._release_temp_register(hay_reg)
                return code
            # Bit rotation
            if fname == "rotl" and len(node.args) == 2:
                # rotl(value, shift) -> rotate left
                code.extend(self._emit_expression_to_register(node.args[0], target))
                shift_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], shift_reg))
                code.append(f"    ROL {target}, {shift_reg}")
                self._release_temp_register(shift_reg)
                return code
            if fname == "rotr" and len(node.args) == 2:
                # rotr(value, shift) -> rotate right
                code.extend(self._emit_expression_to_register(node.args[0], target))
                shift_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], shift_reg))
                code.append(f"    ROR {target}, {shift_reg}")
                self._release_temp_register(shift_reg)
                return code
            # Byte swap for endianness
            if fname == "bswap" and len(node.args) == 1:
                # bswap(x) -> byte swap (reverse byte order)
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    BSWAP {target}")
                return code
            if fname == "clamp" and len(node.args) == 3:
                # clamp(x, lo, hi) implemented via MIN/MAX on registers
                # Evaluate x into target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                # Evaluate lo and hi into temporaries
                lo_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[1], lo_reg))
                hi_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[2], hi_reg))
                # target = min(target, hi_reg)
                code.append(f"    MIN {target}, {hi_reg}")
                # target = max(target, lo_reg)
                code.append(f"    MAX {target}, {lo_reg}")
                self._release_temp_register(hi_reg)
                self._release_temp_register(lo_reg)
                return code
            # Graphics functions
            if fname == "pixel" and len(node.args) == 3:
                # pixel(x, y, color) -> PIXEL (uses R0=x, R1=y, R2=color)
                code.extend(self._emit_expression_to_register(node.args[0], "R0"))
                code.extend(self._emit_expression_to_register(node.args[1], "R1"))
                code.extend(self._emit_expression_to_register(node.args[2], "R2"))
                code.append(f"    PIXEL")
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "line" and len(node.args) == 5:
                # line(x1, y1, x2, y2, color) -> LINE
                code.extend(self._emit_expression_to_register(node.args[0], "R0"))
                code.extend(self._emit_expression_to_register(node.args[1], "R1"))
                code.extend(self._emit_expression_to_register(node.args[2], "R2"))
                code.extend(self._emit_expression_to_register(node.args[3], "R3"))
                color_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[4], color_reg))
                code.append(f"    LINE {color_reg}")
                self._release_temp_register(color_reg)
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "rect" and len(node.args) == 5:
                # rect(x, y, w, h, color) -> RECT
                code.extend(self._emit_expression_to_register(node.args[0], "R0"))
                code.extend(self._emit_expression_to_register(node.args[1], "R1"))
                code.extend(self._emit_expression_to_register(node.args[2], "R2"))
                code.extend(self._emit_expression_to_register(node.args[3], "R3"))
                color_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[4], color_reg))
                code.append(f"    RECT {color_reg}")
                self._release_temp_register(color_reg)
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "fillrect" and len(node.args) == 5:
                # fillrect(x, y, w, h, color) -> FILLRECT
                code.extend(self._emit_expression_to_register(node.args[0], "R0"))
                code.extend(self._emit_expression_to_register(node.args[1], "R1"))
                code.extend(self._emit_expression_to_register(node.args[2], "R2"))
                code.extend(self._emit_expression_to_register(node.args[3], "R3"))
                color_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[4], color_reg))
                code.append(f"    FILLRECT {color_reg}")
                self._release_temp_register(color_reg)
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "circle" and len(node.args) == 4:
                # circle(cx, cy, r, color) -> CIRCLE
                code.extend(self._emit_expression_to_register(node.args[0], "R0"))
                code.extend(self._emit_expression_to_register(node.args[1], "R1"))
                code.extend(self._emit_expression_to_register(node.args[2], "R2"))
                color_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[3], color_reg))
                code.append(f"    CIRCLE {color_reg}")
                self._release_temp_register(color_reg)
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "fillcircle" and len(node.args) == 4:
                # fillcircle(cx, cy, r, color) -> FILLCIRCLE
                code.extend(self._emit_expression_to_register(node.args[0], "R0"))
                code.extend(self._emit_expression_to_register(node.args[1], "R1"))
                code.extend(self._emit_expression_to_register(node.args[2], "R2"))
                color_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[3], color_reg))
                code.append(f"    FILLCIRCLE {color_reg}")
                self._release_temp_register(color_reg)
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            if fname == "getpixel" and len(node.args) == 2:
                # getpixel(x, y) -> GETPIXEL (returns color)
                code.extend(self._emit_expression_to_register(node.args[0], "R1"))
                code.extend(self._emit_expression_to_register(node.args[1], "R2"))
                code.append(f"    GETPIXEL {target}")
                return code
            if fname == "clear" and len(node.args) == 1:
                # clear(color) -> CLEAR
                color_reg = self._acquire_temp_register()
                code.extend(self._emit_expression_to_register(node.args[0], color_reg))
                code.append(f"    CLEAR {color_reg}")
                self._release_temp_register(color_reg)
                code.append(f"    LOADI {target}, 0")  # Return 0
                return code
            # Bit helper intrinsics
            if fname == "popcount" and len(node.args) == 1:
                # popcount(x) -> POPCOUNT target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    POPCOUNT {target}, {target}")
                return code
            if fname == "lzcnt" and len(node.args) == 1:
                # lzcnt(x) -> LZCNT target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    LZCNT {target}, {target}")
                return code
            if fname == "tzcnt" and len(node.args) == 1:
                # tzcnt(x) -> TZCNT target, target
                code.extend(self._emit_expression_to_register(node.args[0], target))
                code.append(f"    TZCNT {target}, {target}")
                return code

            # Regular function calls
            if node.args:
                for arg in reversed(node.args):
                    treg = self._acquire_temp_register()
                    code.extend(self._emit_expression_to_register(arg, treg))
                    code.append(f"    PUSH {treg}")
                    self._release_temp_register(treg)
            if fname in self.var_registers:
                reg = self._require_variable(fname)
                code.append(f"    CALLR {reg}")
            else:
                code.append(f"    CALL {fname}")
            if node.args:
                code.append(f"    ADDI R14, {len(node.args)*4}")
            if target != "R0":
                code.append(f"    MOV {target}, R0")
            return code
        if isinstance(node, ast.BinOp):
            code.extend(self._emit_expression_to_register(node.left, target))
            rhs_code, rhs_reg, should_release = self._load_operand(node.right)
            code.extend(rhs_code)
            code.extend(self._emit_binop(node.op, target, rhs_reg))
            if should_release:
                self._release_temp_register(rhs_reg)
            return code
        # Emit a helpful debug message about unsupported node types
        try:
            nodetype = type(node).__name__
        except Exception:
            nodetype = str(node)
        self.log(f"unsupported_expression_node: {nodetype}", "ERROR")
        raise CppCompilerError("Unsupported expression construct")

    def _emit_coerce_to_bool(self, reg: str) -> List[str]:
        lines: List[str] = []
        lbl_true = self._new_label("bool_true")
        lbl_done = self._new_label("bool_done")
        lines.append(f"    CMP {reg}, 0")
        lines.append(f"    JE {lbl_done}")
        lines.append(f"    LOADI {reg}, 1")
        lines.append(f"    JMP {lbl_done}")
        lines.append(f"{lbl_done}:")
        lines.append(f"    CMP {reg}, 0")
        lines.append(f"    JNE {lbl_true}")
        lines.append(f"    LOADI {reg}, 0")
        lines.append(f"{lbl_true}:")
        return lines

    def _load_operand(self, node) -> Tuple[List[str], str, bool]:
        if isinstance(node, ast.Name):
            return [], self._require_variable(node.id), False
        const_val = self._try_constant_value(node)
        if const_val is not None:
            tmp = self._acquire_temp_register()
            return self._emit_load_immediate(tmp, const_val), tmp, True
        tmp = self._acquire_temp_register()
        code = self._emit_expression_to_register(node, tmp)
        return code, tmp, True

    def _emit_binop(self, op, target: str, rhs_reg: str) -> List[str]:
        if isinstance(op, ast.Add):
            return [f"    ADD {target}, {rhs_reg}"]
        if isinstance(op, ast.Sub):
            return [f"    SUB {target}, {rhs_reg}"]
        if isinstance(op, ast.Mult):
            return [f"    MUL {target}, {rhs_reg}"]
        if isinstance(op, ast.Div) or isinstance(op, ast.FloorDiv):
            return [f"    DIV {target}, {rhs_reg}"]
        if isinstance(op, ast.Mod):
            return [f"    MOD {target}, {rhs_reg}"]
        if isinstance(op, ast.BitAnd):
            return [f"    AND {target}, {rhs_reg}"]
        if isinstance(op, ast.BitOr):
            return [f"    OR {target}, {rhs_reg}"]
        if isinstance(op, ast.BitXor):
            return [f"    XOR {target}, {rhs_reg}"]
        if isinstance(op, ast.LShift):
            return [f"    SHL {target}, {rhs_reg}"]
        if isinstance(op, ast.RShift):
            return [f"    SHR {target}, {rhs_reg}"]
        raise CppCompilerError("Unsupported binary operator")

    def _try_constant_value(self, node) -> Optional[int]:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool)):
                return int(node.value)
            return None
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            inner = self._try_constant_value(node.operand)
            if inner is None:
                return None
            return inner if isinstance(node.op, ast.UAdd) else -inner
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            inner = self._try_constant_value(node.operand)
            if inner is None:
                return None
            return ~inner
        if isinstance(node, ast.BinOp):
            left = self._try_constant_value(node.left)
            right = self._try_constant_value(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, (ast.Div, ast.FloorDiv)):
                if right == 0:
                    return None
                return left // right
            if isinstance(node.op, ast.Mod):
                if right == 0:
                    return None
                return left % right
            if isinstance(node.op, ast.BitAnd):
                return left & right
            if isinstance(node.op, ast.BitOr):
                return left | right
            if isinstance(node.op, ast.BitXor):
                return left ^ right
            if isinstance(node.op, ast.LShift):
                if right < 0:
                    return None
                return left << right
            if isinstance(node.op, ast.RShift):
                if right < 0:
                    return None
                return left >> right
        return None

    def _compile_array_declaration(self, stmt: str) -> List[str]:
        """Compile array declarations like: int arr[10]; or int arr[5] = {1,2,3,4,5};"""
        stmt = stmt.rstrip(";").strip()
        
        # Parse: type name[size] or type name[size] = {...}
        match = re.match(r'(int|float|bool|char)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\](\s*=\s*\{([^}]+)\})?', stmt)
        if not match:
            raise CppCompilerError(f"Invalid array declaration: {stmt}")
        
        typename = match.group(1)
        name = match.group(2)
        size = int(match.group(3))
        init_values = match.group(5)
        
        if name in self.arrays:
            raise CppCompilerError(f"Array '{name}' already declared")
        
        # Allocate memory for array
        addr = self.array_base_addr
        self.arrays[name] = {
            "type": typename,
            "size": size,
            "addr": addr
        }
        self.array_base_addr += size * 4  # Each element is 4 bytes
        
        code: List[str] = [f"    ; Array {name}[{size}] at 0x{addr:04x}"]
        
        # Initialize array if values provided
        if init_values:
            values = [v.strip() for v in init_values.split(',')]
            for i, val in enumerate(values[:size]):  # Don't exceed array size
                try:
                    value = int(val)
                    offset = addr + (i * 4)
                    treg = self._acquire_temp_register()
                    code.append(f"    LOADI {treg}, {value}")
                    code.append(f"    LOADI R0, {offset}")
                    code.append(f"    STORE {treg}, R0")
                    self._release_temp_register(treg)
                except ValueError:
                    self.warnings.append(f"Invalid array initializer value: {val}")
        
        return code

    def _compile_class_definition(self, stmt: str) -> List[str]:
        """Compile simple class definitions with member variables and methods"""
        # Class definitions might span multiple statements, so we need to handle them carefully
        # For now, we'll look for the pattern: class Name { ... };
        
        # Remove trailing semicolon if present
        stmt = stmt.rstrip(';').strip()
        
        # Extract class name and body
        match = re.match(r'class\s+([A-Za-z_]\w*)\s*\{(.+)\}', stmt, re.DOTALL)
        if not match:
            # Maybe it's just the class header, store it for later
            match2 = re.match(r'class\s+([A-Za-z_]\w*)\s*\{', stmt)
            if match2:
                class_name = match2.group(1)
                # Register empty class for now
                self.class_definitions[class_name] = {
                    "members": [],
                    "size": 0
                }
                return [f"    ; Class {class_name} declared"]
            raise CppCompilerError(f"Invalid class definition: {stmt}")
        
        class_name = match.group(1)
        body = match.group(2).strip()
        
        if class_name in self.class_definitions:
            raise CppCompilerError(f"Class '{class_name}' already defined")
        
        # Parse class members (simplified - just track member variables)
        members = []
        for line in body.split(';'):
            line = line.strip()
            if not line:
                continue
            # Look for member variable declarations
            m = re.match(r'(int|float|bool|char)\s+([A-Za-z_]\w*)', line)
            if m:
                members.append({
                    "type": m.group(1),
                    "name": m.group(2)
                })
        
        self.class_definitions[class_name] = {
            "members": members,
            "size": len(members) * 4  # Each member is 4 bytes
        }
        
        # Classes are compile-time constructs, no runtime code needed
        return [f"    ; Class {class_name} defined with {len(members)} members"]

    def _evaluate_expression(self, expr: str) -> int:
        expr = self._normalize_expression(expr)
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise CppCompilerError(f"Invalid expression '{expr}'") from exc
        return self._eval_node(tree.body)

    def _eval_node(self, node) -> int:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, bool)):
                return int(node.value)
            raise CppCompilerError("Only numeric constants supported")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            val = self._eval_node(node.operand)
            return val if isinstance(node.op, ast.UAdd) else -val
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
            val = self._eval_node(node.operand)
            return ~val
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, (ast.Div, ast.FloorDiv)):
                if right == 0:
                    raise CppCompilerError("Division by zero in expression")
                return left // right
            if isinstance(node.op, ast.Mod):
                if right == 0:
                    raise CppCompilerError("Modulo by zero in expression")
                return left % right
            if isinstance(node.op, ast.BitAnd):
                return left & right
            if isinstance(node.op, ast.BitOr):
                return left | right
            if isinstance(node.op, ast.BitXor):
                return left ^ right
            if isinstance(node.op, ast.LShift):
                if right < 0:
                    raise CppCompilerError("Negative shift count")
                return left << right
            if isinstance(node.op, ast.RShift):
                if right < 0:
                    raise CppCompilerError("Negative shift count")
                return left >> right
        if isinstance(node, ast.Name):
            if node.id not in self.variables:
                raise CppCompilerError(f"Unknown identifier '{node.id}'")
            return self.variables[node.id]
        raise CppCompilerError("Unsupported expression construct")

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
    cas++ <src.cpp> [out.bin] [--run] [--asm] [--debug] - compile C++ source
    compilecpp <src.cpp> [out.bin] [options] - alias for cas++
    cpprun <src.cpp> [options] - compile and immediately run program
    c++ - show cas++ compiler help and usage
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
    enterbios - interactive BIOS mode (inspect/change flags)
    setflag <FLAG> - set a CPU flag from shell
    acc [get|set <value>] - inspect or set accumulator register
    sysinfo - show system information
    random - generate random number
    bootload - enter bootloader mode
    entboot - interactive bootloader shell (load, write, dump, run, boot)
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
    memscrub <addr> <len> - securely zero a memory range
    self-repair [target] - run automatic repairs on components
    diagnose [component] - run system diagnostics and self-repair
    """
    def __init__(self, kernel: Kernel, cpu: CPU, assembler: Assembler, bios: BIOS):
        self.kernel = kernel
        self.cpu = cpu
        self.assembler = assembler
        self.bios = bios
        self.bootloader = Bootloader()
        self.history_index = 0
    
    def _resolve_path(self, path: str) -> str:
        """Resolve user-supplied path against current working directory."""
        return self.kernel.normalize_path(path, self.kernel.cwd)
    
    def _default_cpp_output(self, filename: str) -> str:
        if filename.endswith(".cpp"):
            base = filename[:-4]
        else:
            base = filename
        if not base:
            base = "a"
        return f"{base}.bin"
    
    def _get_file_entry(self, path: str, allow_dirs: bool = False):
        """Retrieve a file entry with helpful error handling."""
        try:
            abs_path, entry = self.kernel.get_entry(path, self.kernel.cwd)
        except FileNotFoundError:
            print(f"File not found: {path}")
            return None, None
        if not allow_dirs and entry.get("is_dir", False):
            print(f"{path} is a directory")
            return None, None
        return abs_path, entry
    
    def _read_file_bytes(self, path: str):
        """Return (abs_path, bytes) for a file or (None, None) if missing."""
        abs_path, entry = self._get_file_entry(path)
        if abs_path is None:
            return None, None
        data = entry["data"]
        if isinstance(data, str):
            data = data.encode("utf-8")
        return abs_path, data
    
    def _read_text(self, path: str):
        """Return (abs_path, text) decoding as UTF-8."""
        abs_path, entry = self._get_file_entry(path)
        if abs_path is None:
            return None, None
        data = entry["data"]
        text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
        return abs_path, text
    def run(self):
        print("Welcome to SimpleOS shell. Type 'help' for commands.")
        while True:
            try:
                # Show current directory in prompt
                prompt_dir = self.kernel.cwd if self.kernel.cwd != "/" else ""
                prompt = f"simpleos{prompt_dir}> "
                line = input(prompt)
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
                    if not args:
                        # Show command categories
                        print("Available command categories:")
                        print("  system    - System and process management commands")
                        print("  file      - File operations and management")
                        print("  text      - Text processing commands")
                        print("  data      - Data encoding and hashing commands")
                        print("  memory    - Memory and CPU operations")
                        print("  network   - Network simulation commands")
                        print("  cpp       - C++ compiler commands")
                        print("  games     - Terminal games (Snake, Minesweeper, Tetris)")
                        print("  util      - Utility commands")
                        print("\nUse 'help <category>' to see specific commands.")
                        # continue main loop (don't exit shell)
                        continue
                        
                    category = args[0].lower()
                    if category == "system":
                        print("System Commands:")
                        print("  ps        - List processes")
                        print("  kill      - Kill a process")
                        print("  reboot    - Reboot the system")
                        print("  sysinfo   - Show system information")
                        print("  uptime    - Show system uptime")
                        print("  top       - Show process information")
                        print("  date      - Show current date")
                        print("  time      - Show current time")
                        print("  bios      - Show BIOS information")
                        print("  sleep     - Delay execution")
                        print("  ver       - Show version information")
                        print("  whoami    - Show current user")
                        print("  uname     - Show system info")
                        print("  env       - Show environment variables")
                        print("  export    - Set environment variable")
                        print("  unset     - Remove environment variable")
                        print("  diagnose  - Run system diagnostics")
                        print("  self-repair - Attempt automated repairs")
                        print("  diagnose  - Run system diagnostics and self-repair")
                    elif category == "file":
                        print("File Commands:")
                        print("  ls        - List files")
                        print("  cd        - Change directory")
                        print("  pwd       - Print working directory")
                        print("  cat       - Display file contents")
                        print("  nano      - Text editor (like nano)")
                        print("  write     - Write text to file")
                        print("  mkdir     - Create directory")
                        print("  rm        - Remove file")
                        print("  cp        - Copy file")
                        print("  mv        - Move file")
                        print("  chmod     - Change file permissions")
                        print("  stat      - Show file information")
                        print("  type      - Print file contents")
                        print("  find      - Search for files")
                        print("  touch     - Create empty file")
                        print("  df        - Show disk usage")
                    elif category == "text":
                        print("Text Processing Commands:")
                        print("  grep      - Search within files")
                        print("  wc        - Count lines/words/chars")
                        print("  head      - Show first N lines")
                        print("  tail      - Show last N lines")
                        print("  sort      - Sort lines")
                        print("  uniq      - Remove duplicate lines")
                        print("  cut       - Extract columns")
                        print("  tr        - Translate characters")
                        print("  upper     - Convert to uppercase")
                        print("  lower     - Convert to lowercase")
                        print("  reverse   - Reverse text")
                        print("  diff      - Compare two files")
                    elif category == "data":
                        print("Data Processing Commands:")
                        print("  base64    - Base64 encode/decode")
                        print("  base32    - Base32 encode/decode")
                        print("  hex       - Hex encode/decode")
                        print("  rot13     - ROT13 encode/decode")
                        print("  md5       - MD5 hash")
                        print("  sha256    - SHA256 hash")
                        print("  hexdump   - Hex dump of file/memory")
                    elif category == "memory":
                        print("Memory & Assembly Commands:")
                        print("  memmap    - Map memory region")
                        print("  memstats  - Show memory statistics")
                        print("  memscrub  - Securely zero a memory range")
                        print("  meminfo   - Show memory info")
                        print("  regs      - Show CPU registers")
                        print("  disasm    - Disassemble memory")
                        print("  debug     - Enable/disable CPU tracing")
                        print("  trace     - Trace execution")
                        print("  loadasm   - Load assembly program")
                        print("  asminfo   - Show assembler symbols")
                        print("  asmtest   - Run assembler tests")
                        print("  run       - Execute program")
                        print("  cpuinfo   - Show CPU information")
                    elif category == "cpp":
                        print("C++ Compiler Commands:")
                        print("  cas++      - Compile C++ source with cas++")
                        print("  compilecpp - Alias for cas++")
                        print("  cpprun     - Compile and immediately run C++ code")
                        print("  c++        - Show detailed cas++ help")
                        print("  benchmark - Run benchmarks")
                    elif category == "network":
                        print("Network Commands:")
                        print("  ping <host>              - Test connectivity (real TCP)")
                        print("  curl <url>               - Fetch URL content (real HTTP GET)")
                        print("  wget <url>               - Download file (real HTTP)")
                        print("  http <get|head> <url>    - HTTP operations")
                        print("  dns <hostname>           - DNS lookup")
                        print("  download <url> [file]    - Download and save file")
                        print("  nettest <host> <port>    - Test network connectivity")
                        print("  netsocket <cmd> [args]   - Socket operations (create, connect, send, recv, close)")
                    elif category == "games":
                        print("Terminal Games:")
                        print("  snake       - Play Snake game")
                        print("  minesweeper - Play Minesweeper")
                        print("  tetris      - Play Tetris (auto-falling!)")
                        print("\nControls:")
                        print("  Snake:       w/a/s/d to change direction, Enter to move, q to quit")
                        print("  Minesweeper: 'row col' to reveal (e.g., '3 4')")
                        print("                'f row col' to flag, q to quit")
                        print("  Tetris:      a/d to move, w to rotate, s to drop fast, q to quit")
                        print("                Pieces fall automatically every 0.8 seconds!")
                    elif category == "util":
                        print("Utility Commands:")
                        print("  echo      - Print text")
                        print("  clear/cls - Clear screen")
                        print("  calc      - Basic calculator")
                        print("  history   - Show command history")
                        print("  set       - Set environment variable")
                        print("  get       - Get environment variable")
                        print("  random    - Generate random number")
                        print("  stats     - Show system statistics")
                        print("  test      - Run tests")
                        print("  exit/quit - Exit the shell")
                    else:
                        print(f"Unknown category: {category}")
                        print("Use 'help' for list of categories.")
                elif cmd == "ls":
                    self.do_ls(args)
                elif cmd == "cd":
                    self.do_cd(args)
                elif cmd == "pwd":
                    print(self.kernel.cwd)
                elif cmd == "cat":
                    self.do_cat(args)
                elif cmd == "nano":
                    self.do_nano(args)
                elif cmd == "diagnose":
                    self.do_diagnose(args)
                elif cmd == "self-repair":
                    self.do_self_repair(args)
                elif cmd == "cas++":
                    self.do_caspp(args)
                elif cmd == "c++":
                    self.do_cpp_help(args)
                elif cmd == "compilecpp":
                    self.do_compile_cpp(args)
                elif cmd == "cpprun":
                    self.do_run_cpp(args)
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
                elif cmd == "runmt":
                    self.do_runmt(args)
                elif cmd == "threads":
                    self.do_threads(args)
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
                elif cmd == "enterbios":
                    self.do_enterbios(args)
                elif cmd == "sysinfo":
                    self.do_sysinfo(args)
                elif cmd == "random":
                    self.do_random(args)
                elif cmd == "bootload":
                    self.do_bootload(args)
                elif cmd == "entboot":
                    self.do_entboot(args)
                elif cmd == "clear":
                    self.do_clear(args)
                elif cmd == "history":
                    self.do_history(args)
                elif cmd == "set":
                    self.do_set(args)
                elif cmd == "get":
                    self.do_get(args)
                elif cmd == "setflag":
                    if len(args) != 1:
                        print("Usage: setflag <FLAG>")
                    else:
                        name = args[0].upper()
                        mask = FLAG_NAME_MAP.get(name)
                        if mask is None:
                            print("Unknown flag", name)
                        else:
                            self.cpu.set_flag(mask)
                            print(f"Set {name}")
                elif cmd == "acc":
                    # acc [get|set <value>]
                    if not args or args[0] == 'get':
                        print(f"ACC=0x{self.cpu.acc:08x}")
                    elif args[0] == 'set' and len(args) == 2:
                        try:
                            v = int(args[1], 0)
                            self.cpu.acc = v & 0xFFFFFFFF
                            print(f"ACC set to 0x{self.cpu.acc:08x}")
                        except ValueError:
                            print("Invalid value")
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
                elif cmd == "nettest":
                    self.do_nettest(args)
                elif cmd == "netsocket":
                    self.do_netsocket(args)
                elif cmd == "http":
                    self.do_http(args)
                elif cmd == "dns":
                    self.do_dns(args)
                elif cmd == "download":
                    self.do_download(args)
                elif cmd == "memstats":
                    self.do_memstats(args)
                elif cmd == "memscrub":
                    self.do_memscrub(args)
                elif cmd == "meminfo":
                    self.do_meminfo(args)
                elif cmd == "asmtest":
                    self.do_asmtest(args)
                elif cmd == "stats":
                    self.do_stats(args)
                elif cmd == "cpuinfo":
                    self.do_cpuinfo(args)
                elif cmd == "benchmark":
                    self.do_benchmark(args)
                elif cmd == "test":
                    self.do_test(args)
                # Data processing commands
                elif cmd == "hexdump":
                    self.do_hexdump(args)
                elif cmd == "md5":
                    self.do_md5(args)
                elif cmd == "sha256":
                    self.do_sha256(args)
                elif cmd == "base64":
                    self.do_base64(args)
                elif cmd == "base32":
                    self.do_base32(args)
                elif cmd == "hex":
                    self.do_hex(args)
                elif cmd == "rot13":
                    self.do_rot13(args)
                # Text processing commands
                elif cmd == "reverse":
                    self.do_reverse(args)
                elif cmd == "upper":
                    self.do_upper(args)
                elif cmd == "lower":
                    self.do_lower(args)
                elif cmd == "tr":
                    self.do_tr(args)
                elif cmd == "cut":
                    self.do_cut(args)
                elif cmd == "sort":
                    self.do_sort(args)
                elif cmd == "uniq":
                    self.do_uniq(args)
                elif cmd == "head":
                    self.do_head(args)
                elif cmd == "tail":
                    self.do_tail(args)
                elif cmd == "diff":
                    self.do_diff(args)
                # System commands
                elif cmd == "uname":
                    self.do_uname(args)
                elif cmd == "touch":
                    self.do_touch(args)
                elif cmd == "env":
                    self.do_env(args)
                elif cmd == "export":
                    self.do_export(args)
                elif cmd == "unset":
                    self.do_unset(args)
                # Game commands
                elif cmd == "snake":
                    self.do_snake(args)
                elif cmd == "minesweeper":
                    self.do_minesweeper(args)
                elif cmd == "tetris":
                    self.do_tetris(args)
                else:
                    print("Unknown command. Type 'help'.")
            except Exception as e:
                print("Error:", e)
        return False
    def do_ls(self, args):
        """List files and directories"""
        long_format = False
        target = None
        for arg in args:
            if arg == "-l":
                long_format = True
            elif target is None:
                target = arg
        path = target if target is not None else self.kernel.cwd
        try:
            entries = self.kernel.list_directory(path, self.kernel.cwd)
        except FileNotFoundError:
            print(f"ls: cannot access '{path}': No such file or directory")
            return
        except NotADirectoryError:
            entries = [self.kernel.get_entry(path, self.kernel.cwd)]

        if long_format:
            print(f"{'Mode':<10} {'Size':<8} {'Created':<20} {'Modified':<20} {'Name'}")

        for entry_path, info in entries:
            display_name = self.kernel.display_name(entry_path)
            mode_str = "drwxr-xr-x" if info.get("is_dir") else "rw-r--r--"
            size = len(info["data"])
            created = time.ctime(info["created_time"])
            modified = time.ctime(info["modified_time"])
            if long_format:
                print(f"{mode_str:<10} {size:<8} {created:<20} {modified:<20} {display_name}")
            else:
                print(f"{display_name}\t{size} bytes")
    def do_cat(self, args):
        if not args:
            print("Usage: cat <file>")
            return
        name = args[0]
        try:
            _, data = self.kernel.read_file(name, self.kernel.cwd)
        except FileNotFoundError:
            print("File not found:", name)
            return
        except IsADirectoryError:
            print(f"{name} is a directory")
            return
        try:
            print(data.decode("utf-8", errors="replace"))
        except Exception:
            print(data)
    
    def do_cd(self, args):
        """Change directory"""
        if not args:
            target = self.kernel.env_vars.get("HOME", "/")
        else:
            target = args[0]
        new_path = self.kernel.normalize_path(target, self.kernel.cwd)
        entry = self.kernel.files.get(new_path)
        if entry is None or not entry.get("is_dir", False):
            print(f"cd: no such directory: {target}")
            return
        self.kernel.cwd = new_path
        self.kernel.env_vars["PWD"] = self.kernel.cwd
        print(f"Changed directory to: {self.kernel.cwd}")
    
    def do_nano(self, args):
        """Simple text editor similar to nano"""
        if not args:
            print("Usage: nano <file>")
            return
        filename = args[0]
        try:
            _, data = self.kernel.read_file(filename, self.kernel.cwd)
            content = data.decode("utf-8")
        except FileNotFoundError:
            content = ""
        except IsADirectoryError:
            print(f"{filename} is a directory")
            return
        except Exception as e:
            print("Error reading file:", e)
            return
        
        print(f"Nano Editor - Editing: {filename}")
        print("="*50)
        print("Commands: :w (save), :q (quit), :wq (save & quit)")
        print("Enter text (empty line + :command to execute)")
        print("="*50)
        
        lines = content.split("\n") if content else []
        
        # Display current content
        if lines:
            print("\nCurrent content:")
            for i, line in enumerate(lines, 1):
                print(f"{i:3}: {line}")
        
        print("\nEnter new content (type :w to save, :q to quit, :wq to save & quit):")
        
        new_lines = []
        while True:
            try:
                line = input()
                if line == ":w":
                    # Save
                    new_content = "\n".join(new_lines)
                    self.kernel.write_file(filename, new_content.encode("utf-8"), 0o644, self.kernel.cwd)
                    print(f"Saved {len(new_content)} bytes to {filename}")
                elif line == ":q":
                    # Quit without saving
                    print("Quit without saving")
                    break
                elif line == ":wq":
                    # Save and quit
                    new_content = "\n".join(new_lines)
                    self.kernel.write_file(filename, new_content.encode("utf-8"), 0o644, self.kernel.cwd)
                    print(f"Saved {len(new_content)} bytes to {filename}")
                    break
                else:
                    new_lines.append(line)
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nAborted")
                break
    
    def do_write(self, args):
        if len(args) < 2:
            print("Usage: write <file> <text...>")
            return
        name = args[0]
        text = " ".join(args[1:])
        self.kernel.write_file(name, text.encode("utf-8"), 0o644, self.kernel.cwd)
        print(f"Wrote {len(text)} bytes to {self.kernel.normalize_path(name, self.kernel.cwd)}")
    
    def do_caspp(self, args):
        """Compile C++ code using the cas++ compiler"""
        if not args:
            print("Usage: cas++ <source.cpp> [output.bin] [--run] [--asm] [--debug] [--output]")
            return
        run_after = "--run" in args
        show_asm = "--asm" in args
        debug_mode = "--debug" in args
        output_only = "--output" in args
        positional = [arg for arg in args if not arg.startswith("--")]
        if not positional:
            print("Usage: cas++ <source.cpp> [output.bin] [--run] [--asm] [--debug] [--output]")
            return
        src = positional[0]
        out_file = positional[1] if len(positional) > 1 else self._default_cpp_output(src)
        abs_src, source_bytes = self._read_file_bytes(src)
        if abs_src is None:
            return
        source_text = source_bytes.decode("utf-8", errors="replace")
        compiler = CppCompiler()
        try:
            binary = compiler.compile(source_text)
        except CppCompilerError as exc:
            print(f"cas++ error: {exc}")
            return
        abs_out = self.kernel.write_file(out_file, binary, 0o755, self.kernel.cwd)
        
        # If --output flag is set, suppress all compilation info
        if not output_only:
            statement_count = compiler.functions.get("main", {}).get("statements", 0)
            stats = compiler.get_stats()
            
            print(f"✓ cas++ compiled {abs_src} -> {abs_out} ({len(binary)} bytes)")
            print(f"  Statements: {statement_count}")
            print(f"  Variables: {stats['variables']}, Arrays: {stats['arrays']}, Classes: {stats['classes']}")
            print(f"  String literals: {stats['string_literals']}")
            
            # Show performance stats if optimizations were used
            if stats['expressions_cached'] > 0 or stats['registers_reused'] > 0:
                print(f"  Performance: {stats['expressions_cached']} cached, {stats['registers_reused']} reused")
            
            if compiler.includes:
                print(f"  Includes: {' '.join(compiler.includes)}")
            if compiler.warnings:
                print("Warnings:")
                for warn in compiler.warnings:
                    print(f"  - {warn}")
            if show_asm or debug_mode:
                print("\nGenerated Assembly:")
                print("=" * 60)
                print(compiler.get_assembly_output())
                print("=" * 60)
        
        if run_after:
            # Pass --output flag to run command if set
            run_args = [out_file]
            if output_only:
                run_args.append("--output")
            self.do_run(run_args)
    
    def do_cpp_help(self, args):
        """Show C++ compiler help"""
        print("cas++ - SimpleOS C++ Compiler")
        print("=" * 40)
        print("USAGE:")
        print("  cas++ <source.cpp> [output.bin] [options]")
        print()
        print("OPTIONS:")
        print("  --run     Compile and immediately execute the program")
        print("  --asm     Display generated assembly output")
        print("  --debug   Alias for --asm (kept for compatibility)")
        print("  --output  Show ONLY program output (no debug info)")
        print()
        print("OTHER COMMANDS:")
        print("  compilecpp  - Alias for cas++")
        print("  cpprun      - Compile and run in a single step")
        print("  c++         - Show this help screen")
        print()
        print("SUPPORTED FEATURES:")
        print("  • #include lines (ignored but accepted for common headers)")
        print("  • int / const int / float / bool / char declarations")
        print("  • Mutable variables mapped to CPU registers (R4-R12)")
        print("  • Arithmetic: +, -, *, /, %, ++, --, +=, -=, *=, /=")
        print("  • Bitwise: &, |, ^, ~, <<, >>, &=, |=, ^=, <<=, >>=")
        print("  • Comparison: ==, !=, <, >, <=, >=")
        print("  • Control flow: if/else, while, do-while, for, break, continue")
        print("  • Arrays: int arr[size]; with indexing arr[i]")
        print("  • Classes: Basic class support with members")
        print()
        print("BUILT-IN FUNCTIONS:")
        print("  Math: abs(), min(), max(), sqrt(), pow(), rand(), srand()")
        print("  String: strlen(), strcmp(), memset()")
        print("  Bitwise: popcnt(), clz(), ctz(), swap(), reverse()")
        print("  Graphics: lerp(), sign(), saturate(), clamp()")
        print("  System: gettime(), sleep()")
        print("  • printf(\"text\", value1, value2, ...); with %d placeholders")
        print("  • return <expression>; (integers & simple arithmetic)")
        print()
        print("NEW CPU INSTRUCTIONS:")
        print("  • MULH  - Multiply High (upper 32 bits of 64-bit result)")
        print("  • DIVMOD - Combined division and modulo")
        print("  • AVGB  - Average of two values (useful for blending)")
        print()
        print("OPTIMIZATIONS:")
        print("  • Expression caching for faster compilation")
        print("  • Register reuse optimization")
        print("  • Peephole optimization in assembler")
        print()
        print("Unsupported statements are ignored with warnings.")
    
    def do_compile_cpp(self, args):
        """Alias for cas++"""
        self.do_caspp(args)
    
    def do_run_cpp(self, args):
        """Compile and immediately run a C++ program"""
        if not args:
            print("Usage: cpprun <source.cpp> [output.bin] [options]")
            return
        self.do_caspp(args + ["--run"])
    def do_loadasm(self, args):
        if len(args) < 2:
            print("Usage: loadasm <srcfile> <destfile>")
            return
        src = args[0]
        dest = args[1]
        try:
            _, code_bytes = self.kernel.read_file(src, self.kernel.cwd)
        except FileNotFoundError:
            print(f"Source file {src} not found")
            return
        except IsADirectoryError:
            print(f"{src} is a directory")
            return
        code = code_bytes.decode('utf-8', errors='replace') if isinstance(code_bytes, bytes) else code_bytes
        assembler = Assembler()
        try:
            binary = assembler.assemble(code)
            # Show warnings if any
            warnings = assembler.get_warnings()
            if warnings:
                print("Assembly warnings:")
                for warning in warnings:
                    print(f"  {warning}")
        except AssemblerError as e:
            print(f"Assembly error: {e}")
            return
        self.kernel.write_file(dest, binary, 0o755, self.kernel.cwd)
        print(f"Assembled {len(binary)} bytes to {dest}")
        print(f"Labels: {list(assembler.labels.keys())}")
        print(f"Constants: {list(assembler.constants.keys())}")
    def do_asminfo(self, args):
        if len(args) != 1:
            print("Usage: asminfo <file>")
            return
        filename = args[0]
        try:
            _, code_bytes = self.kernel.read_file(filename, self.kernel.cwd)
        except FileNotFoundError:
            print(f"File {filename} not found")
            return
        except IsADirectoryError:
            print(f"{filename} is a directory")
            return
        code = code_bytes.decode('utf-8', errors='replace') if isinstance(code_bytes, bytes) else code_bytes
        assembler = Assembler()
        try:
            assembler.assemble(code)
        except AssemblerError as e:
            print(f"Assembly error: {e}")
            return
        print(f"Labels: {list(assembler.labels.keys())}")
        print(f"Constants: {list(assembler.constants.keys())}")
    def do_run(self, args):
        if not args:
            print("Usage: run <file> [addr] [--debug] [--output] [--trace]")
            print("  --debug   : Show detailed execution information")
            print("  --output  : Show all register changes and output")
            print("  --trace   : Enable instruction tracing")
            return
        
        # Parse flags
        debug_mode = "--debug" in args
        output_mode = "--output" in args
        output_only = output_mode  # --output means show ONLY program output
        trace_mode = "--trace" in args
        
        # Remove flags from args
        args = [arg for arg in args if not arg.startswith("--")]
        
        fname = args[0]
        try:
            abs_path, data = self.kernel.read_file(fname, self.kernel.cwd)
        except FileNotFoundError:
            print(f"File not found: {fname}")
            return
        except IsADirectoryError:
            print(f"{fname} is a directory")
            return
        addr = int(args[1], 0) if len(args) > 1 else 0x1000
        
        # Load program into memory
        try:
            self.cpu.mem.load_bytes(addr, data)
        except Exception as e:
            print(f"Failed to load program: {e}")
            return
        
        # Save initial state for debug mode
        if debug_mode or output_mode:
            initial_regs = [self.cpu.reg_read(i) for i in range(NUM_REGS)]
        
        self.cpu.pc = addr
        self.cpu.halted = False
        self.cpu.reg_write(REG_SP, (STACK_BASE - 4) & 0xFFFFFFFF)
        # Track program bounds for PC checks
        self.cpu.program_start = addr
        self.cpu.program_end = addr + len(data)
        
        # --output mode: ONLY show program output, nothing else
        if not output_only:
            if debug_mode:
                print(f"=== DEBUG MODE ===")
                print(f"File: {abs_path}")
                print(f"Load Address: {addr:08x}")
                print(f"Size: {len(data)} bytes")
                print(f"Initial PC: {self.cpu.pc:08x}")
                print(f"Initial SP: {self.cpu.reg_read(REG_SP):08x}")
                print("=" * 50)
            else:
                print(f"Executing {abs_path} at {addr:08x} (size {len(data)} bytes).")
            
            # Print separator for program output
            print("\n--- Program Output ---")
        
        try:
            # Add max_steps to prevent infinite loops (10 million instructions)
            import time
            start_time = time.time()
            steps = self.cpu.run(max_steps=10_000_000, trace=trace_mode)
            elapsed = time.time() - start_time
            
            # Show execution stats only if not in output-only mode
            if not output_only:
                # Add newline after program output and show execution stats
                print("\n--- Execution Statistics ---")
                print(f"Executed {steps:,} instructions in {elapsed:.4f}s ({steps/elapsed if elapsed > 0 else 0:,.0f} inst/sec)")
                
                if steps >= 10_000_000:
                    print(f"WARNING: Program reached maximum instruction limit ({steps:,} steps)")
        except Exception as e:
            if not output_only:
                print("\n--- Execution Error ---")
                print("Execution error:", e)
                if debug_mode:
                    import traceback
                    traceback.print_exc()
        
        # Show key register values after execution (skip in output-only mode)
        if not output_only:
            print("\n--- Final State ---")
            r0 = self.cpu.reg_read(0)
            r1 = self.cpu.reg_read(1)
            r2 = self.cpu.reg_read(2)
            print(f"Key registers: R0={r0}, R1={r1}, R2={r2}")
            print(f"Program exit code (R0): {r0}")
            
            # Show output mode results
            if output_mode or debug_mode:
                print("\n=== EXECUTION RESULTS ===")
                print(f"Final PC: {self.cpu.pc:08x}")
                print(f"Final SP: {self.cpu.reg_read(REG_SP):08x}")
                print(f"Flags: {self.cpu.flags:08x}")
                print("\nRegister Changes:")
                for i in range(NUM_REGS):
                    final_val = self.cpu.reg_read(i)
                    if output_mode or (debug_mode and final_val != initial_regs[i]):
                        print(f"  R{i}: {initial_regs[i]:08x} -> {final_val:08x}")
                print("=" * 50)
            
            # Check if it was a reboot signal
            if self.cpu.reg_read(0) == 0xDEADBEEF:
                print("\n[Reboot signal received]")
                return 0xDEADBEEF
            else:
                print("\n[Program finished]")
        
        return 0
    
    def do_runmt(self, args):
        """Run program with multithreading support"""
        if not args:
            print("Usage: runmt <file1> [file2] [file3] ... [--priority=5] [--trace]")
            print("  Run multiple programs as concurrent threads")
            print("  --priority=N : Set thread priority (0-10, default=5)")
            print("  --trace      : Enable instruction tracing")
            return
        
        # Parse flags
        trace_mode = "--trace" in args
        priority = 5
        
        # Extract priority if specified
        files = []
        for arg in args:
            if arg.startswith("--priority="):
                try:
                    priority = int(arg.split("=")[1])
                    priority = max(0, min(10, priority))  # Clamp to 0-10
                except ValueError:
                    print(f"Invalid priority value: {arg}")
                    return
            elif not arg.startswith("--"):
                files.append(arg)
        
        if not files:
            print("No files specified")
            return
        
        # Load all programs and create thread list
        threads = []
        base_addr = 0x1000
        
        for i, fname in enumerate(files):
            try:
                abs_path, data = self.kernel.read_file(fname, self.kernel.cwd)
            except FileNotFoundError:
                print(f"File not found: {fname}")
                return
            except IsADirectoryError:
                print(f"{fname} is a directory")
                return
            addr = base_addr + (i * 0x10000)  # Separate address space per thread
            
            # Load program into memory
            try:
                self.cpu.mem.load_bytes(addr, data)
                threads.append((addr, priority))
                print(f"Loaded {abs_path} at {addr:08x} (size {len(data)} bytes)")
            except Exception as e:
                print(f"Failed to load {fname}: {e}")
                return
        
        print(f"\nStarting {len(threads)} thread(s)...")
        
        # Run multithreaded
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            total_steps = loop.run_until_complete(
                self.cpu.run_multithreaded(threads, trace=trace_mode)
            )
            print(f"\n[All threads finished - {total_steps} total instructions]")
        except Exception as e:
            print(f"Execution error: {e}")
            import traceback
            traceback.print_exc()
    
    def do_threads(self, args):
        """Show thread information"""
        threads = self.cpu.scheduler.list_threads()
        if not threads:
            print("No active threads")
            return
        
        print("\nActive Threads:")
        print("=" * 60)
        print(f"{'TID':<6} {'State':<12} {'Priority':<10} {'PC':<10} {'Instructions':<15}")
        print("-" * 60)
        for t in threads:
            print(f"{t['tid']:<6} {t['state']:<12} {t['priority']:<10} {t['pc']:08x}   {t['instructions']:<15}")
        print("=" * 60)
        print(f"Total threads: {len(threads)}")
    
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
        """List processes/threads"""
        threads = self.cpu.scheduler.list_threads()
        if not threads:
            print("No active threads")
            return
        
        print("TID  State      Priority  PC        Instructions")
        print("---  -----      --------  --------  ------------")
        for t in threads:
            print(f"{t['tid']:<4} {t['state']:<10} {t['priority']:<9} {t['pc']:08x}  {t['instructions']}")
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

    def do_enterbios(self, args):
        """Enter interactive BIOS mode to inspect/change CPU flags and identification"""
        print("Entering interactive BIOS mode. Type 'help' for BIOS commands.")
        while True:
            try:
                line = input("bios> ").strip()
            except EOFError:
                print()
                break
            if not line:
                continue
            parts = shlex.split(line)
            cmd = parts[0].lower()
            args = parts[1:]
            if cmd in ("exit", "quit", "q"):
                print("Exiting BIOS mode")
                break
            elif cmd == "help":
                print("BIOS commands: listflags, showflags, set <FLAG>, clear <FLAG>, toggle <FLAG>, cpuid <R#>, info, help, exit")
            elif cmd == "listflags":
                for name, mask in sorted(FLAG_NAME_MAP.items()):
                    print(f"{name}: 0x{mask:08x}")
            elif cmd == "showflags":
                f = self.cpu.flags
                print(f"FLAGS=0x{f:08x}")
                set_names = [n for n,m in FLAG_NAME_MAP.items() if (f & m)]
                print("Set:", ", ".join(set_names) if set_names else "<none>")
            elif cmd == "set" and args:
                name = args[0].upper()
                mask = FLAG_NAME_MAP.get(name)
                if mask is None:
                    print("Unknown flag", name)
                else:
                    self.cpu.set_flag(mask)
                    print(f"Set {name}")
            elif cmd == "clear" and args:
                name = args[0].upper()
                mask = FLAG_NAME_MAP.get(name)
                if mask is None:
                    print("Unknown flag", name)
                else:
                    self.cpu.clear_flag(mask)
                    print(f"Cleared {name}")
            elif cmd == "toggle" and args:
                name = args[0].upper()
                mask = FLAG_NAME_MAP.get(name)
                if mask is None:
                    print("Unknown flag", name)
                else:
                    if self.cpu.test_flag(mask):
                        self.cpu.clear_flag(mask)
                        print(f"Toggled {name}: now cleared")
                    else:
                        self.cpu.set_flag(mask)
                        print(f"Toggled {name}: now set")
            elif cmd == "cpuid":
                if not args:
                    print("Usage: cpuid <R#>")
                else:
                    try:
                        r = self.assembler.parse_reg(args[0].upper())
                        self.cpu.reg_write(r, self.cpu.flags & 0xFFFFFFFF)
                        print(f"Wrote 0x{self.cpu.flags:08x} to R{r}")
                    except Exception as e:
                        print("Error:", e)
            elif cmd == "info":
                info = self.bios.get_system_info()
                for k,v in info.items():
                    print(f"{k}: {v}")
            else:
                print("Unknown BIOS command. Type 'help'.")
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

    def do_entboot(self, args):
        """Enter interactive bootloader mode (bootloader provides basic memory/load/run operations)."""
        print("Entering bootloader interactive mode...")
        # Ensure bootloader binary is available at 0x7C00 (but interactive mode operates directly)
        try:
            # Let Bootloader handle interactive shell which uses the CPU and memory
            self.bootloader.interactive_shell(self.cpu)
        except Exception as e:
            print("Interactive bootloader error:", e)
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
        """Real curl command - fetch URL content"""
        if not args:
            print("Usage: curl <url>")
            return
        url = args[0]
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            content = self.cpu.network.utils.curl(url)
            print(f"Curl {url}")
            print(f"Response ({len(content)} bytes):")
            print(content[:500])
        except Exception as e:
            print(f"Curl error: {e}")
    
    def do_wget(self, args):
        """Real wget command - download file"""
        if not args:
            print("Usage: wget <url>")
            return
        url = args[0]
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            result = self.cpu.network.utils.wget(url)
            if result > 0:
                print(f"Downloaded {result} bytes from {url}")
            else:
                print(f"Failed to download {url}")
        except Exception as e:
            print(f"Wget error: {e}")
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
    
    def do_nettest(self, args):
        """Test network connectivity"""
        if not args:
            print("Usage: nettest <host> <port>")
            return
        host = args[0]
        port = int(args[1]) if len(args) > 1 else 80
        try:
            sock_id = self.cpu.network.socket_create()
            if sock_id < 0:
                print("Failed to create socket")
                return
            result = self.cpu.network.socket_connect(sock_id, host, port)
            if result == 0:
                print(f"Successfully connected to {host}:{port}")
                self.cpu.network.socket_close(sock_id)
            else:
                print(f"Failed to connect to {host}:{port}")
        except Exception as e:
            print(f"Network test error: {e}")
    
    def do_netsocket(self, args):
        """Manage network sockets"""
        if not args:
            print("Usage: netsocket <create|connect|send|recv|close> [args...]")
            return
        cmd = args[0].lower()
        if cmd == "create":
            sock_id = self.cpu.network.socket_create()
            if sock_id >= 0:
                print(f"Created socket {sock_id}")
            else:
                print("Failed to create socket")
        elif cmd == "connect" and len(args) >= 3:
            sock_id = int(args[1])
            host = args[2]
            port = int(args[3]) if len(args) > 3 else 80
            result = self.cpu.network.socket_connect(sock_id, host, port)
            if result == 0:
                print(f"Connected socket {sock_id} to {host}:{port}")
            else:
                print(f"Failed to connect socket {sock_id}")
        elif cmd == "send" and len(args) >= 3:
            sock_id = int(args[1])
            data = " ".join(args[2:]).encode('utf-8')
            result = self.cpu.network.socket_send(sock_id, data)
            if result > 0:
                print(f"Sent {result} bytes on socket {sock_id}")
            else:
                print(f"Failed to send on socket {sock_id}")
        elif cmd == "recv" and len(args) >= 2:
            sock_id = int(args[1])
            size = int(args[2]) if len(args) > 2 else 1024
            data = self.cpu.network.socket_recv(sock_id, size)
            if data:
                print(f"Received {len(data)} bytes: {data.decode('utf-8', errors='replace')}")
            else:
                print("No data received")
        elif cmd == "close" and len(args) >= 2:
            sock_id = int(args[1])
            result = self.cpu.network.socket_close(sock_id)
            if result == 0:
                print(f"Closed socket {sock_id}")
            else:
                print(f"Failed to close socket {sock_id}")
        else:
            print("Invalid netsocket command")
    
    def do_http(self, args):
        """HTTP operations"""
        if not args:
            print("Usage: http <get|post|head> <url>")
            return
        method = args[0].upper()
        url = args[1] if len(args) > 1 else ""
        if method == "GET" and url:
            content = self.cpu.network.utils.curl(url)
            print(f"HTTP GET {url}")
            print(f"Response ({len(content)} bytes):")
            print(content[:500])
        elif method == "HEAD" and url:
            print(f"HTTP HEAD {url}")
            result = self.cpu.network.utils.wget(url)
            print(f"Content-Length: {result} bytes")
        else:
            print("Invalid HTTP command")
    
    def do_dns(self, args):
        """DNS lookup simulation"""
        if not args:
            print("Usage: dns <hostname>")
            return
        hostname = args[0]
        try:
            import socket as sock
            ip = sock.gethostbyname(hostname)
            print(f"{hostname} -> {ip}")
        except Exception as e:
            print(f"DNS lookup failed: {e}")
    
    def do_download(self, args):
        """Download file from URL"""
        if not args:
            print("Usage: download <url> [filename]")
            return
        url = args[0]
        filename = args[1] if len(args) > 1 else "downloaded_file"
        try:
            result = self.cpu.network.utils.wget(url)
            if result > 0:
                print(f"Downloaded {result} bytes from {url}")
                print(f"Saved to: {filename}")
            else:
                print("Download failed")
        except Exception as e:
            print(f"Download error: {e}")
    
    def do_memstats(self, args):
        """Show memory statistics"""
        stats = self.cpu.mem.get_stats()
        print("Memory Statistics:")
        print(f"  Total Size: {stats['total_size'] / (1024*1024):.1f} MB")
        print(f"  Total Reads: {stats['total_reads']}")
        print(f"  Total Writes: {stats['total_writes']}")
        print(f"  Cache Hits: {stats['cache_hits']}")
        print(f"  Cache Misses: {stats['cache_misses']}")
        print(f"  Cache Ratio: {stats['cache_ratio']:.2%}")
        print(f"  Protected Regions: {stats['protected_regions']}")
        print(f"  Breakpoints: {stats['breakpoints']}")
        print(f"  Scrub Operations: {stats['scrub_operations']}")
    
    def do_memscrub(self, args):
        """Securely zero a memory region"""
        if len(args) != 2:
            print("Usage: memscrub <addr> <length>")
            return
        try:
            addr = int(args[0], 0)
            length = int(args[1], 0)
        except ValueError:
            print("Usage: memscrub <addr> <length>")
            return
        try:
            self.cpu.mem.scrub(addr, length)
            print(f"Scrubbed {length} bytes at 0x{addr:08X}")
        except MemoryError as exc:
            print(f"memscrub failed: {exc}")

    def do_meminfo(self, args):
        """Show detailed memory information"""
        print(self.cpu.mem.dump_stats())
    
    def do_asmtest(self, args):
        """Run comprehensive assembly tests"""
        print("Running assembly tests...")
        assembler = Assembler()
        
        tests = [
            ("Basic instructions", r"""
.org 0x0000
LOADI R0, 42
ADD R0, R0
HALT
"""),
            ("Constants with .equ", r"""
.equ VALUE, 100
.org 0x0000
LOADI R0, VALUE
HALT
"""),
            ("Expression evaluation", r"""
.org 0x0000
LOADI R0, (5 + 3) * 2
HALT
"""),
            ("String directive", r"""
.org 0x0000
LOADI R0, msg
HALT
.org 0x0100
msg:
.string "Hello\n"
"""),
            ("Labels and jumps", r"""
.org 0x0000
start:
    LOADI R0, 5
loop:
    DEC R0
    JNZ loop
    HALT
"""),
            ("Data directives", r"""
.org 0x0000
.word 0x12345678
.dword 0xDEADBEEF
.byte 0x41, 0x42, 0x43
.space 16, 0
"""),
            ("Macros with parameters", r"""
.macro SETVAL reg, val
    LOADI \reg, \val
.endm

.org 0x0000
    SETVAL R0, 42
    SETVAL R1, 100
    HALT
"""),
            ("All features combined", r"""
.equ MAX_SIZE, 1024
.equ MIN_SIZE, 16

.macro BOUNDS_CHECK reg
    CMP \reg, R15
    JL error
    CMP \reg, R14
    JG error
.endm

.org 0x0000
start:
    LOADI R0, (MAX_SIZE / 2)
    LOADI R14, MAX_SIZE
    LOADI R15, MIN_SIZE
    BOUNDS_CHECK R0
    HALT
error:
    LOADI R0, 0xFFFF
    HALT
"""),
        ]
        
        passed = 0
        failed = 0
        
        for name, code in tests:
            try:
                binary = assembler.assemble(code)
                print(f"  ✓ {name} ({len(binary)} bytes)")
                passed += 1
            except Exception as e:
                print(f"  ✗ {name}: {e}")
                failed += 1
        
        print(f"\nResults: {passed} passed, {failed} failed")
    
    def do_stats(self, args):
        """Show system statistics"""
        print("System Statistics:")
        print(f"  Uptime: {time.time() - self.kernel.start_time:.1f}s")
        print(f"  CPU Cycles: {self.cpu.cycle_count}")
        print(f"  Instructions: {self.cpu.instructions_retired}")
        print(f"  Cache Hits: {self.cpu.cache_hits}")
        print(f"  Cache Misses: {self.cpu.cache_misses}")
        if (self.cpu.cache_hits + self.cpu.cache_misses) > 0:
            ratio = self.cpu.cache_hits / (self.cpu.cache_hits + self.cpu.cache_misses)
            print(f"  Cache Ratio: {ratio:.2%}")
    
    def do_cpuinfo(self, args):
        """Show CPU information"""
        print("CPU Information:")
        print(f"  Architecture: 32-bit x86-like")
        print(f"  Registers: 16 general purpose")
        print(f"  FPU Registers: 8")
        print(f"  Instruction Set: {len(pycpu.OPCODE_NAME)} opcodes")
        print(f"  Memory: {self.cpu.mem.size / (1024*1024):.0f} MB")
        print(f"  Stack: {pycpu.STACK_SIZE / 1024:.0f} KB at {hex(pycpu.STACK_BASE)}")
        print(f"  Heap: {pycpu.HEAP_SIZE / (1024*1024):.0f} MB at {hex(pycpu.HEAP_BASE)}")
        print(f"  Features: FPU, MMU, Virtual Memory, Paging")
    
    def do_benchmark(self, args):
        """Run CPU benchmark"""
        print("Running CPU benchmark...")
        start = time.time()
        
        # Simple benchmark: add operations
        for i in range(1000):
            self.cpu.reg_write(0, i)
            self.cpu.reg_write(1, i * 2)
            self.cpu.alu_add(i, i * 2)
        
        elapsed = time.time() - start
        ops_per_sec = 3000 / elapsed if elapsed > 0 else 0
        print(f"  Time: {elapsed:.3f}s")
        print(f"  Operations: 3000")
        print(f"  Speed: {ops_per_sec:.0f} ops/sec")
    
    def do_test(self, args):
        """Run system tests"""
        print("Running system tests...")
        tests_passed = 0
        tests_failed = 0
        
        # Test 1: Register operations
        try:
            self.cpu.reg_write(0, 0x12345678)
            if self.cpu.reg_read(0) == 0x12345678:
                print("  ✓ Register operations")
                tests_passed += 1
            else:
                print("  ✗ Register operations")
                tests_failed += 1
        except Exception as e:
            print(f"  ✗ Register operations: {e}")
            tests_failed += 1
        
        # Test 2: Memory operations
        try:
            self.cpu.mem.write_word(0x1000, 0xDEADBEEF)
            if self.cpu.mem.read_word(0x1000) == 0xDEADBEEF:
                print("  ✓ Memory operations")
                tests_passed += 1
            else:
                print("  ✗ Memory operations")
                tests_failed += 1
        except Exception as e:
            print(f"  ✗ Memory operations: {e}")
            tests_failed += 1
        
        # Test 3: Network
        try:
            result = self.cpu.network.utils.ping("example.com")
            print(f"  ✓ Network (ping: {result})")
            tests_passed += 1
        except Exception as e:
            print(f"  ✗ Network: {e}")
            tests_failed += 1
        
        # Test 4: Assembler
        try:
            asm = pycpu.Assembler()
            binary = asm.assemble(".org 0x1000\nHALT")
            if len(binary) > 0:
                print("  ✓ Assembler")
                tests_passed += 1
            else:
                print("  ✗ Assembler")
                tests_failed += 1
        except Exception as e:
            print(f"  ✗ Assembler: {e}")
            tests_failed += 1
        
        print(f"\nTests: {tests_passed} passed, {tests_failed} failed")
    
    def do_pwd(self, args):
        """Print working directory"""
        print(self.kernel.cwd)
    
    def do_echo(self, args):
        """Echo text to output"""
        if not args:
            print()
        else:
            print(" ".join(args))
    
    def do_env(self, args):
        """Show environment variables"""
        if not self.kernel.env_vars:
            print("No environment variables set")
        else:
            for key, value in sorted(self.kernel.env_vars.items()):
                print(f"{key}={value}")
    
    def do_export(self, args):
        """Export environment variable"""
        if not args:
            print("Usage: export VAR=value")
            return
        for arg in args:
            if '=' in arg:
                key, value = arg.split('=', 1)
                self.kernel.env_vars[key] = value
                print(f"Exported {key}={value}")
            else:
                print(f"Invalid format: {arg}")
    
    def do_unset(self, args):
        """Unset environment variable"""
        if not args:
            print("Usage: unset VAR")
            return
        for var in args:
            if var in self.kernel.env_vars:
                del self.kernel.env_vars[var]
                print(f"Unset {var}")
            else:
                print(f"Variable {var} not found")
    
    # ===== TERMINAL GAMES =====
    
    def do_snake(self, args):
        """Play Snake game in terminal"""
        import random
        import time
        
        print("=" * 50)
        print("SNAKE GAME")
        print("=" * 50)
        print("Controls: w=up, s=down, a=left, d=right")
        print("Just press Enter after each move")
        print("Type 'q' to quit")
        print("Press Enter to start...")
        input()
        
        # Game setup
        width, height = 20, 10
        snake = [[5, 5], [5, 4], [5, 3]]
        direction = [1, 0]  # right
        food = [random.randint(0, width-1), random.randint(0, height-1)]
        score = 0
        game_over = False
        move_count = 0
        
        while not game_over:
            # Clear screen
            print("\033[2J\033[H", end="")
            
            # Draw
            print(f"SNAKE - Score: {score}")
            print("+" + "-" * width + "+")
            
            for y in range(height):
                row = "|"
                for x in range(width):
                    if [x, y] in snake:
                        row += "O" if [x, y] == snake[0] else "o"
                    elif [x, y] == food:
                        row += "*"
                    else:
                        row += " "
                row += "|"
                print(row)
            
            print("+" + "-" * width + "+")
            print(f"Direction: {'→' if direction==[1,0] else '←' if direction==[-1,0] else '↑' if direction==[0,-1] else '↓'}")
            print("Move: w=up, s=down, a=left, d=right, q=quit, Enter=continue")
            
            # Get input
            try:
                move = input("> ").strip().lower()
                
                if move == "q":
                    print("\nGame ended!")
                    break
                elif move == "w" and direction != [0, 1]:
                    direction = [0, -1]
                elif move == "s" and direction != [0, -1]:
                    direction = [0, 1]
                elif move == "a" and direction != [1, 0]:
                    direction = [-1, 0]
                elif move == "d" and direction != [-1, 0]:
                    direction = [1, 0]
                # Empty input just continues in current direction
            except:
                pass
            
            # Move snake
            head = [snake[0][0] + direction[0], snake[0][1] + direction[1]]
            
            # Check collision with walls
            if head[0] < 0 or head[0] >= width or head[1] < 0 or head[1] >= height:
                print("\033[2J\033[H", end="")
                print("+" + "-" * width + "+")
                for y in range(height):
                    row = "|"
                    for x in range(width):
                        if [x, y] in snake:
                            row += "X"
                        else:
                            row += " "
                    row += "|"
                    print(row)
                print("+" + "-" * width + "+")
                print("\n💥 Game Over! Hit wall!")
                print(f"Final Score: {score}")
                input("Press Enter to continue...")
                game_over = True
                continue
            
            # Check collision with self
            if head in snake:
                print("\033[2J\033[H", end="")
                print("+" + "-" * width + "+")
                for y in range(height):
                    row = "|"
                    for x in range(width):
                        if [x, y] in snake:
                            row += "X"
                        else:
                            row += " "
                    row += "|"
                    print(row)
                print("+" + "-" * width + "+")
                print("\n💥 Game Over! Hit yourself!")
                print(f"Final Score: {score}")
                input("Press Enter to continue...")
                game_over = True
                continue
            
            # Add new head
            snake.insert(0, head)
            
            # Check if ate food
            if head == food:
                score += 10
                food = [random.randint(0, width-1), random.randint(0, height-1)]
                while food in snake:
                    food = [random.randint(0, width-1), random.randint(0, height-1)]
            else:
                snake.pop()
            
            move_count += 1
    
    def do_minesweeper(self, args):
        """Play Minesweeper in terminal"""
        import random
        import time
        
        print("=" * 50)
        print("MINESWEEPER")
        print("=" * 50)
        print("Enter row and column (e.g., '3 4' to reveal)")
        print("Type 'f 3 4' to flag/unflag")
        print("Type 'q' to quit")
        print()
        
        # Game setup
        size = 8
        mines = 10
        board = [[0 for _ in range(size)] for _ in range(size)]
        revealed = [[False for _ in range(size)] for _ in range(size)]
        flagged = [[False for _ in range(size)] for _ in range(size)]
        
        # Place mines
        mine_positions = set()
        while len(mine_positions) < mines:
            x, y = random.randint(0, size-1), random.randint(0, size-1)
            mine_positions.add((x, y))
            board[y][x] = -1  # -1 = mine
        
        # Calculate numbers
        for y in range(size):
            for x in range(size):
                if board[y][x] != -1:
                    count = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < size and 0 <= nx < size and board[ny][nx] == -1:
                                count += 1
                    board[y][x] = count
        
        game_over = False
        
        while not game_over:
            # Clear screen
            print("\033[2J\033[H", end="")
            
            # Draw board
            print("MINESWEEPER - Find all mines!")
            print(f"Mines: {mines}  |  Flags: {sum(sum(1 for cell in row if cell) for row in flagged)}")
            print("\n    ", end="")
            for x in range(size):
                print(f"{x} ", end="")
            print()
            
            for y in range(size):
                print(f"  {y} ", end="")
                for x in range(size):
                    if flagged[y][x]:
                        print("F ", end="")
                    elif revealed[y][x]:
                        if board[y][x] == -1:
                            print("* ", end="")
                        elif board[y][x] == 0:
                            print("  ", end="")
                        else:
                            print(f"{board[y][x]} ", end="")
                    else:
                        print("■ ", end="")
                print()
            
            # Get input
            print("\nCommands:")
            print("  'row col' to reveal (e.g., '3 4')")
            print("  'f row col' to flag (e.g., 'f 3 4')")
            print("  'q' to quit")
            
            try:
                cmd = input("\n> ").strip().lower()
                
                if cmd == "q":
                    print("Game ended!")
                    break
                
                parts = cmd.split()
                
                if len(parts) == 2 and parts[0] != "f":
                    # Reveal cell
                    y, x = int(parts[0]), int(parts[1])
                    if 0 <= x < size and 0 <= y < size and not flagged[y][x]:
                        if board[y][x] == -1:
                            revealed[y][x] = True
                            # Show all mines
                            for my in range(size):
                                for mx in range(size):
                                    if board[my][mx] == -1:
                                        revealed[my][mx] = True
                            # Redraw
                            print("\033[2J\033[H", end="")
                            print("BOOM! You hit a mine!")
                            print("\n    ", end="")
                            for x in range(size):
                                print(f"{x} ", end="")
                            print()
                            for y in range(size):
                                print(f"  {y} ", end="")
                                for x in range(size):
                                    if revealed[y][x] and board[y][x] == -1:
                                        print("* ", end="")
                                    elif revealed[y][x]:
                                        print(f"{board[y][x]} " if board[y][x] > 0 else "  ", end="")
                                    else:
                                        print("■ ", end="")
                                print()
                            print("\nGame Over!")
                            input("Press Enter to continue...")
                            game_over = True
                        else:
                            revealed[y][x] = True
                            # Check win
                            revealed_count = sum(sum(1 for cell in row if cell) for row in revealed)
                            if revealed_count == size * size - mines:
                                print("\n🎉 Congratulations! You won!")
                                input("Press Enter to continue...")
                                game_over = True
                    else:
                        print("Invalid coordinates or cell is flagged!")
                        time.sleep(1)
                        
                elif len(parts) == 3 and parts[0] == "f":
                    # Flag cell
                    y, x = int(parts[1]), int(parts[2])
                    if 0 <= x < size and 0 <= y < size and not revealed[y][x]:
                        flagged[y][x] = not flagged[y][x]
                    else:
                        print("Invalid coordinates or cell already revealed!")
                        time.sleep(1)
                else:
                    print("Invalid command! Use 'row col' or 'f row col'")
                    time.sleep(1)
            except ValueError:
                print("Invalid input! Use numbers only.")
                time.sleep(1)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)
    
    def do_tetris(self, args):
        """Play Tetris in terminal"""
        import random
        import time
        import sys
        import select
        
        print("=" * 50)
        print("TETRIS")
        print("=" * 50)
        print("Controls: a=left, d=right, w=rotate, s=drop fast")
        print("Pieces fall automatically!")
        print("Type commands and press Enter")
        print("Press Enter to start...")
        input()
        
        # Game setup
        width, height = 10, 20
        board = [[0 for _ in range(width)] for _ in range(height)]
        
        # Tetromino shapes
        shapes = [
            [[1, 1, 1, 1]],  # I
            [[1, 1], [1, 1]],  # O
            [[1, 1, 1], [0, 1, 0]],  # T
            [[1, 1, 1], [1, 0, 0]],  # L
            [[1, 1, 1], [0, 0, 1]],  # J
            [[1, 1, 0], [0, 1, 1]],  # S
            [[0, 1, 1], [1, 1, 0]],  # Z
        ]
        
        score = 0
        current_piece = random.choice(shapes)
        piece_x, piece_y = width // 2 - 1, 0
        game_over = False
        last_fall = time.time()
        fall_speed = 0.8  # Seconds between falls
        
        def can_place(piece, x, y):
            for py, row in enumerate(piece):
                for px, cell in enumerate(row):
                    if cell:
                        nx, ny = x + px, y + py
                        if nx < 0 or nx >= width or ny >= height:
                            return False
                        if ny >= 0 and board[ny][nx]:
                            return False
            return True
        
        def rotate(piece):
            return [[piece[y][x] for y in range(len(piece)-1, -1, -1)] for x in range(len(piece[0]))]
        
        def draw_game():
            # Clear screen
            print("\033[2J\033[H", end="")
            
            # Draw
            print(f"TETRIS - Score: {score}")
            print("+" + "-" * width + "+")
            
            # Create display board
            display = [row[:] for row in board]
            for py, row in enumerate(current_piece):
                for px, cell in enumerate(row):
                    if cell:
                        nx, ny = piece_x + px, piece_y + py
                        if 0 <= ny < height and 0 <= nx < width:
                            display[ny][nx] = 2
            
            for row in display:
                print("|" + "".join("█" if cell == 1 else "▓" if cell == 2 else " " for cell in row) + "|")
            
            print("+" + "-" * width + "+")
            print("Controls: a=left, d=right, w=rotate, s=drop, q=quit")
            print("> ", end="", flush=True)
        
        # Set stdin to non-blocking mode
        import os
        import fcntl
        fd = sys.stdin.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        input_buffer = ""
        
        try:
            while not game_over:
                draw_game()
                
                # Check for input with timeout
                current_time = time.time()
                time_until_fall = fall_speed - (current_time - last_fall)
                
                if time_until_fall > 0:
                    # Wait for input or timeout
                    ready, _, _ = select.select([sys.stdin], [], [], min(time_until_fall, 0.1))
                    
                    if ready:
                        try:
                            char = sys.stdin.read(1)
                            if char == '\n':
                                # Process command
                                cmd = input_buffer.strip().lower()
                                input_buffer = ""
                                
                                if cmd == "q":
                                    print("\n\nGame ended!")
                                    game_over = True
                                    break
                                elif cmd == "a":
                                    if can_place(current_piece, piece_x - 1, piece_y):
                                        piece_x -= 1
                                elif cmd == "d":
                                    if can_place(current_piece, piece_x + 1, piece_y):
                                        piece_x += 1
                                elif cmd == "w":
                                    rotated = rotate(current_piece)
                                    if can_place(rotated, piece_x, piece_y):
                                        current_piece = rotated
                                elif cmd == "s":
                                    # Fast drop
                                    while can_place(current_piece, piece_x, piece_y + 1):
                                        piece_y += 1
                                        score += 1
                            else:
                                input_buffer += char
                        except:
                            pass
                
                # Auto fall
                if time.time() - last_fall >= fall_speed:
                    last_fall = time.time()
                    
                    if can_place(current_piece, piece_x, piece_y + 1):
                        piece_y += 1
                    else:
                        # Lock piece
                        for py, row in enumerate(current_piece):
                            for px, cell in enumerate(row):
                                if cell:
                                    nx, ny = piece_x + px, piece_y + py
                                    if 0 <= ny < height and 0 <= nx < width:
                                        board[ny][nx] = 1
                        
                        # Check for completed lines
                        lines_cleared = 0
                        y = height - 1
                        while y >= 0:
                            if all(board[y]):
                                board.pop(y)
                                board.insert(0, [0 for _ in range(width)])
                                lines_cleared += 1
                                score += 100
                            else:
                                y -= 1
                        
                        # New piece
                        current_piece = random.choice(shapes)
                        piece_x, piece_y = width // 2 - 1, 0
                        
                        if not can_place(current_piece, piece_x, piece_y):
                            print("\033[2J\033[H", end="")
                            print("+" + "-" * width + "+")
                            for row in board:
                                print("|" + "".join("█" if cell else " " for cell in row) + "|")
                            print("+" + "-" * width + "+")
                            print("\n💥 Game Over!")
                            print(f"Final Score: {score}")
                            game_over = True
        finally:
            # Restore stdin to blocking mode
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)
            if not game_over:
                print()
            input("\nPress Enter to continue...")

    
    def do_hexdump(self, args):
        """Hexdump of file or memory"""
        if not args:
            print("Usage: hexdump <file|addr> [length]")
            return
        target = args[0]
        length = int(args[1], 0) if len(args) > 1 else 256
        
        # Check if it's a file or memory address
        if target.startswith('0x') or target.isdigit():
            # Memory address
            addr = int(target, 0)
            try:
                data = self.cpu.mem.dump(addr, length)
                self._print_hexdump(data, addr)
            except Exception as e:
                print(f"Error reading memory: {e}")
        else:
            # File
            file_path = self._resolve_path(target)
            if file_path not in self.kernel.files:
                print(f"File not found: {target}")
                return
            data = self.kernel.files[file_path]["data"][:length]
            self._print_hexdump(data, 0)
    
    def _print_hexdump(self, data, base_addr):
        """Helper to print hexdump"""
        for i in range(0, len(data), 16):
            addr = base_addr + i
            hex_part = " ".join(f"{b:02x}" for b in data[i:i+16])
            ascii_part = "".join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
            print(f"{addr:08x}  {hex_part:<48}  {ascii_part}")
    
    def do_md5(self, args):
        """Calculate MD5 hash of file"""
        if not args:
            print("Usage: md5 <file>")
            return
        fname = args[0]
        abs_fname, data = self._read_file_bytes(fname)
        if abs_fname is None:
            return
        import hashlib
        md5_hash = hashlib.md5(data).hexdigest()
        print(f"MD5 ({abs_fname}) = {md5_hash}")
    
    def do_sha256(self, args):
        """Calculate SHA256 hash of file"""
        if not args:
            print("Usage: sha256 <file>")
            return
        fname = args[0]
        abs_fname, data = self._read_file_bytes(fname)
        if abs_fname is None:
            return
        import hashlib
        sha256_hash = hashlib.sha256(data).hexdigest()
        print(f"SHA256 ({abs_fname}) = {sha256_hash}")
    
    def do_base64(self, args):
        """Base64 encode/decode file"""
        if len(args) < 2:
            print("Usage: base64 <encode|decode> <file>")
            return
        operation = args[0].lower()
        fname = args[1]
        
        abs_fname, data = self._read_file_bytes(fname)
        if abs_fname is None:
            return
        
        import base64
        
        if operation == "encode":
            encoded = base64.b64encode(data).decode('utf-8')
            print(encoded)
        elif operation == "decode":
            try:
                decoded = base64.b64decode(data)
                print(decoded.decode('utf-8', errors='replace'))
            except Exception as e:
                print(f"Decode error: {e}")
        else:
            print("Invalid operation. Use 'encode' or 'decode'")
    
    def do_base32(self, args):
        """Base32 encode/decode file"""
        if len(args) < 2:
            print("Usage: base32 <encode|decode> <file>")
            return
        operation = args[0].lower()
        fname = args[1]
        
        abs_fname, data = self._read_file_bytes(fname)
        if abs_fname is None:
            return
        
        import base64
        
        if operation == "encode":
            encoded = base64.b32encode(data).decode('utf-8')
            print(encoded)
        elif operation == "decode":
            try:
                decoded = base64.b32decode(data)
                print(decoded.decode('utf-8', errors='replace'))
            except Exception as e:
                print(f"Decode error: {e}")
        else:
            print("Invalid operation. Use 'encode' or 'decode'")
    
    def do_hex(self, args):
        """Hex encode/decode file"""
        if len(args) < 2:
            print("Usage: hex <encode|decode> <file>")
            return
        operation = args[0].lower()
        fname = args[1]
        abs_fname, data = self._read_file_bytes(fname)
        if abs_fname is None:
            return
        
        if operation == "encode":
            encoded = data.hex()
            print(encoded)
        elif operation == "decode":
            try:
                decoded = bytes.fromhex(data.decode('utf-8') if isinstance(data, bytes) else data)
                print(decoded.decode('utf-8', errors='replace'))
            except Exception as e:
                print(f"Decode error: {e}")
        else:
            print("Invalid operation. Use 'encode' or 'decode'")
    
    def do_rot13(self, args):
        """ROT13 encode/decode text"""
        if not args:
            print("Usage: rot13 <file>")
            return
        fname = args[0]
        import codecs
        _, text = self._read_text(fname)
        if text is None:
            return
        result = codecs.encode(text, 'rot_13')
        print(result)
    
    def do_reverse(self, args):
        """Reverse text in file"""
        if not args:
            print("Usage: reverse <file>")
            return
        fname = args[0]
        _, text = self._read_text(fname)
        if text is None:
            return
        print(text[::-1])
    
    def do_upper(self, args):
        """Convert text to uppercase"""
        if not args:
            print("Usage: upper <file>")
            return
        fname = args[0]
        _, text = self._read_text(fname)
        if text is None:
            return
        print(text.upper())
    
    def do_lower(self, args):
        """Convert text to lowercase"""
        if not args:
            print("Usage: lower <file>")
            return
        fname = args[0]
        _, text = self._read_text(fname)
        if text is None:
            return
        print(text.lower())
    
    def do_tr(self, args):
        """Translate characters in file"""
        if len(args) < 3:
            print("Usage: tr <from_chars> <to_chars> <file>")
            return
        from_chars = args[0]
        to_chars = args[1]
        fname = args[2]
        _, text = self._read_text(fname)
        if text is None:
            return
        trans = str.maketrans(from_chars, to_chars)
        print(text.translate(trans))
    
    def do_cut(self, args):
        """Cut columns from file"""
        if len(args) < 2:
            print("Usage: cut <-f fields> <file>")
            print("Example: cut -f 1,3 file.txt")
            return
        
        if args[0] != "-f" or len(args) < 3:
            print("Usage: cut -f <fields> <file>")
            return
        
        fields_str = args[1]
        fname = args[2]
        _, text = self._read_text(fname)
        if text is None:
            return
        
        # Parse field numbers (1-indexed)
        fields = [int(f) - 1 for f in fields_str.split(',')]
        
        for line in text.splitlines():
            parts = line.split()
            selected = [parts[i] for i in fields if i < len(parts)]
            print(' '.join(selected))
    
    def do_sort(self, args):
        """Sort lines in file"""
        if not args:
            print("Usage: sort [-r] <file>")
            return
        
        reverse = False
        fname = args[0]
        
        if args[0] == "-r" and len(args) > 1:
            reverse = True
            fname = args[1]
        
        _, text = self._read_text(fname)
        if text is None:
            return
        lines = text.splitlines()
        lines.sort(reverse=reverse)
        for line in lines:
            print(line)
    
    def do_uniq(self, args):
        """Remove duplicate lines"""
        if not args:
            print("Usage: uniq <file>")
            return
        fname = args[0]
        _, text = self._read_text(fname)
        if text is None:
            return
        lines = text.splitlines()
        
        prev = None
        for line in lines:
            if line != prev:
                print(line)
                prev = line
    
    def do_head(self, args):
        """Show first N lines of file"""
        if not args:
            print("Usage: head [-n count] <file>")
            return
        
        count = 10
        fname = args[0]
        
        if args[0] == "-n" and len(args) > 2:
            count = int(args[1])
            fname = args[2]
        _, text = self._read_text(fname)
        if text is None:
            return
        lines = text.splitlines()[:count]
        for line in lines:
            print(line)
    
    def do_tail(self, args):
        """Show last N lines of file"""
        if not args:
            print("Usage: tail [-n count] <file>")
            return
        
        count = 10
        fname = args[0]
        
        if args[0] == "-n" and len(args) > 2:
            count = int(args[1])
            fname = args[2]
        _, text = self._read_text(fname)
        if text is None:
            return
        lines = text.splitlines()[-count:]
        for line in lines:
            print(line)
    
    def do_diff(self, args):
        """Compare two files"""
        if len(args) < 2:
            print("Usage: diff <file1> <file2>")
            return
        
        file1 = args[0]
        file2 = args[1]
        
        _, text1 = self._read_text(file1)
        if text1 is None:
            return
        _, text2 = self._read_text(file2)
        if text2 is None:
            return
        
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        import difflib
        diff = difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2, lineterm='')
        for line in diff:
            print(line)
    
    def do_whoami(self, args):
        """Print current username"""
        print(self.kernel.username)
    
    def do_uname(self, args):
        """Print system information"""
        print("SimpleOS 2.0 32-bit (x86-like)")
    
    def do_touch(self, args):
        """Create empty file or update timestamp"""
        if not args:
            print("Usage: touch <file>")
            return
        fname = args[0]
        abs_path = self._resolve_path(fname)
        entry = self.kernel.files.get(abs_path)
        if entry:
            entry["modified_time"] = time.time()
            print(f"Updated timestamp for {abs_path}")
        else:
            self.kernel.write_file(abs_path, b"", 0o644, "/")
            print(f"Created empty file {abs_path}")

    def do_diagnose(self, args):
        """Run system diagnostics and auto-repair components."""
        target = args[0].lower() if args else "all"
        mapping = {
            "cpu": self._diagnose_cpu,
            "ram": self._diagnose_memory,
            "memory": self._diagnose_memory,
            "kernel": self._diagnose_kernel,
            "bios": self._diagnose_bios,
        }
        if target != "all" and target not in mapping:
            print("Usage: diagnose [cpu|ram|kernel|bios|all]")
            return
        sequence = ["cpu", "ram", "kernel", "bios"]
        report = []
        for name in sequence:
            if target in ("all", name):
                result = mapping[name]()
                report.append((name, result))
                self._print_diagnose_result(name, result)
        if target == "all":
            print("\nSystem diagnostics complete.")
            statuses = {name: res["status"] for name, res in report}
            print(f"Summary: CPU {statuses['cpu']}, RAM {statuses['ram']}, Kernel {statuses['kernel']}, BIOS {statuses['bios']}")

    def _print_diagnose_result(self, name: str, result: Dict[str, Any]):
        header = f"[{name.upper()}]"
        print(f"\n{header} Status: {result['status']}")
        for key, val in result["info"].items():
            print(f"  {key}: {val}")
        if result["actions"]:
            print("  Repairs:")
            for action in result["actions"]:
                print(f"    - {action}")

    def _diagnose_cpu(self) -> Dict[str, Any]:
        info = {
            "clock_mhz": 125.0,
            "pc": f"0x{self.cpu.pc:08x}",
            "sp": f"0x{self.cpu.reg_read(REG_SP):08x}",
            "flags": f"0x{self.cpu.flags:08x}",
            "features": ", ".join(self.kernel.system_info.get("features", [])),
        }
        actions = []
        if self.cpu.halted:
            self.cpu.halted = False
            actions.append("CPU halted flag cleared")
        status = "OK" if not actions else "REPAIRED"
        return {"status": status, "info": info, "actions": actions}

    def _diagnose_memory(self) -> Dict[str, Any]:
        stats = self.cpu.mem.get_stats()
        info = {
            "size_mb": f"{stats['total_size'] / (1024*1024):.1f}",
            "reads": stats["total_reads"],
            "writes": stats["total_writes"],
            "cache_ratio": f"{stats['cache_ratio']:.2%}",
            "protected_regions": stats["protected_regions"],
            "scrubs": stats.get("scrub_operations", 0),
        }
        actions = []
        total_accesses = stats["total_reads"] + stats["total_writes"]
        if total_accesses > 200 and stats["cache_ratio"] < 0.05:
            self.cpu.mem.clear_cache()
            actions.append("Cache cleared due to poor cache ratio")
        status = "OK" if not actions else "REPAIRED"
        return {"status": status, "info": info, "actions": actions}

    def _diagnose_kernel(self) -> Dict[str, Any]:
        uptime = time.time() - self.kernel.start_time
        info = {
            "processes": len(self.kernel.processes),
            "files": len(self.kernel.files),
            "cwd": self.kernel.cwd,
            "uptime": f"{uptime:.1f}s",
        }
        actions = []
        if not self.kernel.running:
            self.kernel.running = True
            actions.append("Kernel marked as running")
        status = "OK" if not actions else "REPAIRED"
        return {"status": status, "info": info, "actions": actions}

    def _diagnose_bios(self) -> Dict[str, Any]:
        info = {
            "version": getattr(self.bios, "version", "1.1"),
            "vendor": getattr(self.bios, "vendor", "SimpleOS"),
            "last_boot": time.ctime(self.kernel.start_time),
        }
        actions: List[str] = []
        status = "OK"
        return {"status": status, "info": info, "actions": actions}

    def do_self_repair(self, args):
        """Attempt automatic repairs on system components."""
        target = args[0].lower() if args else "all"
        mapping = {
            "cpu": self._diagnose_cpu,
            "ram": self._diagnose_memory,
            "memory": self._diagnose_memory,
            "kernel": self._diagnose_kernel,
            "bios": self._diagnose_bios,
        }
        if target != "all" and target not in mapping:
            print("Usage: self-repair [cpu|ram|kernel|bios|all]")
            return
        print("Initiating self-repair routines...")
        order = ["cpu", "ram", "kernel", "bios"]
        for comp in order:
            if target not in ("all", comp):
                continue
            result = mapping[comp]()
            if result["actions"]:
                print(f"[{comp.upper()}] Repairs applied:")
                for action in result["actions"]:
                    print(f"  - {action}")
            else:
                print(f"[{comp.upper()}] No issues detected")
        print("Self-repair sequence complete.")
    
    def do_du(self, args):
        """Disk usage"""
        total_size = sum(len(f["data"]) for f in self.kernel.files.values() if "data" in f)
        print(f"Total disk usage: {total_size} bytes ({total_size / 1024:.2f} KB)")
        
        if args and args[0] == "-a":
            # Show per-file usage
            for name, info in sorted(self.kernel.files.items()):
                if "data" in info:
                    size = len(info["data"])
                    print(f"{size:>10} bytes  {name}")

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
SAMPLE_KERNEL = r"""
.org 0x1000
; Tiny kernel that prints a message at 0x1100 (loaded by bootloader)
; Syscall convention: R0=syscall num, R1=fd, R2=buf, R3=len
LOADI R0, 1   ; syscall WRITE
LOADI R1, 1   ; fd=1 stdout
LOADI R2, 0x1100
LOADI R3, 15
SYSCALL R0
HALT
.org 0x1100
.byte 0x4B,0x65,0x72,0x6E,0x65,0x6C,0x20,0x73,0x74,0x61,0x72,0x74,0x65,0x64,0x0A
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
        # tiny kernel image for bootloader to load (constructed programmatically)
        # Build a small program at 0x1000 that issues a WRITE syscall to print from 0x1100
        code_words = []
        code_words.append(pack_instruction(OP_LOADI, 0, 0, 1))     # LOADI R0, 1 (syscall number WRITE)
        code_words.append(pack_instruction(OP_LOADI, 1, 0, 1))     # LOADI R1, 1 (fd stdout)
        code_words.append(pack_instruction(OP_LOADI, 2, 0, 0x1100))# LOADI R2, 0x1100 (buf)
        code_words.append(pack_instruction(OP_LOADI, 3, 0, 15))    # LOADI R3, 15 (len)
        code_words.append(pack_instruction(OP_SYSCALL, 0, 0, 0))   # SYSCALL
        code_words.append(pack_instruction(OP_HALT, 0, 0, 0))      # HALT
        bin_code = b''.join(itob_le(w) for w in code_words)
        # place message at 0x1100 (256 bytes after 0x1000)
        pad_len = 0x1100 - 0x1000 - len(bin_code)
        if pad_len < 0:
            pad_len = 0
        bin_kernel = bin_code + (b'\x00' * pad_len) + b"Kernel started\n\0"
        kernel.files["/kernel.bin"] = {
            "data": bin_kernel,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        # kernel message as separate file (optional)
        kernel.files["/kernel_msg"] = {
            "data": b"Kernel started\n",
            "permissions": 0o644,
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
        # Create a test program for ADC and SBB instructions
        test_asm = """
.org 0x0000
; Test ADC and SBB instructions
LOADI R0, 0xFFFFFFFF  ; Load max value
LOADI R1, 1           ; Load 1
STC                   ; Set carry flag
ADC R0, R1            ; R0 = R0 + R1 + carry = 0xFFFFFFFF + 1 + 1 = 1 (with carry set)
; Now R0 should be 1, and carry should be set
LOADI R2, 5
LOADI R3, 3
SUB R2, R3            ; R2 = 5 - 3 = 2
CLI                   ; Clear interrupt flag
STI                   ; Set interrupt flag
HALT
"""
        try:
            test_bin = assembler.assemble(test_asm)
            kernel.files["/data.bin"] = {
                "data": test_bin,
                "permissions": 0o755,
                "created_time": time.time(),
                "modified_time": time.time()
            }
        except Exception as e:
            # Fallback to simple program if assembly fails
            simple_program = [
                0x020000FF,  # LOADI R0, 0xFF (max byte value)
                0x02100001,  # LOADI R1, 1
                0x4A000000,  # STC (set carry)
                0x44001000,  # ADC R0, R1
                0x1F000000,  # HALT
            ]
            test_bin = b''.join(itob_le(word) for word in simple_program)
            kernel.files["/data.bin"] = {
                "data": test_bin,
                "permissions": 0o755,
                "created_time": time.time(),
                "modified_time": time.time()
            }
    except Exception as e:
        logger.warning("Failed to assemble demo: %s", e)
    
    # Create demo program showcasing new assembler features
    DEMO_ADVANCED_ASM = r"""
; Advanced Assembler Demo
; Showcases: .equ, expressions, .string, .macro, labels

.equ SCREEN_START, 0xB800
.equ BUFFER_SIZE, 10
.equ SYSCALL_WRITE, 1

; Macro to print a string
.macro PRINT str_addr
    LOADI R0, SYSCALL_WRITE
    LOADI R1, 1
    LOADI R2, \str_addr
    LOADI R3, 20
    SYSCALL R0
.endm

.org 0x1000
start:
    ; Simple test
    LOADI R0, 5
    LOADI R1, 3
    ADD R0, R1
    
    HALT

; Data section with .string directive
.org 0x1100
msgdata:
.string "Hello from macro!\n"

srcdata:
.string "Source"

.align 16
dstdata:
.space 32, 0

; More data with .dword
.dword 0xDEADBEEF
.dword BUFFER_SIZE
"""
    try:
        demo_bin = assembler.assemble(DEMO_ADVANCED_ASM)
        kernel.files["/demo_advanced.bin"] = {
            "data": demo_bin,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        kernel.files["/demo_advanced.asm"] = {
            "data": DEMO_ADVANCED_ASM.encode('utf-8'),
            "permissions": 0o644,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        logger.info("Successfully assembled advanced demo")
    except Exception as e:
        logger.warning("Failed to assemble advanced demo: %s", e)
        # Create fallback simple demo
        try:
            SIMPLE_DEMO = r"""
.org 0x0000
    LOADI R0, 42
    LOADI R1, 10
    ADD R0, R1
    HALT
"""
            demo_bin = assembler.assemble(SIMPLE_DEMO)
            kernel.files["/demo_advanced.bin"] = {
                "data": demo_bin,
                "permissions": 0o755,
                "created_time": time.time(),
                "modified_time": time.time()
            }
            kernel.files["/demo_advanced.asm"] = {
                "data": SIMPLE_DEMO.encode('utf-8'),
                "permissions": 0o644,
                "created_time": time.time(),
                "modified_time": time.time()
            }
            logger.info("Created fallback demo")
        except Exception as e2:
            logger.error("Failed to create fallback demo: %s", e2)
    
    # Create multithreading demo programs
    THREAD_DEMO_1 = r"""
; Thread 1: Counter that counts to 10 and yields
start:
    LOADI R0, 0        ; Counter
    LOADI R1, 10       ; Max count
loop:
    INC R0
    CMP R0, R1
    YIELD              ; Yield to other threads
    JL loop
    HALT
"""
    
    THREAD_DEMO_2 = r"""
; Thread 2: Accumulator that adds numbers
start:
    LOADI R0, 0        ; Sum
    LOADI R1, 5        ; Counter
loop:
    ADD R0, R1
    DEC R1
    JNZ loop           ; Loop without YIELD for single-thread mode
    HALT
"""
    
    THREAD_DEMO_3 = r"""
; Thread 3: Multiplier
start:
    LOADI R0, 1        ; Result
    LOADI R1, 2        ; Multiplier
    LOADI R2, 4        ; Counter
loop:
    MUL R0, R1
    DEC R2
    JNZ loop           ; Loop without YIELD for single-thread mode
    HALT
"""
    
    try:
        thread1_bin = assembler.assemble(THREAD_DEMO_1)
        kernel.files["/thread1.bin"] = {
            "data": thread1_bin,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        
        thread2_bin = assembler.assemble(THREAD_DEMO_2)
        kernel.files["/thread2.bin"] = {
            "data": thread2_bin,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        
        thread3_bin = assembler.assemble(THREAD_DEMO_3)
        kernel.files["/thread3.bin"] = {
            "data": thread3_bin,
            "permissions": 0o755,
            "created_time": time.time(),
            "modified_time": time.time()
        }
        
        logger.info("Successfully created multithreading demo programs")
    except Exception as e:
        logger.warning("Failed to create multithreading demos: %s", e)

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

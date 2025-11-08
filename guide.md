# SimpleOS: The Complete Guide

## Introduction to SimpleOS

SimpleOS is a lightweight, educational operating system designed to demonstrate fundamental operating system concepts while remaining simple enough to understand completely. This guide provides comprehensive documentation for developers working with SimpleOS.

### Key Features
- 32-bit RISC-like architecture with 16 general-purpose registers
- Preemptive multitasking with process scheduling
- Virtual memory with demand paging
- In-memory filesystem with basic file operations
- Simple shell for system interaction
- Built-in debugger for system inspection

## System Architecture

### CPU Architecture

SimpleOS uses a 32-bit RISC architecture with the following key components:

#### Registers
- **General Purpose Registers (R0-R15)**
  - R0: Return value and first function argument
  - R1-R3: Function arguments
  - R4-R11: General purpose (callee-saved)
  - R12: Intra-procedure call temporary
  - R13 (SP): Stack pointer
  - R14 (LR): Link register
  - R15 (PC): Program counter

#### Memory Model
- **32-bit address space** (4GB)
- **Page size**: 4KB
- **Memory layout**:
  - 0x00000000-0x7FFFFFFF: User space
  - 0x80000000-0xFFFFFFFF: Kernel space

### Memory Management

SimpleOS implements a virtual memory system with the following features:
- Demand paging
- Page replacement using LRU algorithm
- Memory protection
- Memory-mapped I/O

### Process Management

- **Process States**:
  - NEW: Process being created
  - READY: Ready to run
  - RUNNING: Currently executing
  - WAITING: Waiting for I/O
  - TERMINATED: Finished execution

- **Scheduling**:
  - Priority-based round-robin scheduler
  - Time quantum: 10ms
  - Priority levels: 0 (highest) to 31 (lowest)

## Assembly Language Reference

### Instruction Set

#### Data Transfer
- `MOV Rd, Rs` - Move data between registers
- `LOAD Rd, [Rs + offset]` - Load from memory
- `STORE [Rd + offset], Rs` - Store to memory
- `PUSH Rs` - Push register onto stack
- `POP Rd` - Pop from stack to register

#### Arithmetic/Logical
- `ADD Rd, Rs1, Rs2` - Addition
- `SUB Rd, Rs1, Rs2` - Subtraction
- `MUL Rd, Rs1, Rs2` - Multiplication
- `DIV Rd, Rs1, Rs2` - Division
- `AND/OR/XOR/NOT` - Bitwise operations
- `SHL/SHR/SAR` - Shift operations

#### Control Flow
- `B label` - Unconditional branch
- `BEQ/BNE/BLT/BGT/BLE/BGE` - Conditional branches
- `CALL label` - Call subroutine
- `RET` - Return from subroutine
- `SYSCALL num` - Invoke system call
- `HALT` - Halt execution

### Addressing Modes
1. **Register Direct**: `MOV R1, R2`
2. **Immediate**: `LOADI R1, 42`
3. **Register Indirect**: `LOAD R1, [R2]`
4. **Base + Displacement**: `STORE [R1 + 0x100], R2`
5. **Indexed**: `LOAD R1, [R2 + R3 * 4]`
6. **PC-relative**: `B label`

## System Programming

### System Calls

System calls are the interface between user programs and the kernel. They are invoked using the `SYSCALL` instruction with the system call number in R0 and arguments in R1-R3.

#### Common System Calls

| #  | Name      | R1      | R2      | R3      | Description           |
|----|-----------|---------|---------|---------|-----------------------|
| 1  | EXIT      | status  | -       | -       | Terminate process     |
| 2  | FORK      | -       | -       | -       | Create new process    |
| 3  | READ      | fd      | buf     | count   | Read from file        |
| 4  | WRITE     | fd      | buf     | count   | Write to file         |
| 5  | OPEN      | path    | flags   | mode    | Open file             |
| 6  | CLOSE     | fd      | -       | -       | Close file            |
| 7  | EXECVE    | path    | argv    | envp    | Execute program       |
| 8  | WAITPID   | pid     | status  | options | Wait for process      |
| 9  | GETPID    | -       | -       | -       | Get process ID        |
| 10 | SBRK      | incr    | -       | -       | Change data segment   |

### Process Management API

#### Creating Processes
```c
// Fork the current process
pid_t fork(void);

// Execute a program
int execve(const char *pathname, char *const argv[], char *const envp[]);

// Wait for process to change state
pid_t waitpid(pid_t pid, int *status, int options);
```

#### Process Information
```c
// Get process ID
pid_t getpid(void);

// Get parent process ID
pid_t getppid(void);

// Get user ID
uid_t getuid(void);

// Get effective user ID
uid_t geteuid(void);
```

### File System API

#### File Operations
```c
// Open or create a file
int open(const char *pathname, int flags, mode_t mode);

// Read from a file
ssize_t read(int fd, void *buf, size_t count);

// Write to a file
ssize_t write(int fd, const void *buf, size_t count);

// Close a file
int close(int fd);

// Change file position
off_t lseek(int fd, off_t offset, int whence);
```

#### Directory Operations
```c
// Create a directory
int mkdir(const char *pathname, mode_t mode);

// Remove a directory
int rmdir(const char *pathname);

// Open a directory
DIR *opendir(const char *name);

// Read a directory entry
struct dirent *readdir(DIR *dirp);
```

## Advanced Topics

### Interrupts and Exceptions

#### Interrupt Vector Table
| Vector | Description          | Type       |
|--------|----------------------|------------|
| 0      | Division by zero     | Exception  |
| 1      | Debug                | Exception  |
| 2      | NMI                  | Interrupt  |
| 3      | Breakpoint           | Exception  |
| 4      | Overflow             | Exception  |
| 5-31   | Other exceptions     | Exception  |
| 32-255 | Hardware interrupts  | Interrupt  |

#### Handling Interrupts
```c
// Set interrupt handler
void set_interrupt_handler(int vector, void (*handler)());

// Enable/disable interrupts
void enable_interrupts(void);
void disable_interrupts(void);

// Wait for interrupt
void halt(void);
```

### Memory Management Unit (MMU)

#### Page Table Entry (PTE)
```
31    12 11 10 9 8 7 6 5 4 3 2 1 0
+------+--+--+-+-+ +-+-+ +-+-+-+
|  PFN |G |D |A|C|W|U|R|P|P|U|R|P|
+------+--+--+-+-+ +-+-+ +-+-+-+
```
- **P**: Present
- **R/W**: Read/Write
- **U/S**: User/Supervisor
- **PWT/PCD**: Cache control
- **A**: Accessed
- **D**: Dirty
- **G**: Global
- **PFN**: Page Frame Number

### Device Drivers

#### Driver Registration
```c
// Device operations structure
struct file_operations {
    int (*open)(struct inode *, struct file *);
    ssize_t (*read)(struct file *, char *, size_t, loff_t *);
    ssize_t (*write)(struct file *, const char *, size_t, loff_t *);
    int (*ioctl)(struct inode *, struct file *, unsigned int, unsigned long);
    int (*release)(struct inode *, struct file *);
};

// Register a character device
int register_chrdev(unsigned int major, const char *name,
                   const struct file_operations *fops);
```

## Development Tools

### Assembler

#### Command Line Options
```bash
simpleos-as [options] file.s
  -o FILE     Output file name
  -I DIR      Add include directory
  -D SYM[=VAL] Define symbol
  -g          Generate debug information
  -O LEVEL    Optimization level (0-3)
```

#### Example Assembly Program
```assembly
; hello.asm
.section .data
msg:    .string "Hello, World!\n"
len = . - msg

.section .text
.global _start
_start:
    ; Write message to stdout
    mov r0, #4          ; SYS_WRITE
    mov r1, #1          ; STDOUT
    ldr r2, =msg        ; Message address
    ldr r3, =len        ; Message length
    svc #0              ; Invoke syscall

    ; Exit with status 0
    mov r0, #0          ; Status code
    mov r7, #1          ; SYS_EXIT
    svc #0              ; Invoke syscall
```

### Debugger

#### Common Commands
```
break ADDR     Set breakpoint at address
run           Start execution
continue      Continue execution
step          Single step
next          Step over
print EXPR    Print expression value
x/NFU ADDR    Examine memory
info reg      Show registers
disassemble   Disassemble code
backtrace     Show call stack
```

### Emulator

#### Command Line Options
```bash
simpleos-emu [options] image
  -m SIZE     Memory size (e.g., 128M, 1G)
  -smp N      Number of CPUs
  -hda FILE   Hard disk image
  -cdrom FILE CD-ROM image
  -net TYPE   Network type (none, user, tap)
  -vga [std|cirrus|vmware|none]
  -nographic  Disable graphical output
  -s          Wait for gdb connection
  -S          Freeze CPU at startup
```

## Example Programs

### Hello World
```c
#include <unistd.h>

int main() {
    write(1, "Hello, World!\n", 14);
    return 0;
}
```

### Simple Shell
```c
#include <stdio.h>
#include <string.h>

#define MAX_LINE 80

int main() {
    char line[MAX_LINE];
    
    while (1) {
        printf("$ ");
        if (!fgets(line, MAX_LINE, stdin)) break;
        
        // Remove newline
        line[strcspn(line, "\n")] = 0;
        
        // Skip empty lines
        if (strlen(line) == 0) continue;
        
        // Handle commands
        if (strcmp(line, "exit") == 0) {
            break;
        } else if (strcmp(line, "help") == 0) {
            printf("Available commands: help, exit, echo\n");
        } else if (strncmp(line, "echo ", 5) == 0) {
            printf("%s\n", line + 5);
        } else {
            printf("Unknown command: %s\n", line);
        }
    }
    
    return 0;
}
```

## Performance Optimization

### Code Optimization
- Use register variables for frequently accessed data
- Minimize function call overhead with inline functions
- Optimize loops by reducing loop overhead
- Use appropriate data structures and algorithms
- Enable compiler optimizations (-O2 or -O3)

### Memory Optimization
- Minimize dynamic memory allocation
- Use stack allocation when possible
- Optimize data structure layout
- Use memory pools for fixed-size allocations
- Enable memory caching where appropriate

### I/O Optimization
- Use buffered I/O for small reads/writes
- Perform larger, less frequent I/O operations
- Use memory-mapped files for random access
- Implement asynchronous I/O for concurrent operations
- Use scatter/gather I/O when available

## Troubleshooting

### Common Issues

#### Program Crashes
- Check for null pointer dereferences
- Verify array bounds
- Ensure proper memory allocation/deallocation
- Check for stack overflow
- Validate function arguments

#### Performance Problems
- Profile the application to find bottlenecks
- Check for unnecessary I/O operations
- Look for inefficient algorithms
- Check for memory leaks
- Verify compiler optimizations are enabled

#### Build Issues
- Check for missing dependencies
- Verify include paths
- Check for undefined symbols
- Ensure proper library linking order
- Check for ABI compatibility

## Appendices

### A. System Limits
- Maximum file size: 2GB
- Maximum number of processes: 1024
- Maximum command line length: 4096 bytes
- Maximum environment size: 32KB
- Maximum open files per process: 1024

### B. Error Codes
| Code | Name           | Description                  |
|------|----------------|------------------------------|
| EPERM  | 1  | Operation not permitted      |
| ENOENT | 2  | No such file or directory   |
| EIO    | 5  | I/O error                   |
| ENOMEM | 12 | Out of memory               |
| EACCES | 13 | Permission denied            |
| EEXIST | 17 | File exists                 |
| EINVAL | 22 | Invalid argument             |
| ENOSPC | 28 | No space left on device     |

### C. Useful Resources
- [SimpleOS GitHub Repository](#)
- [Assembly Language Reference](#)
- [System Call Documentation](#)
- [Developer Forums](#)
- [Bug Tracker](#)

## Table of Contents
1. [Introduction to SimpleOS](#introduction-to-simpleos)
2. [System Architecture](#system-architecture)
   - [CPU Architecture](#cpu-architecture)
   - [Memory Management](#memory-management)
   - [Process Management](#process-management)
3. [Assembly Language Reference](#assembly-language-reference)
   - [Instruction Set](#instruction-set)
   - [Addressing Modes](#addressing-modes)
   - [Common Patterns](#common-patterns)
4. [System Programming](#system-programming)
   - [System Calls](#system-calls)
   - [Process Management](#process-management-api)
   - [File System](#file-system-api)
   - [Networking](#networking-api)
5. [Advanced Topics](#advanced-topics)
   - [Interrupts and Exceptions](#interrupts-and-exceptions)
   - [Memory Management Unit](#memory-management-unit)
   - [Device Drivers](#device-drivers)
6. [Development Tools](#development-tools)
   - [Assembler](#assembler)
   - [Debugger](#debugger)
   - [Emulator](#emulator)
7. [Example Programs](#example-programs)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)
10. [Appendices](#appendices)
8. [Assembly Programming](#assembly-programming)
9. [Advanced Features](#advanced-features)
10. [Troubleshooting](#troubleshooting)
11. [Examples](#examples)

## Introduction

SimpleOS is a lightweight, educational operating system designed to demonstrate fundamental OS concepts. It features a custom CPU emulator, virtual memory management, process scheduling, and a simple file system.

Key Features:
- 32-bit architecture with FPU and MMU support
- Preemptive multitasking
- In-memory filesystem
- System calls for I/O, process management, and more
- Built-in assembler
- Interactive shell

## Getting Started

To start SimpleOS:
```bash
python pycpu.py
```

## Basic Commands

### File Operations
- `ls` - List files in current directory
- `cat <file>` - Display file contents
- `echo <text>` - Print text to console
- `write <file> <text>` - Write text to file
- `rm <file>` - Remove a file
- `cp <src> <dest>` - Copy a file
- `mv <src> <dest>` - Move/rename a file
- `chmod <mode> <file>` - Change file permissions
- `mkdir <dir>` - Create a directory

### System Commands
- `whoami` - Show current user
- `ps` - List running processes
- `kill <pid>` - Terminate a process
- `clear` - Clear the screen
- `history` - Show command history
- `date` - Show current date
- `time` - Show current time
- `uptime` - Show system uptime
- `reboot` - Reboot the system

## File System Operations

SimpleOS uses an in-memory filesystem with the following structure:
- `/` - Root directory
- `/home` - User home directories
- `/bin` - System binaries

### File Permissions
Permissions are represented in octal format (e.g., 755):
- 4: Read
- 2: Write
- 1: Execute

Example: `chmod 755 script.bin`

## Process Management

### Creating Processes
Processes can be created using system calls or shell commands.

### Process States
- RUNNING: Currently executing
- READY: Ready to run
- WAITING: Waiting for I/O
- TERMINATED: Finished execution

### Process Commands
- `ps` - List processes
- `kill <pid>` - Terminate process
- `yield` - Yield CPU to next process

## System Information

### Hardware
- CPU: 32-bit with FPU and MMU
- Memory: Configurable (default 32MB)
- Storage: In-memory filesystem

### System Commands
- `sysinfo` - Show system information
- `biosinfo` - Show BIOS information
- `df` - Show disk usage
- `top` - Show process information

## Programming in SimpleOS

SimpleOS supports writing programs in assembly language. Programs can be assembled and executed directly in the shell.

### Creating a Program
1. Write your assembly code in a file with `.asm` extension
2. Assemble it using the built-in assembler
3. Run the program

## Assembly Programming

### Registers
- R0-R15: General purpose registers
- PC: Program counter
- SP: Stack pointer
- FLAGS: Status flags

### Instruction Set
- Data Movement: `MOV`, `LOAD`, `STORE`
- Arithmetic: `ADD`, `SUB`, `MUL`, `DIV`
- Logic: `AND`, `OR`, `XOR`, `NOT`
- Control Flow: `JMP`, `CALL`, `RET`, `CMP`, `JZ`, `JNZ`, `JL`, `JG`
- System: `SYSCALL`, `HALT`

### Example Program
```assembly
; Simple program that adds two numbers
LOADI R1, 5      ; Load immediate 5 into R1
LOADI R2, 3      ; Load immediate 3 into R2
ADD R0, R1, R2   ; R0 = R1 + R2
HALT             ; Halt execution
```

## Advanced Features

### System Calls
SimpleOS provides various system calls for interacting with the OS:
- File I/O (read, write, open, close)
- Process management (fork, exec, exit)
- Memory management (alloc, free)
- System information (time, date, uptime)

### Environment Variables
- `USER`: Current username
- `HOME`: User's home directory
- `PWD`: Current working directory

### Built-in Programs
- `hello.bin`: Simple hello world program
- `countdown.bin`: Countdown timer
- `float.bin`: Floating point demo
- `process.bin`: Process creation demo

## Troubleshooting

### Common Issues
1. **Program not found**: Check if the file exists and has execute permissions
2. **Permission denied**: Use `chmod` to change file permissions
3. **Out of memory**: Close unused programs or increase system memory
4. **Invalid instruction**: Check your assembly code for errors

### Debugging
- Use `step` to execute one instruction at a time
- Use `regs` to view register values
- Use `mem <addr> <len>` to inspect memory

## Examples

### Hello World
```assembly
; hello.asm
LOADI R0, 1           ; syscall 1 = WRITE
LOADI R1, 1           ; file descriptor 1 = stdout
LOADI R2, message     ; address of message
LOADI R3, 13          ; message length
SYSCALL R0            ; make system call
HALT                  ; exit

message:
.string "Hello, World!\n"
```

Assemble and run:
```
asm hello.asm hello.bin
run hello.bin
```

### File Operations
```assembly
; fileops.asm
; Create a file and write to it
LOADI R0, 7           ; syscall 7 = STORE_FILE
LOADI R1, filename    ; address of filename
LOADI R2, data        ; address of data
LOADI R3, datalen     ; length of data
SYSCALL R0            ; make system call
HALT

filename:
.string "/test.txt"
data:
.string "This is a test file.\n"
datalen = . - data
```

### Process Creation
```assembly
; process.asm
; Create a new process
LOADI R0, 11          ; syscall 11 = CREATE_PROCESS
LOADI R1, procname    ; address of process name
LOADI R2, 0x1000      ; entry point
LOADI R3, 4096        ; memory size
SYSCALL R0            ; make system call
HALT

procname:
.string "testproc"
```

### Floating Point Math
```assembly
; float.asm
; Calculate area of circle (πr²)
LOADI R0, 3.14159     ; π
LOADI R1, 5.0         ; radius
FMUL R0, R1           ; π * r
FMUL R0, R1           ; π * r * r
HALT
```

## Conclusion

SimpleOS provides a complete environment for learning about operating systems and low-level programming. With its simple yet powerful features, it's an excellent platform for experimentation and education.

For more information, refer to the source code and experiment with the built-in examples. Happy coding!

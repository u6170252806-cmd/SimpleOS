# 📚 Complete Tutorial - SimpleOS, Assembly & C++ Programming

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [SimpleOS Shell Commands](#simpleos-shell-commands)
4. [CPU Architecture](#cpu-architecture)
5. [Assembly Programming](#assembly-programming)
6. [C++ Programming](#c-programming)
7. [Complete Examples](#complete-examples)
8. [Advanced Topics](#advanced-topics)

---

## Introduction

Welcome to SimpleOS! This is a complete operating system emulator with:
- 32-bit CPU with 16 registers
- Memory management (64MB default)
- File system
- Shell with 50+ commands
- Assembly language support
- C++ compiler (cas++)
- Networking simulation
- Process management

---

## Getting Started

### Starting SimpleOS

```bash
python3 pycpu.py
```

You'll see:
```
==================================================
BIOS: Initializing system
BIOS Version: SimpleOS BIOS v1.1
Memory Size: 67108864 bytes (64 MB)
==================================================
Welcome to SimpleOS shell. Type 'help' for commands.
simpleos>
```

### Your First Command

```bash
simpleos> help
```

This shows all available command categories.

---

## SimpleOS Shell Commands

### System Commands

#### `help [category]`
Show available commands or help for a category.

```bash
simpleos> help              # Show categories
simpleos> help system       # Show system commands
simpleos> help file         # Show file commands
```

#### `whoami`
Show current user.

```bash
simpleos> whoami
root
```

#### `sysinfo`
Display system information.

```bash
simpleos> sysinfo
System: SimpleOS
CPU: 32-bit emulated
Memory: 64 MB
Uptime: 123 seconds
```

#### `uptime`
Show how long the system has been running.

```bash
simpleos> uptime
System uptime: 0 days, 0 hours, 2 minutes
```

#### `date` / `time`
Show current date and time.

```bash
simpleos> date
2024-01-15

simpleos> time
14:30:45
```

#### `reboot`
Restart the system.

```bash
simpleos> reboot
Rebooting system...
```

#### `clear` / `cls`
Clear the screen.

```bash
simpleos> clear
```

### File System Commands

#### `ls [-l] [path]`
List files and directories.

```bash
simpleos> ls                # List current directory
simpleos> ls -l             # Detailed listing
simpleos> ls /home          # List specific directory
```

#### `cd <directory>`
Change directory.

```bash
simpleos> cd /home
simpleos/home> cd ..
simpleos>
```

#### `pwd`
Print working directory.

```bash
simpleos/home> pwd
/home
```

#### `mkdir <directory>`
Create a directory.

```bash
simpleos> mkdir mydir
Directory created: /mydir
```

#### `cat <file>`
Display file contents.

```bash
simpleos> cat hello.txt
Hello, World!
```

#### `write <file> <text...>`
Write text to a file.

```bash
simpleos> write hello.txt Hello, World!
File written: /hello.txt
```

#### `nano <file>`
Edit a file (simple text editor).

```bash
simpleos> nano myfile.txt
# Opens editor, type content, Ctrl+D to save
```

#### `rm <file>`
Remove a file.

```bash
simpleos> rm oldfile.txt
File removed: /oldfile.txt
```

#### `cp <source> <dest>`
Copy a file.

```bash
simpleos> cp file1.txt file2.txt
File copied
```

#### `mv <source> <dest>`
Move/rename a file.

```bash
simpleos> mv old.txt new.txt
File moved
```

#### `stat <file>`
Show file information.

```bash
simpleos> stat hello.txt
File: /hello.txt
Size: 13 bytes
Type: file
Permissions: rw-r--r--
```

#### `chmod <mode> <file>`
Change file permissions.

```bash
simpleos> chmod 755 script.sh
Permissions changed
```

#### `touch <file>`
Create an empty file.

```bash
simpleos> touch newfile.txt
File created
```

#### `find <path> <pattern>`
Search for files.

```bash
simpleos> find / *.txt
/hello.txt
/readme.txt
```

### Text Processing Commands

#### `grep <pattern> <file>`
Search for text in a file.

```bash
simpleos> grep "hello" myfile.txt
Line 1: hello world
Line 5: say hello
```

#### `wc <file>`
Count lines, words, and characters.

```bash
simpleos> wc myfile.txt
Lines: 10, Words: 50, Chars: 250
```

#### `head <file> [n]`
Show first N lines (default 10).

```bash
simpleos> head myfile.txt 5
# Shows first 5 lines
```

#### `tail <file> [n]`
Show last N lines (default 10).

```bash
simpleos> tail myfile.txt 5
# Shows last 5 lines
```

### Programming Commands

#### `loadasm <source> <output>`
Assemble an assembly file.

```bash
simpleos> loadasm program.asm program.bin
Assembly successful: 48 bytes
```

#### `cas++ <source> [output] [--run] [--asm] [--debug]`
Compile C++ code.

```bash
simpleos> cas++ hello.cpp hello.bin
Compilation successful

simpleos> cas++ hello.cpp --run
# Compiles and runs immediately

simpleos> cas++ hello.cpp --asm
# Shows assembly output
```

#### `run <file> [addr]`
Execute a binary file.

```bash
simpleos> run program.bin
Program executed, return code: 0
```

### CPU & Memory Commands

#### `regs`
Display CPU registers.

```bash
simpleos> regs
R0:  0x00000000  R1:  0x00000000  R2:  0x00000000
R3:  0x00000000  R4:  0x00000000  R5:  0x00000000
...
PC:  0x00001000  SP:  0x03FF0000  FLAGS: 0x00000000
```

#### `memmap <addr> <len>`
Display memory contents.

```bash
simpleos> memmap 0x1000 64
0x1000: 02 00 00 2A 00 00 00 5B ...
```

#### `disasm <addr> [count]`
Disassemble memory.

```bash
simpleos> disasm 0x1000 10
0x1000: LOADI R0, 42
0x1004: SIGN R0
0x1008: HALT
```

### Process Commands

#### `ps`
List running processes.

```bash
simpleos> ps
PID  NAME        STATE    CPU%
1    init        running  0.5
2    shell       running  1.2
```

#### `kill <pid>`
Terminate a process.

```bash
simpleos> kill 123
Process 123 terminated
```

#### `top`
Show process information.

```bash
simpleos> top
# Shows real-time process stats
```

### Network Commands

#### `ping <host>`
Test network connectivity.

```bash
simpleos> ping google.com
Pinging google.com... Success!
```

#### `curl <url>`
Fetch URL content.

```bash
simpleos> curl http://example.com
# Shows page content
```

#### `wget <url>`
Download from URL.

```bash
simpleos> wget http://example.com/file.txt
Downloaded 1024 bytes
```

### Utility Commands

#### `calc <num1> <num2> <op>`
Perform calculation (1=add, 2=sub, 3=mul, 4=div).

```bash
simpleos> calc 10 5 1
Result: 15
```

#### `sleep <seconds>`
Delay for specified seconds.

```bash
simpleos> sleep 2
# Waits 2 seconds
```

#### `history`
Show command history.

```bash
simpleos> history
1: ls
2: cd /home
3: cat file.txt
```

#### `df`
Show disk usage.

```bash
simpleos> df
Filesystem: SimpleOS
Total: 1024 KB
Used: 256 KB
Free: 768 KB
```

#### `exit` / `quit`
Exit the shell.

```bash
simpleos> exit
Goodbye!
```

---

## CPU Architecture

### Registers

SimpleOS has a 32-bit CPU with 16 general-purpose registers:

| Register | Purpose | Usage |
|----------|---------|-------|
| R0 | Return value | Function return, syscall results |
| R1-R3 | Temporary | Calculations, syscall parameters |
| R4-R12 | Variables | C++ variable storage |
| R13 | Kernel | Reserved for kernel use |
| R14 (SP) | Stack Pointer | Points to top of stack |
| R15 (PC) | Program Counter | Current instruction address |

### Flags

The CPU has several status flags:

- **ZERO**: Set when result is zero
- **NEG**: Set when result is negative
- **CARRY**: Set on arithmetic carry
- **OVERFLOW**: Set on signed overflow
- **INTERRUPT**: Interrupt enable flag

### Memory Layout

```
0x00000000 - 0x00000FFF : Reserved
0x00001000 - 0x0FFFFFFF : Code segment
0x10000000 - 0x1FFFFFFF : Data segment
0x20000000 - 0x2FFFFFFF : Heap
0x30000000 - 0x3FEFFFFF : Stack
0x3FF00000 - 0x3FFFFFFF : Stack (grows down)
```

### Instruction Format

Instructions are 32-bit (4 bytes):

```
[Opcode: 8 bits][Dst: 4 bits][Src: 4 bits][Immediate: 16 bits]
```

---

## Assembly Programming

### Basic Syntax

```assembly
; Comments start with semicolon
LABEL:
    INSTRUCTION dst, src, imm
```

### Directives

#### `.org <address>`
Set code origin address.

```assembly
.org 0x1000
```

#### `.word <value>`
Define a 32-bit word.

```assembly
.word 0x12345678
```

#### `.string "<text>"`
Define a string.

```assembly
.string "Hello, World!"
```

### Basic Instructions

#### Data Movement

```assembly
; Load immediate value
LOADI R0, 42

; Move between registers
MOV R1, R0

; Load from memory
LOAD R2, R3        ; Load from address in R3

; Store to memory
STORE R1, R2       ; Store R1 to address in R2
```

#### Arithmetic

```assembly
; Addition
ADD R0, R1         ; R0 = R0 + R1
ADDI R0, 10        ; R0 = R0 + 10

; Subtraction
SUB R0, R1         ; R0 = R0 - R1
SUBI R0, 5         ; R0 = R0 - 5

; Multiplication
MUL R0, R1         ; R0 = R0 * R1

; Division
DIV R0, R1         ; R0 = R0 / R1

; Modulo
MOD R0, R1         ; R0 = R0 % R1
```

#### Logical Operations

```assembly
; Bitwise AND
AND R0, R1

; Bitwise OR
OR R0, R1

; Bitwise XOR
XOR R0, R1

; Bitwise NOT
NOT R0

; Shift left
SHL R0, R1

; Shift right
SHR R0, R1
```

#### Comparison & Branching

```assembly
; Compare
CMP R0, R1         ; Sets flags based on R0 - R1

; Jump
JMP label          ; Unconditional jump
JZ label           ; Jump if zero
JNZ label          ; Jump if not zero
JE label           ; Jump if equal
JNE label          ; Jump if not equal
JL label           ; Jump if less
JG label           ; Jump if greater
JLE label          ; Jump if less or equal
JGE label          ; Jump if greater or equal
```

#### Stack Operations

```assembly
; Push to stack
PUSH R0

; Pop from stack
POP R0

; Push flags
PUSHF

; Pop flags
POPF
```

#### Function Calls

```assembly
; Call function
CALL function_name

; Return from function
RET
```

#### System Calls

```assembly
; System call
SYSCALL R0         ; R0 contains syscall number
```

#### Special Instructions

```assembly
; No operation
NOP

; Halt CPU
HALT

; Increment
INC R0

; Decrement
DEC R0

; Negate
NEG R0

; Absolute value
ABS R0, R0
```

### New Instructions (Phase 2)

```assembly
; Linear interpolation
LERP R0, R1, 128   ; R0 = lerp(R0, R1, 0.5)

; Sign function
SIGN R0            ; R0 = sign(R0)

; Saturate to 0-255
SATURATE R0        ; R0 = clamp(R0, 0, 255)

; Rotate left
ROL R0, R1

; Rotate right
ROR R0, R1

; Byte swap
BSWAP R0

; Population count
POPCOUNT R0, R0
```

### Complete Assembly Example

```assembly
; Hello World Program
.org 0x1000

main:
    ; Print "Hello, World!"
    LOADI R0, 1              ; Syscall 1 = write
    LOADI R1, 1              ; File descriptor 1 = stdout
    LOADI R2, hello_msg      ; Address of string
    LOADI R3, 13             ; Length of string
    SYSCALL R0
    
    ; Exit
    LOADI R0, 0              ; Return code 0
    HALT

hello_msg:
    .string "Hello, World!"
```

### Assembly Example: Loop

```assembly
; Count from 1 to 10
.org 0x1000

main:
    LOADI R0, 1              ; Counter
    LOADI R1, 10             ; Limit
    
loop:
    ; Do something with R0
    INC R0
    CMP R0, R1
    JLE loop                 ; Continue if R0 <= R1
    
    HALT
```

### Assembly Example: Function

```assembly
; Function that adds two numbers
.org 0x1000

main:
    LOADI R0, 10
    LOADI R1, 20
    CALL add_numbers
    ; Result in R0
    HALT

add_numbers:
    PUSH R1
    ADD R0, R1
    POP R1
    RET
```

---

## C++ Programming

### Basic Syntax

```cpp
int main() {
    // Your code here
    return 0;
}
```

### Variables

```cpp
int main() {
    int x = 10;
    int y = 20;
    int sum = x + y;
    return sum;
}
```

### Constants

```cpp
int main() {
    const int MAX = 100;
    int value = 50;
    return value;
}
```

### Arrays

```cpp
int main() {
    // Declaration
    int arr[10];
    
    // Initialization
    int nums[5] = {1, 2, 3, 4, 5};
    
    // Access
    int first = nums[0];
    
    // Assignment
    nums[2] = 100;
    
    return first;
}
```

### Classes

```cpp
class Point {
    int x;
    int y;
};

class Player {
    int x;
    int y;
    int health;
};

int main() {
    // Classes are defined
    return 0;
}
```

### Control Flow

#### If Statements

```cpp
int main() {
    int x = 10;
    
    if (x > 5) {
        x = x + 1;
    }
    
    if (x == 11) {
        x = 100;
    } else {
        x = 0;
    }
    
    return x;
}
```

#### While Loops

```cpp
int main() {
    int i = 0;
    int sum = 0;
    
    while (i < 10) {
        sum = sum + i;
        i++;
    }
    
    return sum;
}
```

#### For Loops

```cpp
int main() {
    int sum = 0;
    
    for (int i = 0; i < 10; i++) {
        sum = sum + i;
    }
    
    return sum;
}
```

#### Do-While Loops

```cpp
int main() {
    int i = 0;
    
    do {
        i++;
    } while (i < 10);
    
    return i;
}
```

#### Break & Continue

```cpp
int main() {
    int i = 0;
    
    while (i < 100) {
        i++;
        
        if (i == 5) {
            continue;  // Skip to next iteration
        }
        
        if (i == 10) {
            break;     // Exit loop
        }
    }
    
    return i;
}
```

### Math Functions

```cpp
int main() {
    int x = abs(-42);          // Absolute value
    int m = min(10, 20);       // Minimum
    int M = max(10, 20);       // Maximum
    int s = sqrt(16);          // Square root
    int p = pow(2, 8);         // Power
    
    return x;
}
```

### Graphics Functions (NEW!)

```cpp
int main() {
    // Linear interpolation
    int color = lerp(0, 255, 128);  // 50% blend
    
    // Clamp to color range
    color = saturate(color);
    
    // Get direction
    int dir = sign(100 - 50);  // Returns 1
    
    return color;
}
```

### Bit Operations

```cpp
int main() {
    int x = 15;
    
    // Rotate
    int rotated = rotl(x, 4);
    
    // Count bits
    int bits = popcount(255);
    
    // Reverse bits
    int reversed = reverse(x);
    
    // Byte swap
    int swapped = bswap(0x1234);
    
    return bits;
}
```

### Timing & Random

```cpp
int main() {
    // Get timestamp
    int start = gettime();
    
    // Sleep
    sleep(100);  // 100 milliseconds
    
    // Random number
    int r = rand();
    
    // Hash
    int h = hash(42);
    
    return r;
}
```

### Inline Assembly

```cpp
int main() {
    int x = 10;
    
    // Inline assembly
    asm("NOP");
    asm("PUSH R4");
    asm("INC R4");
    asm("POP R4");
    
    return x;
}
```

### Printf

```cpp
int main() {
    printf("Hello, World!\n");
    printf("Number: %d\n", 42);
    return 0;
}
```

### Complete C++ Examples

#### Example 1: Array Sum

```cpp
int main() {
    int nums[10];
    int i = 0;
    
    // Initialize
    for (i = 0; i < 10; i++) {
        nums[i] = i + 1;
    }
    
    // Sum
    int sum = 0;
    for (i = 0; i < 10; i++) {
        sum = sum + nums[i];
    }
    
    return sum;  // Returns 55
}
```

#### Example 2: Color Fade

```cpp
int main() {
    int colors[10];
    int i = 0;
    
    // Fade from black to white
    for (i = 0; i < 10; i++) {
        int t = i * 25;
        colors[i] = lerp(0, 255, t);
        colors[i] = saturate(colors[i]);
    }
    
    return colors[5];
}
```

#### Example 3: Sprite Movement

```cpp
class Sprite {
    int x;
    int y;
};

int main() {
    int sprite_x = 50;
    int target_x = 150;
    
    // Calculate direction
    int dx = target_x - sprite_x;
    int dir = sign(dx);
    
    // Move sprite
    int speed = 5;
    sprite_x = sprite_x + dir * speed;
    
    return sprite_x;
}
```

---

## Complete Examples

### Example 1: Hello World (Assembly)

**File: hello.asm**
```assembly
.org 0x1000

main:
    LOADI R0, 1
    LOADI R1, 1
    LOADI R2, msg
    LOADI R3, 13
    SYSCALL R0
    HALT

msg:
    .string "Hello, World!"
```

**Commands:**
```bash
simpleos> write hello.asm ".org 0x1000..."
simpleos> loadasm hello.asm hello.bin
simpleos> run hello.bin
Hello, World!
```

### Example 2: Hello World (C++)

**File: hello.cpp**
```cpp
int main() {
    printf("Hello, World!\n");
    return 0;
}
```

**Commands:**
```bash
simpleos> write hello.cpp "int main() { printf..."
simpleos> cas++ hello.cpp hello.bin
simpleos> run hello.bin
Hello, World!
```

### Example 3: Game Loop

**File: game.cpp**
```cpp
class Player {
    int x;
    int y;
    int health;
};

int main() {
    int player_x = 50;
    int enemy_x = 100;
    int score = 0;
    
    printf("Game starting...\n");
    
    // Game loop
    int frame = 0;
    for (frame = 0; frame < 60; frame++) {
        // Calculate direction
        int dx = enemy_x - player_x;
        int dir = sign(dx);
        
        // Move player
        player_x = player_x + dir * 2;
        
        // Check collision
        int dist = abs(enemy_x - player_x);
        if (dist < 5) {
            score = score + 10;
        }
        
        // Frame delay
        sleep(16);  // ~60 FPS
    }
    
    printf("Game over!\n");
    printf("Final score: %d\n", score);
    
    return score;
}
```

**Commands:**
```bash
simpleos> nano game.cpp
# Write the code
simpleos> cas++ game.cpp game.bin --run
Game starting...
Game over!
Final score: 100
```

---

## Advanced Topics

### System Calls

System calls are accessed via the `SYSCALL` instruction:

| Number | Name | Parameters | Description |
|--------|------|------------|-------------|
| 1 | write | R1=fd, R2=addr, R3=len | Write to file |
| 2 | read | R1=fd, R2=addr, R3=len | Read from file |
| 3 | open | R1=path, R2=flags | Open file |
| 4 | close | R1=fd | Close file |
| 5 | exit | R1=code | Exit process |

### Memory Management

```assembly
; Allocate memory (syscall 9)
LOADI R0, 9
LOADI R1, 1024        ; Size in bytes
SYSCALL R0
; R0 now contains address

; Free memory (syscall 10)
LOADI R0, 10
MOV R1, R0            ; Address to free
SYSCALL R0
```

### Process Management

```assembly
; Fork process (syscall 11)
LOADI R0, 11
SYSCALL R0
; R0 = 0 in child, PID in parent

; Wait for process (syscall 12)
LOADI R0, 12
LOADI R1, pid
SYSCALL R0
```

### File I/O

```cpp
// In C++ (using syscalls)
int main() {
    // Files are accessed via shell commands
    // or direct syscalls in assembly
    return 0;
}
```

### Optimization Tips

1. **Use registers efficiently** - Max 9 variables in C++
2. **Reuse variables** in loops
3. **Use inline assembly** for critical code
4. **Minimize memory access** - Keep data in registers
5. **Use new opcodes** - LERP, SIGN, SATURATE are fast

### Debugging

```bash
# Show registers
simpleos> regs

# Disassemble code
simpleos> disasm 0x1000 20

# View memory
simpleos> memmap 0x2000 64

# Enable debug mode
simpleos> debug on

# Trace execution
simpleos> trace 0x1000 10
```

### Performance Profiling

```bash
# Time a command
simpleos> time run program.bin
Execution time: 0.123 seconds

# Show CPU usage
simpleos> top
```

---

## Quick Reference Card

### Essential Commands
```bash
help          # Show help
ls            # List files
cd <dir>      # Change directory
cat <file>    # View file
nano <file>   # Edit file
cas++ <file>  # Compile C++
run <file>    # Execute program
regs          # Show registers
exit          # Quit
```

### Essential Assembly
```assembly
LOADI R0, 42  # Load immediate
MOV R1, R0    # Move register
ADD R0, R1    # Add
CMP R0, R1    # Compare
JMP label     # Jump
CALL func     # Call function
RET           # Return
HALT          # Stop
```

### Essential C++
```cpp
int x = 10;              // Variable
int arr[5];              // Array
if (x > 5) { }           // If statement
for (int i=0; i<10; i++) // For loop
int y = abs(-10);        // Math function
int c = lerp(0,255,128); // Interpolation
asm("NOP");              // Inline assembly
printf("text\n");        // Print
```

---

## Troubleshooting

### Common Errors

**"File not found"**
→ Check file path with `ls` and `pwd`

**"Out of registers"**
→ Reduce number of variables in C++ code

**"Invalid instruction"**
→ Check assembly syntax

**"Segmentation fault"**
→ Check memory addresses

**"Compilation failed"**
→ Check C++ syntax, use `--debug` flag

### Getting Help

1. Use `help <category>` for command help
2. Check documentation files
3. Run diagnose all to test system
4. Use `debug on` for detailed execution

---

## Conclusion

You now know how to:
- ✅ Navigate SimpleOS
- ✅ Use shell commands
- ✅ Write assembly programs
- ✅ Write C++ programs
- ✅ Use new features (LERP, SIGN, SATURATE)
- ✅ Debug and optimize code

**Happy coding in SimpleOS!** 🚀

---

*For more information, see:*
- `coding.md` - Full coding guide 

*Version: 2.0*
*Last Updated: 2025*

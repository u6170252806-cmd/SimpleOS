# 💻 Complete Coding Guide - Assembly & C++ in SimpleOS

## 📚 Table of Contents

1. [Introduction](#introduction)
2. [Assembly Programming Guide](#assembly-programming-guide)
3. [C++ Programming Guide](#c-programming-guide)
4. [Running Programs](#running-programs)
5. [Complete Code Examples](#complete-code-examples)
6. [Advanced Techniques](#advanced-techniques)
7. [Debugging & Optimization](#debugging--optimization)

---

## Introduction

This guide provides detailed instructions for writing, compiling, and running both Assembly and C++ programs in SimpleOS.

### What You'll Learn
- ✅ Complete assembly instruction set
- ✅ All C++ features and syntax
- ✅ How to compile and run programs
- ✅ Real-world code examples
- ✅ Debugging techniques
- ✅ Performance optimization

---

## Assembly Programming Guide

### Getting Started with Assembly

Assembly is the lowest-level programming language in SimpleOS. Each instruction directly corresponds to a CPU operation.

### Basic Structure

```assembly
; Comments start with semicolon
.org 0x1000          ; Set code origin

main:                ; Label
    LOADI R0, 42     ; Load immediate
    HALT             ; Stop execution
```

### Complete Instruction Reference

#### 1. Data Movement Instructions

**LOADI - Load Immediate**
```assembly
LOADI R0, 42         ; R0 = 42
LOADI R1, -10        ; R1 = -10
LOADI R2, 0x100      ; R2 = 256 (hex)
```

**MOV - Move Register**
```assembly
MOV R1, R0           ; R1 = R0
MOV R2, R1           ; R2 = R1
```

**LOAD - Load from Memory**
```assembly
LOADI R1, 0x2000     ; R1 = address
LOAD R0, R1          ; R0 = memory[R1]

; Or with immediate address
LOAD R0, 0x2000      ; R0 = memory[0x2000]
```

**STORE - Store to Memory**
```assembly
LOADI R0, 42         ; Value to store
LOADI R1, 0x2000     ; Address
STORE R0, R1         ; memory[R1] = R0
```

**LOADB - Load Byte**
```assembly
LOADB R0, R1         ; Load byte from address in R1
```

**STOREB - Store Byte**
```assembly
STOREB R0, R1        ; Store byte to address in R1
```


#### 2. Arithmetic Instructions

**ADD - Addition**
```assembly
LOADI R0, 10
LOADI R1, 20
ADD R0, R1           ; R0 = R0 + R1 = 30
```

**ADDI - Add Immediate**
```assembly
LOADI R0, 10
ADDI R0, 5           ; R0 = R0 + 5 = 15
```

**SUB - Subtraction**
```assembly
LOADI R0, 30
LOADI R1, 10
SUB R0, R1           ; R0 = R0 - R1 = 20
```

**SUBI - Subtract Immediate**
```assembly
LOADI R0, 30
SUBI R0, 10          ; R0 = R0 - 10 = 20
```

**MUL - Multiplication**
```assembly
LOADI R0, 5
LOADI R1, 6
MUL R0, R1           ; R0 = R0 * R1 = 30
```

**DIV - Division**
```assembly
LOADI R0, 20
LOADI R1, 4
DIV R0, R1           ; R0 = R0 / R1 = 5
```

**MOD - Modulo**
```assembly
LOADI R0, 17
LOADI R1, 5
MOD R0, R1           ; R0 = R0 % R1 = 2
```

**INC - Increment**
```assembly
LOADI R0, 10
INC R0               ; R0 = R0 + 1 = 11
```

**DEC - Decrement**
```assembly
LOADI R0, 10
DEC R0               ; R0 = R0 - 1 = 9
```

**NEG - Negate**
```assembly
LOADI R0, 42
NEG R0               ; R0 = -R0 = -42
```

**ABS - Absolute Value**
```assembly
LOADI R0, -42
ABS R0, R0           ; R0 = |R0| = 42
```

#### 3. Logical & Bit Operations

**AND - Bitwise AND**
```assembly
LOADI R0, 0b1111
LOADI R1, 0b1010
AND R0, R1           ; R0 = 0b1010
```

**OR - Bitwise OR**
```assembly
LOADI R0, 0b1100
LOADI R1, 0b0011
OR R0, R1            ; R0 = 0b1111
```

**XOR - Bitwise XOR**
```assembly
LOADI R0, 0b1100
LOADI R1, 0b1010
XOR R0, R1           ; R0 = 0b0110
```

**NOT - Bitwise NOT**
```assembly
LOADI R0, 0b1010
NOT R0               ; R0 = ~R0
```

**SHL - Shift Left**
```assembly
LOADI R0, 1
LOADI R1, 4
SHL R0, R1           ; R0 = R0 << R1 = 16
```

**SHR - Shift Right**
```assembly
LOADI R0, 16
LOADI R1, 2
SHR R0, R1           ; R0 = R0 >> R1 = 4
```

**ROL - Rotate Left**
```assembly
LOADI R0, 0x0F
LOADI R1, 4
ROL R0, R1           ; Rotate R0 left by R1 bits
```

**ROR - Rotate Right**
```assembly
LOADI R0, 0xF0
LOADI R1, 4
ROR R0, R1           ; Rotate R0 right by R1 bits
```


#### 4. Comparison & Branching

**CMP - Compare**
```assembly
LOADI R0, 10
LOADI R1, 20
CMP R0, R1           ; Sets flags based on R0 - R1
```

**TEST - Test (AND without storing)**
```assembly
LOADI R0, 0b1010
LOADI R1, 0b0010
TEST R0, R1          ; Sets flags based on R0 & R1
```

**JMP - Unconditional Jump**
```assembly
JMP label            ; Jump to label
```

**JZ / JE - Jump if Zero/Equal**
```assembly
CMP R0, R1
JZ equal_label       ; Jump if R0 == R1
```

**JNZ / JNE - Jump if Not Zero/Not Equal**
```assembly
CMP R0, R1
JNZ not_equal        ; Jump if R0 != R1
```

**JL - Jump if Less**
```assembly
CMP R0, R1
JL less_label        ; Jump if R0 < R1
```

**JG - Jump if Greater**
```assembly
CMP R0, R1
JG greater_label     ; Jump if R0 > R1
```

**JLE - Jump if Less or Equal**
```assembly
CMP R0, R1
JLE le_label         ; Jump if R0 <= R1
```

**JGE - Jump if Greater or Equal**
```assembly
CMP R0, R1
JGE ge_label         ; Jump if R0 >= R1
```

#### 5. Stack Operations

**PUSH - Push to Stack**
```assembly
LOADI R0, 42
PUSH R0              ; Push R0 onto stack
```

**POP - Pop from Stack**
```assembly
POP R0               ; Pop from stack into R0
```

**PUSHF - Push Flags**
```assembly
PUSHF                ; Push flags register
```

**POPF - Pop Flags**
```assembly
POPF                 ; Pop into flags register
```

#### 6. Function Calls

**CALL - Call Function**
```assembly
CALL function_name   ; Call function
```

**RET - Return from Function**
```assembly
RET                  ; Return to caller
```

**Example Function:**
```assembly
main:
    LOADI R0, 10
    LOADI R1, 20
    CALL add_numbers
    HALT

add_numbers:
    PUSH R1
    ADD R0, R1       ; R0 = R0 + R1
    POP R1
    RET
```

#### 7. New Instructions (Phase 2)

**LERP - Linear Interpolation**
```assembly
LOADI R0, 0          ; Start value
LOADI R1, 100        ; End value
LERP R0, R1, 128     ; R0 = lerp(R0, R1, 0.5)
```

**SIGN - Sign Function**
```assembly
LOADI R0, -42
SIGN R0              ; R0 = -1 (negative)

LOADI R0, 42
SIGN R0              ; R0 = 1 (positive)

LOADI R0, 0
SIGN R0              ; R0 = 0 (zero)
```

**SATURATE - Clamp to 0-255**
```assembly
LOADI R0, 300
SATURATE R0          ; R0 = 255

LOADI R0, -10
SATURATE R0          ; R0 = 0

LOADI R0, 128
SATURATE R0          ; R0 = 128
```

**POPCOUNT - Count Set Bits**
```assembly
LOADI R0, 0xFF
POPCOUNT R0, R0      ; R0 = 8 (8 bits set)
```

**REVERSE - Reverse Bits**
```assembly
LOADI R0, 0x0F
REVERSE R0, R0       ; Reverse all 32 bits
```

**BSWAP - Byte Swap**
```assembly
LOADI R0, 0x1234
BSWAP R0             ; Reverse byte order
```


#### 8. System Calls

**SYSCALL - System Call**
```assembly
; Write to stdout (syscall 1)
LOADI R0, 1          ; Syscall number
LOADI R1, 1          ; File descriptor (stdout)
LOADI R2, msg        ; Address of string
LOADI R3, 13         ; Length
SYSCALL R0

msg:
    .string "Hello, World!"
```

#### 9. Special Instructions

**NOP - No Operation**
```assembly
NOP                  ; Do nothing (1 cycle)
```

**HALT - Stop Execution**
```assembly
HALT                 ; Stop CPU
```

### Complete Assembly Examples

#### Example 1: Hello World
```assembly
.org 0x1000

main:
    ; Print "Hello, World!"
    LOADI R0, 1
    LOADI R1, 1
    LOADI R2, hello_msg
    LOADI R3, 13
    SYSCALL R0
    HALT

hello_msg:
    .string "Hello, World!"
```

**How to run:**
```bash
simpleos> write hello.asm ".org 0x1000..."
simpleos> loadasm hello.asm hello.bin
simpleos> run hello.bin
Hello, World!
```

#### Example 2: Sum of Numbers
```assembly
.org 0x1000

main:
    LOADI R0, 0      ; Sum
    LOADI R1, 1      ; Counter
    LOADI R2, 10     ; Limit

loop:
    ADD R0, R1       ; Sum += counter
    INC R1           ; counter++
    CMP R1, R2
    JLE loop         ; Continue if counter <= limit
    
    HALT             ; R0 contains sum (55)
```

#### Example 3: Factorial
```assembly
.org 0x1000

main:
    LOADI R0, 5      ; Number to calculate
    CALL factorial
    HALT             ; R0 contains result (120)

factorial:
    ; Calculate factorial of R0
    PUSH R1
    PUSH R2
    
    MOV R1, R0       ; Save n
    LOADI R0, 1      ; Result = 1
    
fact_loop:
    CMP R1, 1
    JLE fact_done
    
    MUL R0, R1       ; Result *= n
    DEC R1           ; n--
    JMP fact_loop
    
fact_done:
    POP R2
    POP R1
    RET
```

#### Example 4: Array Operations
```assembly
.org 0x1000

main:
    ; Initialize array
    LOADI R0, 0      ; Index
    LOADI R1, array  ; Array address
    LOADI R2, 10     ; Count

init_loop:
    CMP R0, R2
    JGE init_done
    
    ; array[i] = i * 2
    MOV R3, R0
    LOADI R4, 2
    MUL R3, R4
    STORE R3, R1
    
    ; Next element
    INC R0
    ADDI R1, 4       ; Next word (4 bytes)
    JMP init_loop

init_done:
    HALT

array:
    .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
```

#### Example 5: Using New Opcodes
```assembly
.org 0x1000

main:
    ; Color interpolation
    LOADI R0, 0      ; Start color
    LOADI R1, 255    ; End color
    LERP R0, R1, 128 ; 50% blend
    SATURATE R0      ; Ensure 0-255
    
    ; Direction calculation
    LOADI R1, 100
    LOADI R2, 50
    SUB R1, R2       ; R1 = 50
    SIGN R1          ; R1 = 1 (positive)
    
    ; Bit operations
    LOADI R2, 0x0F
    LOADI R3, 4
    ROL R2, R3       ; Rotate left
    
    HALT
```

---

## C++ Programming Guide

### Getting Started with C++

The cas++ compiler supports a subset of C++ designed for system programming and game development.

### Basic Program Structure

```cpp
int main() {
    // Your code here
    return 0;
}
```

### Variables & Types

**Supported Types:**
- `int` - 32-bit integer
- `float` - Floating point (limited support)
- `bool` - Boolean
- `char` - Character

**Declaration:**
```cpp
int x;               // Declare
int y = 10;          // Declare and initialize
const int MAX = 100; // Constant
```

**Examples:**
```cpp
int main() {
    int a = 10;
    int b = 20;
    int sum = a + b;
    
    const int LIMIT = 100;
    
    return sum;
}
```


### Arrays

**Declaration:**
```cpp
int arr[10];                    // Declare array
int nums[5] = {1, 2, 3, 4, 5}; // Initialize
```

**Access & Assignment:**
```cpp
int main() {
    int arr[5] = {10, 20, 30, 40, 50};
    
    // Read element
    int first = arr[0];         // first = 10
    int third = arr[2];         // third = 30
    
    // Write element
    arr[1] = 100;               // arr[1] = 100
    arr[4] = 200;               // arr[4] = 200
    
    // Dynamic index
    int i = 2;
    int value = arr[i];         // value = 30
    arr[i] = 999;               // arr[2] = 999
    
    return first;
}
```

**Array in Loops:**
```cpp
int main() {
    int data[10];
    
    // Initialize
    int i = 0;
    for (i = 0; i < 10; i++) {
        data[i] = i * 10;
    }
    
    // Sum
    int sum = 0;
    for (i = 0; i < 10; i++) {
        sum = sum + data[i];
    }
    
    return sum;
}
```

### Classes

**Definition:**
```cpp
class Point {
    int x;
    int y;
};

class Player {
    int x;
    int y;
    int health;
    int score;
};

class Color {
    int r;
    int g;
    int b;
};
```

**Usage:**
```cpp
class Sprite {
    int x;
    int y;
    int active;
};

int main() {
    // Classes are defined at compile-time
    // Use variables to represent instances
    int sprite_x = 100;
    int sprite_y = 50;
    int sprite_active = 1;
    
    return sprite_x;
}
```

### Control Flow

**If Statements:**
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
    
    // Nested if
    if (x > 50) {
        if (x < 150) {
            x = 75;
        }
    }
    
    return x;
}
```

**Comparison Operators:**
- `==` - Equal
- `!=` - Not equal
- `>` - Greater than
- `<` - Less than
- `>=` - Greater or equal
- `<=` - Less or equal

**While Loops:**
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

**For Loops:**
```cpp
int main() {
    int sum = 0;
    
    for (int i = 0; i < 10; i++) {
        sum = sum + i;
    }
    
    return sum;
}
```

**Do-While Loops:**
```cpp
int main() {
    int i = 0;
    int sum = 0;
    
    do {
        sum = sum + i;
        i++;
    } while (i < 10);
    
    return sum;
}
```

**Break & Continue:**
```cpp
int main() {
    int sum = 0;
    
    for (int i = 0; i < 100; i++) {
        if (i == 5) {
            continue;  // Skip 5
        }
        
        if (i == 10) {
            break;     // Stop at 10
        }
        
        sum = sum + i;
    }
    
    return sum;
}
```

### Operators

**Arithmetic:**
```cpp
int a = 10 + 5;      // Addition
int b = 10 - 5;      // Subtraction
int c = 10 * 5;      // Multiplication
int d = 10 / 5;      // Division
int e = 10 % 3;      // Modulo
```

**Compound Assignment:**
```cpp
int x = 10;
x += 5;              // x = x + 5
x -= 3;              // x = x - 3
x *= 2;              // x = x * 2
x /= 4;              // x = x / 4
```

**Increment/Decrement:**
```cpp
int i = 0;
i++;                 // i = i + 1
i--;                 // i = i - 1
++i;                 // i = i + 1
--i;                 // i = i - 1
```

**Bitwise:**
```cpp
int a = 0b1100;
int b = 0b1010;

int c = a & b;       // AND
int d = a | b;       // OR
int e = a ^ b;       // XOR
int f = ~a;          // NOT
int g = a << 2;      // Shift left
int h = a >> 1;      // Shift right
```


### Built-in Functions

#### Math Functions

```cpp
int main() {
    // Basic math
    int a = abs(-42);           // Absolute value = 42
    int m = min(10, 20);        // Minimum = 10
    int M = max(10, 20);        // Maximum = 20
    
    // Advanced math
    int s = sqrt(16);           // Square root = 4
    int p = pow(2, 8);          // Power = 256
    int l = log(100);           // Logarithm
    int e = exp(2);             // Exponential
    
    // Trigonometry
    int si = sin(45);           // Sine
    int co = cos(45);           // Cosine
    int ta = tan(45);           // Tangent
    
    // Clamping
    int c = clamp(150, 0, 100); // Clamp to range = 100
    
    return a;
}
```

#### Graphics Functions (NEW!)

```cpp
int main() {
    // Linear interpolation
    int color = lerp(0, 255, 128);  // 50% blend = ~127
    
    // Clamp to color range
    color = saturate(color);         // Ensure 0-255
    
    // Get direction/sign
    int dx = 100 - 50;
    int dir = sign(dx);              // Returns 1 (positive)
    
    return color;
}
```

**LERP Examples:**
```cpp
// Color fade
int start_color = 0;
int end_color = 255;
int mid_color = lerp(start_color, end_color, 128);  // 50%

// Position interpolation
int start_x = 0;
int end_x = 100;
int current_x = lerp(start_x, end_x, 64);  // 25%

// Animation
for (int i = 0; i < 10; i++) {
    int t = i * 25;  // 0, 25, 50, ..., 225
    int pos = lerp(0, 100, t);
}
```

**SIGN Examples:**
```cpp
// Movement direction
int player_x = 50;
int target_x = 150;
int dx = target_x - player_x;
int dir_x = sign(dx);  // Returns 1 (moving right)

// Move player
player_x = player_x + dir_x * 5;

// Collision normal
int collision_x = -10;
int normal_x = sign(collision_x);  // Returns -1
```

**SATURATE Examples:**
```cpp
// Brightness control
int brightness = 300;
brightness = saturate(brightness);  // = 255

// Color operations
int r = 200;
int light = 100;
r = r + light;
r = saturate(r);  // = 255 (clamped)

// Ensure valid color
int color = -50;
color = saturate(color);  // = 0
```

#### Bit Operations

```cpp
int main() {
    // Rotate bits
    int pattern = 0x0F;
    int rotated_left = rotl(pattern, 4);
    int rotated_right = rotr(pattern, 4);
    
    // Count bits
    int bits = popcount(255);      // = 8
    int leading = lzcnt(16);       // Leading zeros
    int trailing = tzcnt(16);      // Trailing zeros
    
    // Reverse & swap
    int reversed = reverse(0xFF);
    int swapped = bswap(0x1234);
    
    return bits;
}
```

#### Timing & Random

```cpp
int main() {
    // Get timestamp
    int start = gettime();
    
    // Sleep (milliseconds)
    sleep(100);
    
    // Calculate elapsed time
    int end = gettime();
    int elapsed = end - start;
    
    // Random number
    int r = rand();
    int random_pos = r % 100;  // 0-99
    
    // Hash
    int h = hash(42);
    int seed = hash(elapsed);
    
    // CRC32
    int checksum = crc32(12345);
    
    return elapsed;
}
```

#### String & Memory

```cpp
int main() {
    // String length (address-based)
    int len = strlen(0x1000);
    
    // String compare (address-based)
    int cmp = strcmp(0x1000, 0x2000);
    
    // Memory set (address-based)
    memset(0x3000, 0, 100);
    
    return len;
}
```

#### Utilities

```cpp
int main() {
    // Swap variables
    int a = 10;
    int b = 20;
    swap(a, b);  // Now a=20, b=10
    
    // Clamp to range
    int value = 150;
    int clamped = clamp(value, 0, 100);  // = 100
    
    return a;
}
```

### Inline Assembly

**Syntax:**
```cpp
asm("INSTRUCTION");
```

**Examples:**
```cpp
int main() {
    int x = 10;
    
    // No operation
    asm("NOP");
    
    // Register operations
    asm("INC R4");
    asm("DEC R5");
    
    // Stack operations
    asm("PUSH R0");
    asm("POP R0");
    
    // Multiple instructions
    asm("PUSH R4");
    asm("LOADI R4, 100");
    asm("POP R4");
    
    return x;
}
```

**Performance-Critical Code:**
```cpp
int main() {
    int result = 0;
    
    // Fast loop using assembly
    asm("LOADI R4, 0");      // counter
    asm("LOADI R5, 100");    // limit
    
    // Loop would go here
    
    asm("MOV R0, R4");       // Return counter
    
    return result;
}
```

### Printf

**Basic Usage:**
```cpp
int main() {
    printf("Hello, World!\n");
    return 0;
}
```

**With Values:**
```cpp
int main() {
    int x = 42;
    printf("Value: %d\n", x);
    
    printf("Multiple: %d %d\n", 10, 20);
    
    return 0;
}
```


---

## Running Programs

### Compiling Assembly

**Step 1: Write the code**
```bash
simpleos> nano program.asm
```

**Step 2: Assemble**
```bash
simpleos> loadasm program.asm program.bin
Assembly successful: 48 bytes
```

**Step 3: Run**
```bash
simpleos> run program.bin
Program executed, return code: 0
```

**All in one (using write):**
```bash
simpleos> write program.asm ".org 0x1000\nmain:\n  LOADI R0, 42\n  HALT"
simpleos> loadasm program.asm program.bin
simpleos> run program.bin
```

### Compiling C++

**Step 1: Write the code**
```bash
simpleos> nano hello.cpp
```

**Step 2: Compile**
```bash
simpleos> cas++ hello.cpp hello.bin
Compilation successful
```

**Step 3: Run**
```bash
simpleos> run hello.bin
Hello, World!
```

**Compile and run immediately:**
```bash
simpleos> cas++ hello.cpp --run
Hello, World!
```

**Show assembly output:**
```bash
simpleos> cas++ hello.cpp --asm
; Generated by cas++ compiler
.org 0x1000
main:
    LOADI R0, 1
    ...
```

**Debug mode:**
```bash
simpleos> cas++ hello.cpp --debug
Compilation successful
Debug info: ...
```

### Using the Shell

**Create a file:**
```bash
simpleos> write hello.cpp "int main() { printf(\"Hello!\\n\"); return 0; }"
```

**Edit a file:**
```bash
simpleos> nano hello.cpp
# Edit in nano, :wq to save
```

**View a file:**
```bash
simpleos> cat hello.cpp
int main() { printf("Hello!\n"); return 0; }
```

**Compile:**
```bash
simpleos> cas++ hello.cpp hello.bin
```

**Run:**
```bash
simpleos> run hello.bin
Hello!
```

**Check registers after execution:**
```bash
simpleos> regs
R0:  0x00000000  R1:  0x00000000
...
```

**Disassemble:**
```bash
simpleos> disasm 0x1000 10
0x1000: LOADI R0, 1
0x1004: LOADI R1, 1
...
```

---

## Complete Code Examples

### Example 1: Array Sum (C++)

```cpp
int main() {
    int nums[10];
    int i = 0;
    
    // Initialize array
    for (i = 0; i < 10; i++) {
        nums[i] = i + 1;  // 1, 2, 3, ..., 10
    }
    
    // Calculate sum
    int sum = 0;
    for (i = 0; i < 10; i++) {
        sum = sum + nums[i];
    }
    
    printf("Sum: %d\n", sum);
    return sum;  // Returns 55
}
```

**How to run:**
```bash
simpleos> write sum.cpp "int main() { ..."
simpleos> cas++ sum.cpp --run
Sum: 55
```

### Example 2: Color Fade (C++)

```cpp
int main() {
    int colors[10];
    int i = 0;
    
    printf("Color fade animation\n");
    
    // Fade from black (0) to white (255)
    for (i = 0; i < 10; i++) {
        int t = i * 25;  // 0, 25, 50, ..., 225
        colors[i] = lerp(0, 255, t);
        colors[i] = saturate(colors[i]);
        
        printf("Frame %d: color = %d\n", i, colors[i]);
    }
    
    return colors[5];
}
```

### Example 3: Sprite Movement (C++)

```cpp
class Sprite {
    int x;
    int y;
    int health;
};

int main() {
    int sprite_x = 50;
    int sprite_y = 50;
    int target_x = 150;
    int target_y = 100;
    int speed = 5;
    
    printf("Moving sprite to target\n");
    
    // Move for 10 frames
    int frame = 0;
    for (frame = 0; frame < 10; frame++) {
        // Calculate direction
        int dx = target_x - sprite_x;
        int dy = target_y - sprite_y;
        
        int dir_x = sign(dx);
        int dir_y = sign(dy);
        
        // Move sprite
        sprite_x = sprite_x + dir_x * speed;
        sprite_y = sprite_y + dir_y * speed;
        
        printf("Frame %d: pos=(%d, %d)\n", frame, sprite_x, sprite_y);
        
        // Frame delay
        sleep(16);  // ~60 FPS
    }
    
    printf("Final position: (%d, %d)\n", sprite_x, sprite_y);
    return 0;
}
```

### Example 4: Game Loop (C++)

```cpp
int main() {
    int player_x = 50;
    int enemy_x = 100;
    int score = 0;
    int health = 100;
    
    printf("Game starting...\n");
    
    // Game loop (60 frames)
    int frame = 0;
    for (frame = 0; frame < 60; frame++) {
        // AI: Move toward player
        int dx = player_x - enemy_x;
        int dir = sign(dx);
        enemy_x = enemy_x + dir * 1;
        
        // Player: Move toward enemy
        dx = enemy_x - player_x;
        dir = sign(dx);
        player_x = player_x + dir * 2;
        
        // Check collision
        int dist = abs(enemy_x - player_x);
        if (dist < 5) {
            score = score + 10;
            health = health - 5;
            printf("Hit! Score: %d, Health: %d\n", score, health);
        }
        
        // Check game over
        if (health <= 0) {
            printf("Game Over!\n");
            break;
        }
        
        // Frame delay
        sleep(16);
    }
    
    printf("Final score: %d\n", score);
    return score;
}
```

### Example 5: Particle System (C++)

```cpp
int main() {
    int particles_x[20];
    int particles_y[20];
    int particles_active[20];
    
    printf("Particle system demo\n");
    
    // Initialize particles
    int i = 0;
    for (i = 0; i < 20; i++) {
        int r = rand();
        particles_x[i] = r % 100;
        particles_y[i] = 0;
        particles_active[i] = 1;
    }
    
    // Simulate 30 frames
    int frame = 0;
    for (frame = 0; frame < 30; frame++) {
        // Update particles
        for (i = 0; i < 20; i++) {
            if (particles_active[i] == 1) {
                // Apply gravity
                particles_y[i] = particles_y[i] + 2;
                
                // Deactivate if off screen
                if (particles_y[i] > 100) {
                    particles_active[i] = 0;
                }
            }
        }
        
        // Count active particles
        int active = 0;
        for (i = 0; i < 20; i++) {
            if (particles_active[i] == 1) {
                active++;
            }
        }
        
        printf("Frame %d: %d active particles\n", frame, active);
        sleep(33);  // ~30 FPS
    }
    
    return 0;
}
```


### Example 6: Bit Pattern Effects (Assembly)

```assembly
.org 0x1000

main:
    ; Initialize pattern
    LOADI R0, 0x0F
    LOADI R1, 0        ; Frame counter
    LOADI R2, 8        ; Frame limit
    
animation_loop:
    ; Rotate pattern
    PUSH R0
    LOADI R3, 1
    ROL R0, R3
    
    ; Count active bits
    POPCOUNT R4, R0
    
    ; Next frame
    INC R1
    CMP R1, R2
    POP R0
    JL animation_loop
    
    HALT
```

### Example 7: Memory Operations (Assembly)

```assembly
.org 0x1000

main:
    ; Copy memory block
    LOADI R0, source     ; Source address
    LOADI R1, dest       ; Dest address
    LOADI R2, 10         ; Count
    
copy_loop:
    CMP R2, 0
    JE copy_done
    
    LOAD R3, R0          ; Load from source
    STORE R3, R1         ; Store to dest
    
    ADDI R0, 4           ; Next source word
    ADDI R1, 4           ; Next dest word
    DEC R2
    JMP copy_loop
    
copy_done:
    HALT

source:
    .word 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

dest:
    .word 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
```

---

## Advanced Techniques

### Optimization Tips

**1. Minimize Variables**
```cpp
// Bad: Too many variables
int main() {
    int a = 10;
    int b = 20;
    int c = 30;
    int d = 40;
    int e = 50;
    int f = 60;
    int g = 70;
    int h = 80;
    int i = 90;
    int j = 100;  // ERROR: Out of registers!
    return 0;
}

// Good: Reuse variables
int main() {
    int temp = 0;
    int sum = 0;
    
    temp = 10;
    sum = sum + temp;
    
    temp = 20;
    sum = sum + temp;
    
    return sum;
}
```

**2. Use Arrays for Bulk Data**
```cpp
// Good: Use arrays
int main() {
    int data[100];  // Only uses 1 "variable"
    
    int i = 0;
    for (i = 0; i < 100; i++) {
        data[i] = i;
    }
    
    return data[0];
}
```

**3. Use New Opcodes**
```cpp
// Slow: Manual interpolation
int lerp_manual(int a, int b, int t) {
    int diff = b - a;
    int scaled = diff * t;
    int result = a + scaled / 256;
    return result;
}

// Fast: Use LERP opcode
int lerp_fast(int a, int b, int t) {
    return lerp(a, b, t);  // Single instruction!
}
```

**4. Use Inline Assembly for Critical Code**
```cpp
int main() {
    int x = 100;
    
    // Critical performance section
    asm("PUSH R4");
    asm("LOADI R4, 1000");
    // ... fast operations ...
    asm("POP R4");
    
    return x;
}
```

### Common Patterns

**Pattern 1: Smooth Movement**
```cpp
int main() {
    int current_x = 0;
    int target_x = 100;
    
    // Smooth approach (10 frames)
    int frame = 0;
    for (frame = 0; frame < 10; frame++) {
        int t = frame * 25;  // 0, 25, 50, ..., 225
        current_x = lerp(current_x, target_x, t);
    }
    
    return current_x;
}
```

**Pattern 2: Direction-Based Movement**
```cpp
int main() {
    int player_x = 50;
    int target_x = 150;
    int speed = 5;
    
    // Move toward target
    int dx = target_x - player_x;
    int dir = sign(dx);
    player_x = player_x + dir * speed;
    
    return player_x;
}
```

**Pattern 3: Color Blending**
```cpp
int main() {
    int color1 = 0;      // Black
    int color2 = 255;    // White
    int blend = 128;     // 50%
    
    int result = lerp(color1, color2, blend);
    result = saturate(result);
    
    return result;
}
```

**Pattern 4: Collision Detection**
```cpp
int main() {
    int obj1_x = 50;
    int obj2_x = 55;
    int threshold = 10;
    
    int dist = abs(obj2_x - obj1_x);
    
    if (dist < threshold) {
        // Collision!
        int dx = obj2_x - obj1_x;
        int bounce = sign(dx);
        obj1_x = obj1_x - bounce * 5;
    }
    
    return obj1_x;
}
```

---

## Debugging & Optimization

### Debugging Techniques

**1. Use Printf**
```cpp
int main() {
    int x = 10;
    printf("x = %d\n", x);
    
    x = x * 2;
    printf("After multiply: x = %d\n", x);
    
    return x;
}
```

**2. Check Registers**
```bash
simpleos> run program.bin
simpleos> regs
R0:  0x0000002A  # Return value
R1:  0x00000000
...
```

**3. Disassemble Code**
```bash
simpleos> disasm 0x1000 20
0x1000: LOADI R0, 42
0x1004: SIGN R0
0x1008: HALT
```

**4. View Memory**
```bash
simpleos> memmap 0x2000 64
0x2000: 00 00 00 2A 00 00 00 00 ...
```

**5. Enable Debug Mode**
```bash
simpleos> debug on
simpleos> run program.bin
# Shows detailed execution
```

**6. Trace Execution**
```bash
simpleos> trace 0x1000 10
# Shows step-by-step execution
```

### Performance Profiling

**1. Time Execution**
```bash
simpleos> time run program.bin
Execution time: 0.123 seconds
```

**2. Count Instructions**
```cpp
int main() {
    int start = gettime();
    
    // Code to profile
    int sum = 0;
    for (int i = 0; i < 1000; i++) {
        sum = sum + i;
    }
    
    int end = gettime();
    int elapsed = end - start;
    
    printf("Time: %d ms\n", elapsed);
    return sum;
}
```

### Common Errors & Solutions

**Error: "Out of registers"**
```
Solution: Reduce number of variables
- Use arrays instead of many variables
- Reuse variables in loops
- Limit scope of variables
```

**Error: "Array not declared"**
```
Solution: Declare array before use
int arr[10];  // Declare first
arr[0] = 100; // Then use
```

**Error: "Invalid instruction"**
```
Solution: Check assembly syntax
LOADI R0, 42  # Correct
LOAD R0, 42   # Wrong (LOAD needs address)
```

**Error: "Segmentation fault"**
```
Solution: Check memory addresses
- Ensure addresses are valid
- Don't access beyond array bounds
- Initialize pointers properly
```

**Error: "Compilation failed"**
```
Solution: Check C++ syntax
- Missing semicolons
- Unmatched braces
- Undefined variables
- Type mismatches
```

### Best Practices

1. **Comment your code**
```cpp
// Calculate player movement
int dx = target_x - player_x;
int dir = sign(dx);  // Get direction (-1, 0, 1)
```

2. **Use meaningful names**
```cpp
// Good
int player_health = 100;
int enemy_damage = 10;

// Bad
int x = 100;
int y = 10;
```

3. **Test incrementally**
```cpp
// Test each part separately
int main() {
    // Test 1: Array initialization
    int arr[5] = {1, 2, 3, 4, 5};
    printf("Test 1 passed\n");
    
    // Test 2: Array access
    int x = arr[2];
    printf("Test 2: x = %d\n", x);
    
    return 0;
}
```

4. **Keep functions focused**
```cpp
// Good: One clear purpose
int calculate_distance(int x1, int x2) {
    int dx = x2 - x1;
    return abs(dx);
}
```

5. **Use constants**
```cpp
const int MAX_HEALTH = 100;
const int SCREEN_WIDTH = 320;
const int SCREEN_HEIGHT = 240;
```

---

## Quick Reference

### Essential Assembly Instructions
```assembly
LOADI R0, 42     # Load immediate
MOV R1, R0       # Move register
ADD R0, R1       # Add
SUB R0, R1       # Subtract
MUL R0, R1       # Multiply
DIV R0, R1       # Divide
CMP R0, R1       # Compare
JMP label        # Jump
JZ label         # Jump if zero
CALL func        # Call function
RET              # Return
PUSH R0          # Push to stack
POP R0           # Pop from stack
HALT             # Stop
```

### Essential C++ Syntax
```cpp
int x = 10;              // Variable
int arr[5];              // Array
if (x > 5) { }           // If statement
for (int i=0; i<10; i++) // For loop
while (x < 100) { }      // While loop
int y = abs(-10);        // Math function
int c = lerp(0,255,128); // Interpolation
int d = sign(-42);       // Sign function
int s = saturate(300);   // Saturate
asm("NOP");              // Inline assembly
printf("text\n");        // Print
```

### Shell Commands for Coding
```bash
nano file.asm        # Edit assembly
loadasm file.asm out.bin  # Assemble
nano file.cpp        # Edit C++
cas++ file.cpp out.bin    # Compile C++
cas++ file.cpp --run      # Compile and run
run program.bin      # Execute
regs                 # Show registers
disasm 0x1000 10     # Disassemble
memmap 0x2000 64     # View memory
debug on             # Enable debug
```

---

## Conclusion

You now have complete knowledge of:
- ✅ Assembly programming (all instructions)
- ✅ C++ programming (all features)
- ✅ How to compile and run programs
- ✅ Advanced techniques and patterns
- ✅ Debugging and optimization
- ✅ Best practices

**Start coding and build amazing things in SimpleOS!** 🚀

---

*For more information:*
- See TUTORIAL.md for system overview

*Version: 2.0*
*Last Updated: 2024*

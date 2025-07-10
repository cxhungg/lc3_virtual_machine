# LC-3 Virtual Machine

This project implements an LC-3 Virtual Machine system, including a C-based emulator, a Python interactive debugger, and an assembler. I learned how to do this through this [blog](https://www.jmeiners.com/lc3-vm/).

## Overview

The LC-3 is a simple 16-bit computer architecture designed for educational purposes. This project implements:

- **Virtual Machine** (`lc3_vm.c`): A C implementation of the LC-3 processor
- **Assembler** (`assemble.py`): Converts LC-3 assembly code to machine code
- **Debugger** (`lc3_debugger.py`): Interactive GUI debugger with real-time visualization

## Features

### Virtual Machine (`lc3_vm.c`)
- Complete LC-3 instruction set implementation
- Memory-mapped I/O support
- Real-time keyboard input handling
- All standard LC-3 trap routines (GETC, OUT, PUTS, IN, PUTSP, HALT)

### Assembler (`assemble.py`)
- Two-pass assembly process
- Symbol table generation and resolution
- Support for all LC-3 directives (.ORIG, .FILL, .BLKW, .STRINGZ, .END)
- Generates standard LC-3 object files

### Debugger (`lc3_debugger.py`)
- Interactive GUI built with Tkinter
- Real-time register and memory visualization
- Step-by-step execution
- Breakpoint management
- Console I/O simulation
- Memory view with disassembly
- Input/output buffering

## Project Structure

```
VirtualMachine/
├── lc3_vm.c              # C implementation of LC-3 virtual machine
├── assemble.py            # Python assembler for LC-3 assembly code
├── lc3_debugger.py       # Interactive GUI debugger
└── games/                 # Sample assembly programs
    ├── hello.asm         # Simple "Hello World" program
    └── guessing_game.asm # Interactive number guessing game
```

### Building the Virtual Machine

```bash
# Compile the C virtual machine
gcc -o lc3_vm lc3_vm.c

# Run a program
./lc3_vm hello.obj
```

### Using the Assembler

```bash
# Assemble an assembly file
python assemble.py games/hello.asm hello.obj

# Assemble the guessing game
python assemble.py games/guessing_game.asm guessing_game.obj
```

### Using the Debugger

```bash
# Start the debugger
python lc3_debugger.py
```

The debugger provides a graphical interface where you can:
- Load `.obj` files
- Step through code execution
- Set breakpoints
- View registers and memory in real-time
- Interact with console I/O

![LC-3 Debugger Interface](.\image\debugger.jpg)

## Sample Programs

### Hello World (`games/hello.asm`)
A simple program that prints "Hello!" to the console.

```assembly
.ORIG x3000
        LEA R0, HELLO
        PUTS
        HALT
HELLO:  .STRINGZ "Hello!\n"
```




## Use

1. **Write Assembly Code**: Create `.asm` files using any text editor
2. **Assemble**: Use `assemble.py` to convert `.asm` to `.obj` files
3. **Debug**: Use `lc3_debugger.py` for debugging
4. **Run**: Use `lc3_vm.c` for standalone execution

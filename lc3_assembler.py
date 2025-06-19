import sys
import struct

INSTRUCTION_SET = {
    "ADD", "AND", "BR", "BRn", "BRz", "BRp", "BRnz", "BRnp", "BRzp", "BRnzp",
    "JMP", "JSR", "JSRR", "LD", "LDI", "LDR", "LEA",
    "NOT", "RET", "ST", "STI", "STR", "TRAP", "HALT"
}

TRAP_CODES = {
    "GETC": 0x20,
    "OUT":  0x21,
    "PUTS": 0x22,
    "IN":   0x23,
    "PUTSP":0x24,
    "HALT": 0x25
}
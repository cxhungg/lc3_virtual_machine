
"""
LC-3 Assembler
Converts LC-3 assembly code to object files compatible with the LC-3 VM.
"""

import sys
import re
import struct
from typing import Dict, List, Tuple, Optional, Union
from enum import Enum

class TokenType(Enum):
    DIRECTIVE = "directive"
    INSTRUCTION = "instruction"
    LABEL = "label"
    REGISTER = "register"
    IMMEDIATE = "immediate"
    STRING = "string"
    COMMENT = "comment"
    NEWLINE = "newline"

class LC3Assembler:
    def __init__(self):
        # Instruction opcodes
        self.opcodes = {
            'BR': 0, 'BRN': 0, 'BRZ': 0, 'BRP': 0, 'BRNZ': 0, 'BRNP': 0, 'BRZP': 0, 'BRNZP': 0,
            'ADD': 1,
            'LD': 2,
            'ST': 3,
            'JSR': 4, 'JSRR': 4,
            'AND': 5,
            'LDR': 6,
            'STR': 7,
            'RTI': 8,
            'NOT': 9,
            'LDI': 10,
            'STI': 11,
            'JMP': 12, 'RET': 12,
            'LEA': 14,
            'TRAP': 15
        }
        
        # Trap vectors
        self.trap_vectors = {
            'GETC': 0x20,
            'OUT': 0x21,
            'PUTS': 0x22,
            'IN': 0x23,
            'PUTSP': 0x24,
            'HALT': 0x25
        }
        
        # Registers
        self.registers = {
            'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3,
            'R4': 4, 'R5': 5, 'R6': 6, 'R7': 7
        }
        
        # Symbol table for labels
        self.symbol_table: Dict[str, int] = {}
        
        # Current program counter
        self.pc = 0
        
        # Origin address
        self.origin = 0x3000
        
        # Memory for assembled code
        self.memory: List[int] = []
        
        # Current line number for error reporting
        self.line_number = 0
        
    def error(self, message: str) -> None:
        """Print error message and exit"""
        print(f"Error on line {self.line_number}: {message}", file=sys.stderr)
        sys.exit(1)
        
    def warning(self, message: str) -> None:
        """Print warning message"""
        print(f"Warning on line {self.line_number}: {message}", file=sys.stderr)
        
    def parse_number(self, token: str) -> int:
        """Parse a number in decimal, hex, or binary format"""
        token = token.strip()
        
        if token.startswith('x') or token.startswith('X'):
            # Hexadecimal
            return int(token[1:], 16)
        elif token.startswith('b') or token.startswith('B'):
            # Binary
            return int(token[1:], 2)
        elif token.startswith('#'):
            # Decimal with # prefix
            return int(token[1:])
        else:
            # Plain decimal
            return int(token)
            
    def sign_extend(self, value: int, bits: int) -> int:
        """Sign extend a value to 16 bits"""
        # Check if the sign bit is set
        if value & (1 << (bits - 1)):
            # Extend with 1s
            return value | (0xFFFF << bits)
        return value & ((1 << bits) - 1)
        
    def check_range(self, value: int, bits: int, signed: bool = True) -> bool:
        """Check if value fits in the specified number of bits"""
        if signed:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1
        else:
            min_val = 0
            max_val = (1 << bits) - 1
        return min_val <= value <= max_val
        
    def tokenize_line(self, line: str) -> List[str]:
        """Tokenize a line of assembly code"""
        # Remove comments
        if ';' in line:
            line = line[:line.index(';')]
        
        # Split by whitespace and commas
        tokens = re.split(r'[\s,]+', line.strip())
        return [token for token in tokens if token]
        
    def is_register(self, token: str) -> bool:
        """Check if token is a register"""
        return token.upper() in self.registers
        
    def is_label(self, token: str) -> bool:
        """Check if token is a label (ends with colon or is a valid identifier)"""
        return token.endswith(':') or (token.isidentifier() and not self.is_register(token))
        
    def parse_register(self, token: str) -> int:
        """Parse register token"""
        reg = token.upper()
        if reg not in self.registers:
            self.error(f"Invalid register: {token}")
        return self.registers[reg]
        
    def parse_immediate(self, token: str) -> int:
        """Parse immediate value"""
        try:
            return self.parse_number(token)
        except ValueError:
            self.error(f"Invalid immediate value: {token}")
            
    def assemble_br(self, tokens: List[str]) -> int:
        """Assemble branch instruction"""
        if len(tokens) != 2:
            self.error("BR instruction requires exactly one operand")
            
        instr = tokens[0].upper()
        
        # Determine condition codes
        n = z = p = 0
        if 'N' in instr:
            n = 1
        if 'Z' in instr:
            z = 1
        if 'P' in instr:
            p = 1
            
        # If no condition specified, default to unconditional (NZP)
        if n == 0 and z == 0 and p == 0:
            n = z = p = 1
            
        # Parse offset
        if tokens[1] in self.symbol_table:
            offset = self.symbol_table[tokens[1]] - (self.pc + 1)
        else:
            try:
                offset = self.parse_immediate(tokens[1])
            except:
                self.error(f"Undefined label or invalid offset: {tokens[1]}")
                
        if not self.check_range(offset, 9):
            self.error(f"Branch offset out of range: {offset}")
            
        offset = offset & 0x1FF  # 9 bits
        
        return (0 << 12) | (n << 11) | (z << 10) | (p << 9) | offset
        
    def assemble_add(self, tokens: List[str]) -> int:
        """Assemble ADD instruction"""
        if len(tokens) != 4:
            self.error("ADD instruction requires exactly 3 operands")
            
        dr = self.parse_register(tokens[1])
        sr1 = self.parse_register(tokens[2])
        
        # Check if third operand is register or immediate
        if self.is_register(tokens[3]):
            # Register mode
            sr2 = self.parse_register(tokens[3])
            return (1 << 12) | (dr << 9) | (sr1 << 6) | sr2
        else:
            # Immediate mode
            imm = self.parse_immediate(tokens[3])
            if not self.check_range(imm, 5):
                self.error(f"ADD immediate value out of range: {imm}")
            imm = imm & 0x1F  # 5 bits
            return (1 << 12) | (dr << 9) | (sr1 << 6) | (1 << 5) | imm
            
    def assemble_and(self, tokens: List[str]) -> int:
        """Assemble AND instruction"""
        if len(tokens) != 4:
            self.error("AND instruction requires exactly 3 operands")
            
        dr = self.parse_register(tokens[1])
        sr1 = self.parse_register(tokens[2])
        
        # Check if third operand is register or immediate
        if self.is_register(tokens[3]):
            # Register mode
            sr2 = self.parse_register(tokens[3])
            return (5 << 12) | (dr << 9) | (sr1 << 6) | sr2
        else:
            # Immediate mode
            imm = self.parse_immediate(tokens[3])
            if not self.check_range(imm, 5):
                self.error(f"AND immediate value out of range: {imm}")
            imm = imm & 0x1F  # 5 bits
            return (5 << 12) | (dr << 9) | (sr1 << 6) | (1 << 5) | imm
            
    def assemble_not(self, tokens: List[str]) -> int:
        """Assemble NOT instruction"""
        if len(tokens) != 3:
            self.error("NOT instruction requires exactly 2 operands")
            
        dr = self.parse_register(tokens[1])
        sr = self.parse_register(tokens[2])
        
        return (9 << 12) | (dr << 9) | (sr << 6) | 0x3F
        
    def assemble_ld(self, tokens: List[str]) -> int:
        """Assemble LD instruction"""
        if len(tokens) != 3:
            self.error("LD instruction requires exactly 2 operands")
            
        dr = self.parse_register(tokens[1])
        
        # Parse offset
        if tokens[2] in self.symbol_table:
            offset = self.symbol_table[tokens[2]] - (self.pc + 1)
        else:
            offset = self.parse_immediate(tokens[2])
            
        if not self.check_range(offset, 9):
            self.error(f"LD offset out of range: {offset}")
            
        offset = offset & 0x1FF  # 9 bits
        
        return (2 << 12) | (dr << 9) | offset
        
    def assemble_st(self, tokens: List[str]) -> int:
        """Assemble ST instruction"""
        if len(tokens) != 3:
            self.error("ST instruction requires exactly 2 operands")
            
        sr = self.parse_register(tokens[1])
        
        # Parse offset
        if tokens[2] in self.symbol_table:
            offset = self.symbol_table[tokens[2]] - (self.pc + 1)
        else:
            offset = self.parse_immediate(tokens[2])
            
        if not self.check_range(offset, 9):
            self.error(f"ST offset out of range: {offset}")
            
        offset = offset & 0x1FF  # 9 bits
        
        return (3 << 12) | (sr << 9) | offset
        
    def assemble_jsr(self, tokens: List[str]) -> int:
        """Assemble JSR/JSRR instruction"""
        if len(tokens) != 2:
            self.error("JSR/JSRR instruction requires exactly 1 operand")
            
        if tokens[0].upper() == 'JSRR':
            # JSRR - register mode
            base_r = self.parse_register(tokens[1])
            return (4 << 12) | (base_r << 6)
        else:
            # JSR - PC-relative mode
            if tokens[1] in self.symbol_table:
                offset = self.symbol_table[tokens[1]] - (self.pc + 1)
            else:
                offset = self.parse_immediate(tokens[1])
                
            if not self.check_range(offset, 11):
                self.error(f"JSR offset out of range: {offset}")
                
            offset = offset & 0x7FF  # 11 bits
            
            return (4 << 12) | (1 << 11) | offset
            
    def assemble_jmp(self, tokens: List[str]) -> int:
        """Assemble JMP/RET instruction"""
        if tokens[0].upper() == 'RET':
            # RET is JMP R7
            return (12 << 12) | (7 << 6)
        else:
            if len(tokens) != 2:
                self.error("JMP instruction requires exactly 1 operand")
            base_r = self.parse_register(tokens[1])
            return (12 << 12) | (base_r << 6)
            
    def assemble_ldr(self, tokens: List[str]) -> int:
        """Assemble LDR instruction"""
        if len(tokens) != 4:
            self.error("LDR instruction requires exactly 3 operands")
            
        dr = self.parse_register(tokens[1])
        base_r = self.parse_register(tokens[2])
        offset = self.parse_immediate(tokens[3])
        
        if not self.check_range(offset, 6):
            self.error(f"LDR offset out of range: {offset}")
            
        offset = offset & 0x3F  # 6 bits
        
        return (6 << 12) | (dr << 9) | (base_r << 6) | offset
        
    def assemble_str(self, tokens: List[str]) -> int:
        """Assemble STR instruction"""
        if len(tokens) != 4:
            self.error("STR instruction requires exactly 3 operands")
            
        sr = self.parse_register(tokens[1])
        base_r = self.parse_register(tokens[2])
        offset = self.parse_immediate(tokens[3])
        
        if not self.check_range(offset, 6):
            self.error(f"STR offset out of range: {offset}")
            
        offset = offset & 0x3F  # 6 bits
        
        return (7 << 12) | (sr << 9) | (base_r << 6) | offset
        
    def assemble_ldi(self, tokens: List[str]) -> int:
        """Assemble LDI instruction"""
        if len(tokens) != 3:
            self.error("LDI instruction requires exactly 2 operands")
            
        dr = self.parse_register(tokens[1])
        
        # Parse offset
        if tokens[2] in self.symbol_table:
            offset = self.symbol_table[tokens[2]] - (self.pc + 1)
        else:
            offset = self.parse_immediate(tokens[2])
            
        if not self.check_range(offset, 9):
            self.error(f"LDI offset out of range: {offset}")
            
        offset = offset & 0x1FF  # 9 bits
        
        return (10 << 12) | (dr << 9) | offset
        
    def assemble_sti(self, tokens: List[str]) -> int:
        """Assemble STI instruction"""
        if len(tokens) != 3:
            self.error("STI instruction requires exactly 2 operands")
            
        sr = self.parse_register(tokens[1])
        
        # Parse offset
        if tokens[2] in self.symbol_table:
            offset = self.symbol_table[tokens[2]] - (self.pc + 1)
        else:
            offset = self.parse_immediate(tokens[2])
            
        if not self.check_range(offset, 9):
            self.error(f"STI offset out of range: {offset}")
            
        offset = offset & 0x1FF  # 9 bits
        
        return (11 << 12) | (sr << 9) | offset
        
    def assemble_lea(self, tokens: List[str]) -> int:
        """Assemble LEA instruction"""
        if len(tokens) != 3:
            self.error("LEA instruction requires exactly 2 operands")
            
        dr = self.parse_register(tokens[1])
        
        # Parse offset
        if tokens[2] in self.symbol_table:
            offset = self.symbol_table[tokens[2]] - (self.pc + 1)
        else:
            offset = self.parse_immediate(tokens[2])
            
        if not self.check_range(offset, 9):
            self.error(f"LEA offset out of range: {offset}")
            
        offset = offset & 0x1FF  # 9 bits
        
        return (14 << 12) | (dr << 9) | offset
        
    def assemble_trap(self, tokens: List[str]) -> int:
        """Assemble TRAP instruction"""
        if len(tokens) != 2:
            self.error("TRAP instruction requires exactly 1 operand")
            
        # Check if it's a named trap
        trap_name = tokens[1].upper()
        if trap_name in self.trap_vectors:
            trap_vector = self.trap_vectors[trap_name]
        else:
            trap_vector = self.parse_immediate(tokens[1])
            
        if not self.check_range(trap_vector, 8, signed=False):
            self.error(f"TRAP vector out of range: {trap_vector}")
            
        return (15 << 12) | (trap_vector & 0xFF)
        
    def assemble_rti(self, tokens: List[str]) -> int:
        """Assemble RTI instruction"""
        if len(tokens) != 1:
            self.error("RTI instruction takes no operands")
        return 8 << 12
        
    def assemble_instruction(self, tokens: List[str]) -> int:
        """Assemble a single instruction"""
        opcode = tokens[0].upper()
        
        if opcode.startswith('BR'):
            return self.assemble_br(tokens)
        elif opcode == 'ADD':
            return self.assemble_add(tokens)
        elif opcode == 'AND':
            return self.assemble_and(tokens)
        elif opcode == 'NOT':
            return self.assemble_not(tokens)
        elif opcode == 'LD':
            return self.assemble_ld(tokens)
        elif opcode == 'ST':
            return self.assemble_st(tokens)
        elif opcode in ['JSR', 'JSRR']:
            return self.assemble_jsr(tokens)
        elif opcode in ['JMP', 'RET']:
            return self.assemble_jmp(tokens)
        elif opcode == 'LDR':
            return self.assemble_ldr(tokens)
        elif opcode == 'STR':
            return self.assemble_str(tokens)
        elif opcode == 'LDI':
            return self.assemble_ldi(tokens)
        elif opcode == 'STI':
            return self.assemble_sti(tokens)
        elif opcode == 'LEA':
            return self.assemble_lea(tokens)
        elif opcode == 'TRAP' or opcode in self.trap_vectors:
            if opcode in self.trap_vectors:
                # Handle named traps like HALT, GETC, etc.
                return self.assemble_trap(['TRAP', opcode])
            else:
                return self.assemble_trap(tokens)
        elif opcode == 'RTI':
            return self.assemble_rti(tokens)
        else:
            self.error(f"Unknown instruction: {opcode}")
            
    def process_directive(self, tokens: List[str]) -> Optional[int]:
        """Process assembler directives"""
        directive = tokens[0].upper()
        
        if directive == '.ORIG':
            if len(tokens) != 2:
                self.error(".ORIG directive requires exactly 1 operand")
            self.origin = self.parse_immediate(tokens[1])
            self.pc = self.origin
            return None
            
        elif directive == '.FILL':
            if len(tokens) != 2:
                self.error(".FILL directive requires exactly 1 operand")
            if tokens[1] in self.symbol_table:
                return self.symbol_table[tokens[1]]
            else:
                return self.parse_immediate(tokens[1]) & 0xFFFF
                
        elif directive == '.BLKW':
            if len(tokens) != 2:
                self.error(".BLKW directive requires exactly 1 operand")
            count = self.parse_immediate(tokens[1])
            if count < 0:
                self.error(".BLKW count must be non-negative")
            # Return a list of zeros
            return [0] * count
            
        elif directive == '.STRINGZ':
            if len(tokens) < 2:
                self.error(".STRINGZ directive requires a string operand")
            # Join all tokens after the directive to handle strings with spaces
            string_content = ' '.join(tokens[1:])
            if not (string_content.startswith('"') and string_content.endswith('"')):
                self.error(".STRINGZ string must be enclosed in double quotes")
            string_content = string_content[1:-1]  # Remove quotes
            
            # Convert string to list of character codes
            result = []
            i = 0
            while i < len(string_content):
                if string_content[i] == '\\' and i + 1 < len(string_content):
                    # Handle escape sequences
                    if string_content[i + 1] == 'n':
                        result.append(ord('\n'))
                    elif string_content[i + 1] == 't':
                        result.append(ord('\t'))
                    elif string_content[i + 1] == 'r':
                        result.append(ord('\r'))
                    elif string_content[i + 1] == '\\':
                        result.append(ord('\\'))
                    elif string_content[i + 1] == '"':
                        result.append(ord('"'))
                    else:
                        result.append(ord(string_content[i + 1]))
                    i += 2
                else:
                    result.append(ord(string_content[i]))
                    i += 1
            result.append(0)  # Null terminator
            return result
            
        elif directive == '.END':
            return None
            
        else:
            self.error(f"Unknown directive: {directive}")
            
    def first_pass(self, lines: List[str]) -> None:
        """First pass: build symbol table"""
        self.pc = self.origin
        
        for line_num, line in enumerate(lines):
            self.line_number = line_num + 1
            
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith(';'):
                continue
                
            tokens = self.tokenize_line(line)
            if not tokens:
                continue
                
            # Check for label
            if tokens[0].endswith(':'):
                label = tokens[0][:-1]
                if label in self.symbol_table:
                    self.error(f"Duplicate label: {label}")
                self.symbol_table[label] = self.pc
                tokens = tokens[1:]  # Remove label from tokens
                
            if not tokens:
                continue
                
            # Check if it's a directive
            if tokens[0].startswith('.'):
                if tokens[0].upper() == '.ORIG':
                    self.origin = self.parse_immediate(tokens[1])
                    self.pc = self.origin
                elif tokens[0].upper() == '.BLKW':
                    count = self.parse_immediate(tokens[1])
                    self.pc += count
                elif tokens[0].upper() == '.STRINGZ':
                    string_content = ' '.join(tokens[1:])
                    if string_content.startswith('"') and string_content.endswith('"'):
                        string_content = string_content[1:-1]
                        # Count characters (including escape sequences)
                        char_count = 0
                        i = 0
                        while i < len(string_content):
                            if string_content[i] == '\\' and i + 1 < len(string_content):
                                i += 2
                            else:
                                i += 1
                            char_count += 1
                        self.pc += char_count + 1  # +1 for null terminator
                    else:
                        self.pc += 1  # Assume single word for error recovery
                elif tokens[0].upper() in ['.FILL', '.END']:
                    if tokens[0].upper() == '.FILL':
                        self.pc += 1
                else:
                    self.error(f"Unknown directive: {tokens[0]}")
            else:
                # It's an instruction
                self.pc += 1
                
    def second_pass(self, lines: List[str]) -> None:
        """Second pass: generate machine code"""
        self.pc = self.origin
        self.memory = []
        
        for line_num, line in enumerate(lines):
            self.line_number = line_num + 1
            
            # Skip empty lines and comments
            line = line.strip()
            if not line or line.startswith(';'):
                continue
                
            tokens = self.tokenize_line(line)
            if not tokens:
                continue
                
            # Skip label
            if tokens[0].endswith(':'):
                tokens = tokens[1:]
                
            if not tokens:
                continue
                
            # Process directive or instruction
            if tokens[0].startswith('.'):
                result = self.process_directive(tokens)
                if result is not None:
                    if isinstance(result, list):
                        self.memory.extend(result)
                        self.pc += len(result)
                    else:
                        self.memory.append(result)
                        self.pc += 1
            else:
                # Assemble instruction
                machine_code = self.assemble_instruction(tokens)
                self.memory.append(machine_code)
                self.pc += 1
                
    def assemble_file(self, input_file: str, output_file: str) -> None:
        """Assemble a file"""
        try:
            with open(input_file, 'r') as f:
                lines = f.readlines()
        except IOError as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            sys.exit(1)
            
        # First pass: build symbol table
        self.first_pass(lines)
        
        # Second pass: generate machine code
        self.second_pass(lines)
        
        # Write output file
        self.write_obj_file(output_file)
        
    def write_obj_file(self, filename: str) -> None:
        """Write object file in LC-3 format"""
        try:
            with open(filename, 'wb') as f:
                # Write origin (big-endian)
                f.write(struct.pack('>H', self.origin))
                
                # Write machine code (big-endian)
                for word in self.memory:
                    f.write(struct.pack('>H', word & 0xFFFF))
                    
        except IOError as e:
            print(f"Error writing output file: {e}", file=sys.stderr)
            sys.exit(1)
            
    def print_symbol_table(self) -> None:
        """Print symbol table for debugging"""
        print("Symbol Table:")
        for symbol, address in sorted(self.symbol_table.items()):
            print(f"  {symbol}: x{address:04X}")
            
def main():
    if len(sys.argv) != 3:
        print("Usage: python lc3_assembler.py <input.asm> <output.obj>", file=sys.stderr)
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    assembler = LC3Assembler()
    
    try:
        assembler.assemble_file(input_file, output_file)
        print(f"Assembly successful: {input_file} -> {output_file}")
        
        # Optionally print symbol table
        if assembler.symbol_table:
            print("\nSymbol Table:")
            for symbol, address in sorted(assembler.symbol_table.items()):
                print(f"  {symbol}: x{address:04X}")
                
    except SystemExit:
        pass
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
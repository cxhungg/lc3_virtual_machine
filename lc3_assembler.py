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

def to_twos_complement(val, bits):
    if val < 0:
        val = (1 << bits) + val
    return val & ((1 << bits) - 1)

def parse_reg(reg):
    return int(reg.replace("R", ""))






def parse_lc3_literal(s):
    s = s.strip()
    if s.startswith('x') or s.startswith('X'):
        return int(s[1:], 16)
    elif s.startswith('#'):
        return int(s[1:], 10)
    else:
        return int(s, 0)




def assemble_line(opcode, args, labels, pc):
    def get_offset(label, bits):
        return to_twos_complement(labels[label] - (pc + 1), bits)

    if opcode == "NOP":
        return 0x0000

    if opcode == "ADD" or opcode == "AND":
        dr, sr1, sr2 = args[0], args[1], args[2]
        drn, sr1n = parse_reg(dr), parse_reg(sr1)
        if sr2.startswith("R"):
            sr2n = parse_reg(sr2)
            return (0b0001 if opcode == "ADD" else 0b0101) << 12 | drn << 9 | sr1n << 6 | sr2n
        else:
            imm5 = to_twos_complement(int(sr2.replace("#", "")), 5)
            return (0b0001 if opcode == "ADD" else 0b0101) << 12 | drn << 9 | sr1n << 6 | 1 << 5 | imm5

    elif opcode == "NOT":
        dr, sr = args
        return 0b1001 << 12 | parse_reg(dr) << 9 | parse_reg(sr) << 6 | 0x3F

    elif opcode.startswith("BR"):
        cond = 0
        if "n" in opcode: cond |= 0b100
        if "z" in opcode: cond |= 0b010
        if "p" in opcode: cond |= 0b001
        label = args[0]
        pc_offset = get_offset(label, 9)
        return 0b0000 << 12 | cond << 9 | pc_offset

    elif opcode == "JMP" or opcode == "RET":
        r1 = parse_reg(args[0]) if opcode != "RET" else 7
        return 0b1100 << 12 | r1 << 6

    elif opcode == "JSR":
        label = args[0]
        pc_offset = get_offset(label, 11)
        return 0b0100 << 12 | 1 << 11 | pc_offset

    elif opcode == "JSRR":
        r1 = parse_reg(args[0])
        return 0b0100 << 12 | r1 << 6

    elif opcode == "LD":
        dr, label = args
        offset = get_offset(label, 9)
        return 0b0010 << 12 | parse_reg(dr) << 9 | offset

    elif opcode == "LDI":
        dr, label = args
        offset = get_offset(label, 9)
        return 0b1010 << 12 | parse_reg(dr) << 9 | offset

    elif opcode == "LDR":
        dr, base_r, offset = parse_reg(args[0]), parse_reg(args[1]), int(args[2].replace("#", ""))
        return 0b0110 << 12 | dr << 9 | base_r << 6 | to_twos_complement(offset, 6)

    elif opcode == "LEA":
        dr, label = args
        offset = get_offset(label, 9)
        return 0b1110 << 12 | parse_reg(dr) << 9 | offset

    elif opcode == "ST":
        sr, label = args
        offset = get_offset(label, 9)
        return 0b0011 << 12 | parse_reg(sr) << 9 | offset

    elif opcode == "STI":
        sr, label = args
        offset = get_offset(label, 9)
        return 0b1011 << 12 | parse_reg(sr) << 9 | offset

    elif opcode == "STR":
        sr, base_r, offset = parse_reg(args[0]), parse_reg(args[1]), int(args[2].replace("#", ""))
        return 0b0111 << 12 | sr << 9 | base_r << 6 | to_twos_complement(offset, 6)

    elif opcode == "TRAP":
        trapvect = TRAP_CODES.get(args[0], int(args[0], 0))
        return 0b1111 << 12 | trapvect

    elif opcode == "HALT":
        return 0b1111 << 12 | TRAP_CODES["HALT"]

    elif opcode == ".FILL":
        val = args[0]
        return int(val, 0)

    else:
        raise ValueError(f"Unsupported instruction: {opcode}")

def assemble(filepath):
    with open(filepath, "r") as f:
        lines = [line.strip().split(";")[0].strip() for line in f.readlines()]
    lines = [l for l in lines if l]

    pc = 0x3000
    labels = {}
    instructions = []

    # First pass: label resolution
    for line in lines:
        parts = line.split()
        if parts[0].endswith(":"):
            labels[parts[0][:-1]] = pc
            parts = parts[1:]
        if not parts: continue
        if parts[0] == ".ORIG":
            pc = parse_lc3_literal(parts[1])
            continue
        if parts[0] == ".END":
            break
        instructions.append((pc, parts))
        pc += 1

    # Second pass: encode
    output = []
    output.append(pc := instructions[0][0])
    for pc, parts in instructions:
        opcode = parts[0].upper()
        args = [p.strip(",") for p in parts[1:]]
        word = assemble_line(opcode, args, labels, pc)
        output.append(word)

    return output

def write_obj(output_words, filename="out.obj"):
    with open(filename, "wb") as f:
        for word in output_words:
            f.write(struct.pack('>H', word))  # Big-endian

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lc3_assembler.py input.asm")
        sys.exit(1)

    words = assemble(sys.argv[1])
    write_obj(words)
    print("Assembled successfully to out.obj")

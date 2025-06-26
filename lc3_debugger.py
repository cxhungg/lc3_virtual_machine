import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import struct
import threading
import time
from typing import Dict, Set, Optional, List, Tuple

class LC3VirtualMachine:
    
    def __init__(self):
        # Memory
        self.MAX_MEMORY = 1 << 16
        self.memory = [0] * self.MAX_MEMORY
        
        # Registers
        self.R_R0, self.R_R1, self.R_R2, self.R_R3 = 0, 1, 2, 3
        self.R_R4, self.R_R5, self.R_R6, self.R_R7 = 4, 5, 6, 7
        self.R_PC, self.R_COND, self.R_COUNT = 8, 9, 10
        self.reg = [0] * self.R_COUNT
        
        # Instruction opcodes
        self.BR, self.ADD, self.LD, self.ST = 0, 1, 2, 3
        self.JSR, self.AND, self.LDR, self.STR = 4, 5, 6, 7
        self.RTI, self.NOT, self.LDI, self.STI = 8, 9, 10, 11
        self.JMP, self.RES, self.LEA, self.TRAP = 12, 13, 14, 15
        
        # Condition flags
        self.FL_POS, self.FL_ZERO, self.FL_NEG = 1, 2, 4
        
        # Trap routines
        self.TRAP_GETC, self.TRAP_OUT = 0x20, 0x21
        self.TRAP_PUTS, self.TRAP_IN = 0x22, 0x23
        self.TRAP_PUTSP, self.TRAP_HALT = 0x24, 0x25
        
        # Memory mapped registers
        self.MR_KBSR, self.MR_KBDR = 0xFE00, 0xFE02
        
        # Debugging state
        self.running = False
        self.halted = False
        self.breakpoints: Set[int] = set()
        self.step_mode = False
        self.output_buffer = []
        self.input_buffer = []
        self.wait_for_input = False  # New flag for input waiting
        
        # Initialize
        self.reset()
    
    def reset(self):
        """Reset the virtual machine to initial state"""
        self.memory = [0] * self.MAX_MEMORY
        self.reg = [0] * self.R_COUNT
        self.reg[self.R_COND] = self.FL_ZERO
        self.reg[self.R_PC] = 0x3000
        self.running = False
        self.halted = False
        self.output_buffer = []
        self.input_buffer = []
        self.wait_for_input = False  # Reset input wait flag
    
    def sign_extend(self, x: int, num_bits: int) -> int:
        """Sign extend a value to 16 bits"""
        if (x >> (num_bits - 1)) & 1:
            x |= (0xFFFF << num_bits)
        return x & 0xFFFF
    
    def update_flags(self, r: int):
        """Update condition flags based on register value"""
        if self.reg[r] == 0:
            self.reg[self.R_COND] = self.FL_ZERO
        elif self.reg[r] >> 15:
            self.reg[self.R_COND] = self.FL_NEG
        else:
            self.reg[self.R_COND] = self.FL_POS
    
    def swap16(self, x: int) -> int:
        """Swap bytes for endianness conversion"""
        return ((x << 8) | (x >> 8)) & 0xFFFF
    
    def mem_read(self, address: int) -> int:
        """Read from memory with memory-mapped I/O handling"""
        address &= 0xFFFF
        if address == self.MR_KBSR:
            if self.input_buffer:
                self.memory[self.MR_KBSR] = 1 << 15
                self.memory[self.MR_KBDR] = ord(self.input_buffer.pop(0))
            else:
                self.memory[self.MR_KBSR] = 0
        return self.memory[address]
    
    def mem_write(self, address: int, val: int):
        """Write to memory"""
        address &= 0xFFFF
        val &= 0xFFFF
        self.memory[address] = val
    
    def load_program(self, data: bytes) -> bool:
        """Load a program from binary data"""
        if len(data) < 2:
            return False
        
        try:
            # Read origin address
            origin = struct.unpack('>H', data[:2])[0]  # Big-endian
            
            # Load program data
            program_data = data[2:]
            words = len(program_data) // 2
            
            for i in range(words):
                if origin + i >= self.MAX_MEMORY:
                    break
                word = struct.unpack('>H', program_data[i*2:(i+1)*2])[0]
                self.memory[origin + i] = word
            
            self.reg[self.R_PC] = origin
            
            return True
        except:
            return False
    
    def step(self) -> bool:
        """Execute one instruction and return True if continuing"""
        if self.halted or self.wait_for_input:
            return False
        
        # Check for breakpoint
        if self.reg[self.R_PC] in self.breakpoints and not self.step_mode:
            return False
        
        # Fetch instruction and increment PC (LC-3 spec)
        instr = self.mem_read(self.reg[self.R_PC])
        self.reg[self.R_PC] = (self.reg[self.R_PC] + 1) & 0xFFFF
        
        # Decode and execute
        op = instr >> 12
        
        if op == self.BR:
            self._execute_br(instr)
        elif op == self.ADD:
            self._execute_add(instr)
        elif op == self.LD:
            self._execute_ld(instr)
        elif op == self.ST:
            self._execute_st(instr)
        elif op == self.JSR:
            self._execute_jsr(instr)
        elif op == self.AND:
            self._execute_and(instr)
        elif op == self.LDR:
            self._execute_ldr(instr)
        elif op == self.STR:
            self._execute_str(instr)
        elif op == self.RTI:
            pass  # Not implemented
        elif op == self.NOT:
            self._execute_not(instr)
        elif op == self.LDI:
            self._execute_ldi(instr)
        elif op == self.STI:
            self._execute_sti(instr)
        elif op == self.JMP:
            self._execute_jmp(instr)
        elif op == self.RES:
            pass  # Reserved
        elif op == self.LEA:
            self._execute_lea(instr)
        elif op == self.TRAP:
            trap_result = self._execute_trap(instr)
            if trap_result == 'WAIT_FOR_INPUT':
                self.wait_for_input = True
                # Undo PC increment so the TRAP is re-executed after input
                self.reg[self.R_PC] = (self.reg[self.R_PC]-1) & 0xFFFF
                return False
            if trap_result is False:
                self.halted = True
                return False
        
        return True
    
    def _execute_br(self, instr: int):
        """Execute branch instruction"""
        pc_offset = self.sign_extend(instr & 0x1FF, 9)
        condition_flag = (instr >> 9) & 0x7
        if self.reg[self.R_COND] & condition_flag:
            self.reg[self.R_PC] = (self.reg[self.R_PC] + pc_offset) & 0xFFFF
    
    def _execute_add(self, instr: int):
        """Execute add instruction"""
        r0 = (instr >> 9) & 0x7
        r1 = (instr >> 6) & 0x7
        imm_flag = (instr >> 5) & 0x1
        
        if imm_flag:
            imm5 = self.sign_extend(instr & 0x1F, 5)
            self.reg[r0] = (self.reg[r1] + imm5) & 0xFFFF
        else:
            r2 = instr & 0x7
            self.reg[r0] = (self.reg[r1] + self.reg[r2]) & 0xFFFF
        
        self.update_flags(r0)
    
    def _execute_ld(self, instr: int):
        """Execute load instruction"""
        r0 = (instr >> 9) & 0x7
        pc_offset = self.sign_extend(instr & 0x1FF, 9)
        self.reg[r0] = self.mem_read((self.reg[self.R_PC] + pc_offset) & 0xFFFF)
        self.update_flags(r0)
    
    def _execute_st(self, instr: int):
        """Execute store instruction"""
        r0 = (instr >> 9) & 0x7
        pc_offset = self.sign_extend(instr & 0x1FF, 9)
        self.mem_write((self.reg[self.R_PC] + pc_offset) & 0xFFFF, self.reg[r0])
    
    def _execute_jsr(self, instr: int):
        """Execute jump to subroutine instruction"""
        flag = (instr >> 11) & 0x1
        self.reg[self.R_R7] = self.reg[self.R_PC]
        if flag:
            self.reg[self.R_PC] = (self.reg[self.R_PC] + self.sign_extend(instr & 0x7FF, 11)) & 0xFFFF
        else:
            r1 = (instr >> 6) & 0x7
            self.reg[self.R_PC] = self.reg[r1]
    
    def _execute_and(self, instr: int):
        """Execute bitwise AND instruction"""
        r0 = (instr >> 9) & 0x7
        r1 = (instr >> 6) & 0x7
        imm_flag = (instr >> 5) & 0x1
        
        if imm_flag:
            imm5 = self.sign_extend(instr & 0x1F, 5)
            self.reg[r0] = (self.reg[r1] & imm5) & 0xFFFF
        else:
            r2 = instr & 0x7
            self.reg[r0] = (self.reg[r1] & self.reg[r2]) & 0xFFFF
        
        self.update_flags(r0)
    
    def _execute_ldr(self, instr: int):
        """Execute load register instruction"""
        r0 = (instr >> 9) & 0x7
        r1 = (instr >> 6) & 0x7
        offset = self.sign_extend(instr & 0x3F, 6)
        self.reg[r0] = self.mem_read((self.reg[r1] + offset) & 0xFFFF)
        self.update_flags(r0)
    
    def _execute_str(self, instr: int):
        """Execute store register instruction"""
        r0 = (instr >> 9) & 0x7
        r1 = (instr >> 6) & 0x7
        offset = self.sign_extend(instr & 0x3F, 6)
        self.mem_write((self.reg[r1] + offset) & 0xFFFF, self.reg[r0])
    
    def _execute_not(self, instr: int):
        """Execute bitwise NOT instruction"""
        r0 = (instr >> 9) & 0x7
        r1 = (instr >> 6) & 0x7
        self.reg[r0] = (~self.reg[r1]) & 0xFFFF
        self.update_flags(r0)
    
    def _execute_ldi(self, instr: int):
        """Execute load indirect instruction"""
        r0 = (instr >> 9) & 0x7
        pc_offset = self.sign_extend(instr & 0x1FF, 9)
        addr = self.mem_read((self.reg[self.R_PC] + pc_offset) & 0xFFFF)
        self.reg[r0] = self.mem_read(addr)
        self.update_flags(r0)
    
    def _execute_sti(self, instr: int):
        """Execute store indirect instruction"""
        r0 = (instr >> 9) & 0x7
        pc_offset = self.sign_extend(instr & 0x1FF, 9)
        addr = self.mem_read((self.reg[self.R_PC] + pc_offset) & 0xFFFF)
        self.mem_write(addr, self.reg[r0])
    
    def _execute_jmp(self, instr: int):
        """Execute jump instruction"""
        r1 = (instr >> 6) & 0x7
        self.reg[self.R_PC] = self.reg[r1]
    
    def _execute_lea(self, instr: int):
        """Execute load effective address instruction"""
        r0 = (instr >> 9) & 0x7
        pc_offset = self.sign_extend(instr & 0x1FF, 9)
        self.reg[r0] = (self.reg[self.R_PC] + pc_offset) & 0xFFFF
        self.update_flags(r0)
    
    def _execute_trap(self, instr: int) -> bool:
        """Execute trap instruction"""
        self.reg[self.R_R7] = self.reg[self.R_PC]
        trap_code = instr & 0xFF
        
        if trap_code == self.TRAP_GETC:
            if self.input_buffer:
                self.reg[self.R_R0] = ord(self.input_buffer.pop(0))
                self.update_flags(self.R_R0)
            else:
                return 'WAIT_FOR_INPUT'
        elif trap_code == self.TRAP_OUT:
            self.output_buffer.append(chr(self.reg[self.R_R0] & 0xFF))
        elif trap_code == self.TRAP_PUTS:
            addr = self.reg[self.R_R0]
            while self.memory[addr] != 0:
                self.output_buffer.append(chr(self.memory[addr] & 0xFF))
                addr = (addr + 1) & 0xFFFF
        elif trap_code == self.TRAP_IN:
            if self.input_buffer:
                char = self.input_buffer.pop(0)
                self.output_buffer.append(char)
                self.reg[self.R_R0] = ord(char)
                self.update_flags(self.R_R0)
            else:
                return 'WAIT_FOR_INPUT'
        elif trap_code == self.TRAP_PUTSP:
            addr = self.reg[self.R_R0]
            while self.memory[addr] != 0:
                char1 = self.memory[addr] & 0xFF
                char2 = (self.memory[addr] >> 8) & 0xFF
                if char1:
                    self.output_buffer.append(chr(char1))
                if char2:
                    self.output_buffer.append(chr(char2))
                addr = (addr + 1) & 0xFFFF
        elif trap_code == self.TRAP_HALT:
            self.output_buffer.append("HALT\n")
            return False
        
        return True


class LC3Debugger:
    
    def __init__(self):
        self.vm = LC3VirtualMachine()
        self.root = tk.Tk()
        self.root.title("LC-3 Interactive Debugger")
        self.root.geometry("1200x800")
        
        # Variables
        self.running_thread = None
        self.memory_view_start = tk.IntVar(value=0x3000)
        self.memory_view_end = tk.IntVar(value=0x3020)
        
        self.setup_ui()
        self.update_display()
        self.update_memory_view()
    
    def setup_ui(self):
        """Setup the GUI layout"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Control")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(control_frame, text="Load Program", command=self.load_program).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Run", command=self.run_program).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Step", command=self.step_program).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Stop", command=self.stop_program).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Reset", command=self.reset_program).pack(side=tk.LEFT, padx=5)
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Registers and Status
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # Registers
        reg_frame = ttk.LabelFrame(left_frame, text="Registers")
        reg_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.reg_labels = {}
        reg_names = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'PC', 'COND']
        for i, name in enumerate(reg_names):
            frame = ttk.Frame(reg_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(frame, text=f"{name}:", width=6).pack(side=tk.LEFT)
            label = ttk.Label(frame, text="0x0000", font=("Courier", 10))
            label.pack(side=tk.LEFT)
            self.reg_labels[name] = label
        
        # Status
        status_frame = ttk.LabelFrame(left_frame, text="Status")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="green")
        self.status_label.pack(padx=5, pady=5)
        
        # Breakpoints
        bp_frame = ttk.LabelFrame(left_frame, text="Breakpoints")
        bp_frame.pack(fill=tk.BOTH, expand=True)
        
        bp_input_frame = ttk.Frame(bp_frame)
        bp_input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(bp_input_frame, text="Address:").pack(side=tk.LEFT)
        self.bp_entry = ttk.Entry(bp_input_frame, width=8)
        self.bp_entry.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(bp_input_frame, text="Add", command=self.add_breakpoint).pack(side=tk.LEFT, padx=(5, 0))
        
        self.bp_listbox = tk.Listbox(bp_frame, height=6)
        self.bp_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.bp_listbox.bind('<Double-Button-1>', self.remove_breakpoint)
        
        # Right panel - Memory and Output
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Memory view
        mem_frame = ttk.LabelFrame(right_frame, text="Memory View")
        mem_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        mem_control_frame = ttk.Frame(mem_frame)
        mem_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mem_control_frame, text="Start:").pack(side=tk.LEFT)
        start_entry = ttk.Entry(mem_control_frame, textvariable=self.memory_view_start, width=8)
        start_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(mem_control_frame, text="End:").pack(side=tk.LEFT)
        end_entry = ttk.Entry(mem_control_frame, textvariable=self.memory_view_end, width=8)
        end_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Button(mem_control_frame, text="Refresh", command=self.update_memory_view).pack(side=tk.LEFT, padx=(10, 0))
        
        # Memory display
        mem_display_frame = ttk.Frame(mem_frame)
        mem_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.memory_text = scrolledtext.ScrolledText(mem_display_frame, height=15, font=("Courier", 9))
        self.memory_text.pack(fill=tk.BOTH, expand=True)
        
        # Output/Console
        output_frame = ttk.LabelFrame(right_frame, text="Console Output")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=8, font=("Courier", 10))
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Input frame
        input_frame = ttk.Frame(output_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        ttk.Label(input_frame, text="Input:").pack(side=tk.LEFT)
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.input_entry.bind('<Return>', self.send_input)
        ttk.Button(input_frame, text="Send", command=self.send_input).pack(side=tk.RIGHT, padx=(5, 0))
    
    def update_display(self):
        """Update all display elements"""
        self.update_registers()
        self.update_status()
        self.update_output()
        self.update_breakpoints()
        
        # Schedule next update
        self.root.after(100, self.update_display)
    
    def update_registers(self):
        """Update register display"""
        reg_names = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'PC', 'COND']
        for i, name in enumerate(reg_names):
            if i < len(self.vm.reg):
                value = self.vm.reg[i]
                hex_val = f"0x{value:04X}"
                dec_val = f"({value})"
                
                # Highlight PC
                if name == 'PC':
                    self.reg_labels[name].config(text=f"{hex_val} {dec_val}", foreground="red")
                else:
                    self.reg_labels[name].config(text=f"{hex_val} {dec_val}", foreground="black")
    
    def update_status(self):
        """Update status display"""
        if self.vm.halted:
            self.status_label.config(text="Halted", foreground="red")
        elif self.vm.running:
            self.status_label.config(text="Running", foreground="blue")
        else:
            self.status_label.config(text="Ready", foreground="green")
    
    def update_memory_view(self):
        """Update memory view display"""
        self.memory_text.delete(1.0, tk.END)
        
        start = self.memory_view_start.get()
        end = self.memory_view_end.get()
        
        if start < 0 or end >= self.vm.MAX_MEMORY or start > end:
            self.memory_text.insert(tk.END, "Invalid memory range\n")
            return
        
        for addr in range(start, min(end + 1, self.vm.MAX_MEMORY)):
            value = self.vm.memory[addr]
            
            # Highlight current PC
            if addr == self.vm.reg[self.vm.R_PC]:
                prefix = ">> "
            elif addr in self.vm.breakpoints:
                prefix = "BP "
            else:
                prefix = "   "
            
            # Format: address: value (instruction or data)
            instr_str = self.disassemble_instruction(value)
            line = f"{prefix}0x{addr:04X}: 0x{value:04X} {instr_str}\n"
            
            self.memory_text.insert(tk.END, line)
    
    def disassemble_instruction(self, instr: int) -> str:
        """Simple disassembler for display"""
        op = instr >> 12
        opcode_names = {
            0: "BR", 1: "ADD", 2: "LD", 3: "ST", 4: "JSR", 5: "AND",
            6: "LDR", 7: "STR", 8: "RTI", 9: "NOT", 10: "LDI", 11: "STI",
            12: "JMP", 13: "RES", 14: "LEA", 15: "TRAP"
        }
        
        if op in opcode_names:
            if op == 15:  # TRAP
                trap_code = instr & 0xFF
                trap_names = {
                    0x20: "GETC", 0x21: "OUT", 0x22: "PUTS",
                    0x23: "IN", 0x24: "PUTSP", 0x25: "HALT"
                }
                return f"TRAP {trap_names.get(trap_code, f'0x{trap_code:02X}')}"
            return opcode_names[op]
        return "DATA"
    
    def update_output(self):
        """Update console output"""
        if self.vm.output_buffer:
            output = ''.join(self.vm.output_buffer)
            self.vm.output_buffer.clear()
            self.output_text.insert(tk.END, output)
            self.output_text.see(tk.END)
    
    def update_breakpoints(self):
        """Update breakpoint list"""
        self.bp_listbox.delete(0, tk.END)
        for bp in sorted(self.vm.breakpoints):
            self.bp_listbox.insert(tk.END, f"0x{bp:04X}")
    
    def load_program(self):
        """Load a program file"""
        filename = filedialog.askopenfilename(
            title="Load LC-3 Program",
            filetypes=[("LC-3 Object Files", "*.obj"), ("All Files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                
                if self.vm.load_program(data):
                    messagebox.showinfo("Success", f"Program loaded successfully from {filename}")
                    self.update_memory_view()
                    self.update_display()
                else:
                    messagebox.showerror("Error", "Failed to load program")
            except Exception as e:
                messagebox.showerror("Error", f"Error loading file: {str(e)}")
    
    def run_program(self):
        """Run the program"""
        if not self.vm.running and not self.vm.halted:
            self.vm.running = True
            self.vm.step_mode = False
            self.running_thread = threading.Thread(target=self._run_thread)
            self.running_thread.daemon = True
            self.running_thread.start()
    
    def _run_thread(self):
        """Thread for running the program"""
        while self.vm.running and not self.vm.halted:
            if not self.vm.step():
                # If we paused for input, just stop running
                self.vm.running = False
                break
            
            # Check for breakpoints
            if self.vm.reg[self.vm.R_PC] in self.vm.breakpoints:
                self.vm.running = False
                break
            
            # Small delay to prevent UI freezing
            time.sleep(0.001)
    
    def step_program(self):
        """Execute one instruction"""
        if not self.vm.halted:
            self.vm.step_mode = True
            self.vm.step()
            self.update_memory_view()
            self.update_display()
    
    def stop_program(self):
        """Stop program execution"""
        self.vm.running = False
    
    def reset_program(self):
        """Reset the virtual machine"""
        self.vm.running = False
        self.vm.reset()
        self.update_memory_view()
        self.update_display()
    
    def add_breakpoint(self):
        """Add a breakpoint"""
        try:
            addr_str = self.bp_entry.get().strip()
            if addr_str.startswith('0x'):
                addr = int(addr_str, 16)
            else:
                addr = int(addr_str)
            
            if 0 <= addr < self.vm.MAX_MEMORY:
                self.vm.breakpoints.add(addr)
                self.bp_entry.delete(0, tk.END)
                self.update_breakpoints()
                self.update_memory_view()
            else:
                messagebox.showerror("Error", "Address out of range")
        except ValueError:
            messagebox.showerror("Error", "Invalid address format")
    
    def remove_breakpoint(self, event=None):
        """Remove selected breakpoint"""
        selection = self.bp_listbox.curselection()
        if selection:
            addr_str = self.bp_listbox.get(selection[0])
            addr = int(addr_str, 16)
            self.vm.breakpoints.discard(addr)
            self.update_breakpoints()
            self.update_memory_view()
    
    def send_input(self, event=None):
        """Send input to the virtual machine"""
        text = self.input_entry.get()
        if text:
            for char in text:
                self.vm.input_buffer.append(char)
            self.input_entry.delete(0, tk.END)
            self.output_text.insert(tk.END, f"Input: {text}\n")
            self.output_text.see(tk.END)
            self.update_output()
            # Resume execution if VM was waiting for input
            if not self.vm.halted and self.vm.wait_for_input:
                self.vm.wait_for_input = False
                self.run_program()
    
    def run(self):
        """Start the GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass


def main():
    """Main function"""
    print("LC-3 Interactive Debugger")
    print("Features:")
    print("- Load LC-3 object files")
    print("- Step-by-step execution")
    print("- Breakpoints")
    print("- Real-time register and memory viewing")
    print("- Console I/O simulation\n")
    print("Starting debugger GUI...")
    
    # Start the debugger
    debugger = LC3Debugger()
    debugger.run()


if __name__ == "__main__":
    main()
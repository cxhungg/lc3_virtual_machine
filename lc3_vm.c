#include <stdio.h>
#include <stdint.h>
#include <signal.h>
/* windows only */
#include <Windows.h>
#include <conio.h>  // _kbhit


#define MAX_MEMORY (1 << 16)  // this shifts the 1 to the left by 16 places
uint16_t memory[MAX_MEMORY];  // memory is stored in a an array with 65536 (2^16) locations, where each location can store 16 bits

//registers----------------------------------------------------------------------------------

enum {

    R_R0 = 0,
    R_R1,
    R_R2,
    R_R3,
    R_R4,
    R_R5,
    R_R6,
    R_R7,
    R_PC,
    R_COND,
    R_COUNT
};

uint16_t reg[R_COUNT];  // creating an array called reg, that has 11 locations, each able to store 16 bits of data

// instruction set----------------------------------------------------------------------------------

enum {

    BR = 0,
    ADD,
    LD,
    ST,
    JSR,
    AND,
    LDR,
    STR,
    RTI,
    NOT,
    LDI,
    STI,
    JMP,
    RES,
    LEA,
    TRAP

};

//condition flags----------------------------------------------------------------------------------

enum {
    //represent individual bits in a bit field, allowing the use of bitwise operations to store and check multiple flags efficiently in a single integer

    FL_POS = 1,  // 0001
    FL_ZERO = 2, // 0010
    FL_NEG = 4   // 0100

    //this way we can easily
    /*
    
    Set a flag: flags |= FL_POS;

    Clear a flag: flags &= ~FL_POS;

    Check a flag: if (flags & FL_POS) {...}

    */

    /*
    this is a more standard way of writing it

    FL_POS = 1 << 0, 
    FL_ZERO = 1 << 1, 
    FL_NEG = 1 << 2, 
    
    */

};

int read_image(const char* image_path);
uint16_t sign_extend(uint16_t x, int num_bits);
void update_flags(uint16_t r);


int main(int argc, const char*argv[]){

    // (load arguments)
    if (argc < 2){
        printf("enter in this format: lc3 [image-file] ... \n");
        exit(2);
    }

    for (int i = 1; i < argc; i++){
        if(!read_image(argv[i])){
            printf("failed to load image: %s\n", argv[i]);
            exit(1);
        }
    }


    // (setup)

    reg[R_COND] = FL_ZERO;

    enum { PC_START = 0x3000 }; // this is to declare a local constant in C
    //can also do this #define PC_START 0x3000 , but this is global, and its not necessary for this variable to be global

    reg[R_PC] = PC_START;
    
    int running = 1;
    while(running){

        uint16_t instr = mem_read(reg[R_PC]++);
        uint16_t op = instr >> 12; // extracts the top 4 bits to determine the opcode

        switch(op){

            case BR:
            {
                uint16_t pc_offset = sign_extend(instr & 0x1FF,9);
                uint16_t condition_flag = (instr >> 9) & 0x7;
                if (reg[R_COND] & condition_flag){
                    reg[R_PC] += pc_offset;
                }
            }
                break;
            case ADD:
            {
                // this is the destination register (DR)
                uint16_t r0 = instr >> 9 & 0b0111;  // we and this with 0111 to remove the leading 1 since the opcode binary for add is 0001. This will result in just the number of the register
                
                // this is the first operand (SR1)
                uint16_t r1 = instr >> 6 &0b111;

                // to check if its add immediate or just add between registers
                uint16_t imm_flag = instr >> 5 & 0b1;

                uint16_t r2;
                //this is the second operand (SR2)
                if (imm_flag) {
                    r2 = instr & 0b11111;    
                } else {
                    r2 = instr & 0b111;
                }
                
                reg[r0] = reg[r1] + reg[r2];
                update_flags(r0);
            }
                break;
            case LD:
            {
                uint16_t r0 = (instr >> 9) & 0x7;
                uint16_t pc_offset = sign_extend(instr & 0x1FF,9);
                reg[r0] = mem_read(reg[R_PC]+pc_offset);
                update_flags(r0);
            }
                break;
            case ST:
                break;
            case JSR:
            {
                uint16_t flag = (instr >> 11) & 0b1;
                if (flag){
                    reg[R_PC] += sign_extend((instr & 0x7FF),11);
                }
                else {
                    uint16_t r1 = (instr >> 6) & 0x7;
                    reg[R_PC] = reg[r1];
                }
            }
                break;
            case AND:
            {
                //destination register (DR)
                uint16_t r0 = instr >> 9 & 0x7;
                uint16_t imm_flag = (instr >> 5) & 0b1;
                uint16_t r1 = (instr >> 6) & 0x7;
                uint16_t result;
                if (imm_flag){
                    uint16_t imm_val = sign_extend(instr & 0b11111,5);
                    result = reg[r1] & imm_val;
                } else {
                    uint16_t r2 = instr & 0x7;
                    result = reg[r1] & reg[r2];
                }
                reg[r0] = result;
                update_flags(r0);
            }
                break;
            case LDR:
            {
                uint16_t r0 = (instr >> 9) & 0x7;
                uint16_t r1 = (instr >> 6) & 0x7;

                uint16_t offset = sign_extend((instr & 0b111111),6);
                reg[r0] = mem_read(reg[r1] + offset);
                update_flags(r0);
            }
                break;
            case STR:
                break;
            case RTI:
                break;
            case NOT:
            {
                // destination register (DR)
                uint16_t r0 = (instr >> 9) & 0x7;
                uint16_t r1 = (instr >> 6) & 0x7;
                reg[r0] = ~reg[r1];
                update_flags(r0);
            }
                break;  
            case LDI:
                {
                    // destination register (DR)
                    uint16_t r0 = (instr >> 9) & 0x7;

                    //get PCoffset9 and sign extend it
                    uint16_t pc_offset = sign_extend(instr& 0b000000111111111,9);

                    reg[r0] = mem_read(mem_read(reg[R_PC]+pc_offset));
                    update_flags(r0);

                }
                break;
            case STI:
                break;
            case JMP:
            {
                reg[R_PC] = reg[(instr >> 6) & 0x7];
            }
                break;
            case RES:
                break;
            case LEA:
                break;
            case TRAP:
                break;
            default:
                break;
        }
    }
}
            

uint16_t sign_extend(uint16_t x, int num_bits){

    int most_significant_bit = x>>(num_bits - 1); //for example 10110, shifted 4 bits to the right would just be 1, and 1 & 1 is 1

    if (most_significant_bit & 1){ // this means x is negative

        // computation is done in 32 bits or more
        x |= (0xFFFF << num_bits);  //automatically truncates the result to 16 bits when result is stored in x
    }
    return x;
};

void update_flags(uint16_t r){

    if (reg[r]==0){
        reg[R_COND] = FL_ZERO;
    } else if (reg[r]>>15){
        reg[R_COND] = FL_NEG;
    } else {
        reg[R_COND] = FL_POS;
    }

}
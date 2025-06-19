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

    BR = 0, /* branch */
    ADD,    /* add  */
    LD,     /* load */
    ST,     /* store */
    JSR,    /* jump register */
    AND,    /* bitwise and */
    LDR,    /* load register */
    STR,    /* store register */
    RTI,    /* unused */
    NOT,    /* bitwise not */
    LDI,    /* load indirect */
    STI,    /* store indirect */
    JMP,    /* jump */
    RES,    /* reserved (unused) */
    LEA,    /* load effective address */
    TRAP    /* execute trap */

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


enum {

    // trap routines

    TRAP_GETC = 0x20,   // get character from keyboard, not echoed onto the terminal , 0b00100000
    TRAP_OUT = 0x21,    // output a character  0b00100001
    TRAP_PUTS = 0x22,   // output a word string     0b00100010
    TRAP_IN = 0x23,     // get character from keyboard, echoed onto the terminal        0b00100011
    TRAP_PUTSP = 0x24,  // output a byte program    0b00100100
    TRAP_HALT = 0x25    // halt the program     0b00100101

};

//memory mapped registers----------------------------------------------------------------------------------

enum
{
    MR_KBSR = 0xFE00, // keyboard status
    MR_KBDR = 0xFE02  // keyboard data 
};





HANDLE hStdin = INVALID_HANDLE_VALUE;
DWORD fdwMode, fdwOldMode;

void disable_input_buffering()
{
    hStdin = GetStdHandle(STD_INPUT_HANDLE);
    GetConsoleMode(hStdin, &fdwOldMode); /* save old mode */
    // fdwMode = fdwOldMode;
    // fdwMode &= ~(ENABLE_ECHO_INPUT | ENABLE_LINE_INPUT);
    fdwMode = fdwOldMode
            ^ ENABLE_ECHO_INPUT  /* no input echo */
            ^ ENABLE_LINE_INPUT; /* return when one or
                                    more characters are available */
    SetConsoleMode(hStdin, fdwMode); /* set new mode */
    FlushConsoleInputBuffer(hStdin); /* clear buffer */
}

void restore_input_buffering()
{
    SetConsoleMode(hStdin, fdwOldMode);
}

uint16_t check_key()
{
    return WaitForSingleObject(hStdin, 1000) == WAIT_OBJECT_0 && _kbhit();
}



void handle_interrupt(int signal)
{
    restore_input_buffering();
    printf("\n");
    exit(-2);
}


int read_image(const char* image_path);
uint16_t sign_extend(uint16_t x, int num_bits);
void update_flags(uint16_t r);
uint16_t mem_read(uint16_t address);
void mem_write(uint16_t address, uint16_t val);
uint16_t swap16(uint16_t x);
void read_image_file(FILE* file);

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
    signal(SIGINT, handle_interrupt);
    disable_input_buffering();

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
                uint16_t r0 = (instr >> 9) & 0b0111;  // we and this with 0111 to remove the leading 1 since the opcode binary for add is 0001. This will result in just the 
                //number of the register
                
                // this is the first operand (SR1)
                uint16_t r1 = (instr >> 6) &0b111;

                // to check if its add immediate or just add between registers
                uint16_t imm_flag = (instr >> 5) & 0b1;

                
                //this is the second operand (SR2)
                if (imm_flag) {
                    uint16_t imm5 = sign_extend(instr & 0b11111,5); 
                    reg[r0] = reg[r1] + imm5;   
                } else {
                    uint16_t r2 = instr & 0b111;
                    reg[r0] = reg[r1] + reg[r2];
                }
                
                
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
            {
                uint16_t r0 = (instr >> 9) & 0x7;
                 
                uint16_t offset = sign_extend(instr & 0b111111111,9);
                mem_write(reg[R_PC]+offset,reg[r0]);
            }
                break;
            case JSR:
            {
                uint16_t flag = (instr >> 11) & 0b1;
                reg[R_R7] = reg[R_PC];
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
                uint16_t r0 = (instr >> 9) & 0x7;
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
            {
                    uint16_t r0 = (instr >> 9) & 0x7;
                    uint16_t r1 = (instr >> 6) & 0x7;
                    uint16_t offset = sign_extend(instr & 0x3F, 6);
                    mem_write(reg[r1] + offset, reg[r0]);
            }
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
            {
                    // destination register (DR)
                    uint16_t r0 = (instr >> 9) & 0x7;

                    //get PCoffset9 and sign extend it
                    uint16_t pc_offset = sign_extend(instr& 0b000000111111111,9);

                    mem_write(mem_read(reg[R_PC]+pc_offset),reg[r0]);
                    
            }
                break;
            case JMP:
            {
                reg[R_PC] = reg[(instr >> 6) & 0x7];
            }
                break;
            case RES:
                break;
            case LEA:
            {
                uint16_t r0 = (instr >> 9) & 0x7;
                uint16_t offset = sign_extend((instr & 0x1FF),9);
                reg[r0] = reg[R_PC] + offset;
                update_flags(r0); 
            }
                break;
            case TRAP:
                reg[R_R7] = reg[R_PC];
                
                switch (instr & 0xFF)
                {
                    case TRAP_GETC:
                        // reads a single ASCII char
                        reg[R_R0] = (uint16_t)getchar();

                        //Reads a single character from input without echo
                        //Stores it in R0
                        //Updates condition flags based on the character's value

                        update_flags(R_R0);
                        break;
                    case TRAP_OUT:
                        putc((char)reg[R_R0], stdout);
                        fflush(stdout);
                        /*
                        Outputs the character in R0 to the screen.
                        fflush(stdout) ensures it is shown immediately.
                        */
                        break;
                    case TRAP_PUTS:
                        {
                            // one char per 16 bit word
                            uint16_t* c = memory + reg[R_R0]; // memory is a pointer to the first element of the memory array
                            while (*c)
                            {
                                putc((char)*c, stdout);
                                //Casts the 16-bit word to an 8-bit char, which is what putc() expects
                                //Sends it to stdout (standard output)
                                //This prints one character to the screen


                                c++; //Move to the next word in memory, because c is a uint16_t*, this increments by 2 bytes, advancing to the next character
                            }
                            fflush(stdout); // make sure that all buffered output is immediately displayed to the screen
                        }
                        break;
                    case TRAP_IN:
                        {
                            printf("Enter a character: "); //prompt user to enter a character
                            char c = getchar();
                            putc(c, stdout);    //echoes it back
                            fflush(stdout);
                            reg[R_R0] = (uint16_t)c;        // stores it in R0
                            update_flags(R_R0);         // updates flags
                        }
                        break;
                    case TRAP_PUTSP:
                        {

                            /*
                            The TRAP_PUTSP routine in the LC-3 emulator is used to print strings stored in memory with two characters per word, also known as packed strings. This is more space-efficient than TRAP_PUTS, which uses one character per 16-bit word.
                            */

                            //for example

                            /*
                            memory[0x3000] = 0x6548; // 'H' (0x48), 'e' (0x65)
                            memory[0x3001] = 0x6C6C; // 'l', 'l'
                            memory[0x3002] = 0x006F; // 'o', '\0'
                            reg[R_R0] = 0x3000;

                            */

                            //storing characters this way is more space efficient 

                            uint16_t* c = memory + reg[R_R0];  // c points to the first word of the packed string 
                            while (*c)
                            {
                                char char1 = (*c) & 0xFF;   //Extracts the low-order byte (bits 0–7) from the 16-bit word, the first character stored in the word
                                putc(char1, stdout);        //Prints the first character to the screen
                                char char2 = (*c) >> 8;     //Extracts the high-order byte (bits 8–15) from the word, this is the second character
                                if (char2){
                                    putc(char2, stdout);    //only print the second character if it is non-zero
                                }    
                                c++;    //Move to the next word in memory
                            }
                            fflush(stdout);
                        }
                        break;
                    case TRAP_HALT:
                        puts("HALT");
                        fflush(stdout);
                        running = 0;        // stops the execution loop by setting running to 0
                        break;

                }

                break;
            default:
                abort();
                break;
        }
    }
    restore_input_buffering();
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

//LC-3 programs are big-endian, but most modern computers are little-endian. So, we need to swap each uint16 that is loaded
uint16_t swap16(uint16_t x){
    return (x << 8) | (x >> 8);     //this reverses the byte order of a 16-bit value

    /*
    
    x << 8: Shifts the lower byte to the upper byte position

    0x1234 << 8 = 0x3400

    x >> 8: Shifts the upper byte to the lower byte position

    0x1234 >> 8 = 0x0012

    Combine them with bitwise OR 

    0x3400 | 0x0012 = 0x3412
    
    */


}

void read_image_file(FILE* file){
    //the code for reading an LC-3 program into memory

    uint16_t origin;
    fread(&origin, sizeof(origin), 1, file);  //reads the first 16 bits of the file into origin
    origin = swap16(origin);

    uint16_t max_read = MAX_MEMORY - origin;  //computes how many words we can safely load without going out of bounds.

    uint16_t* p = memory + origin;  //p now points to the memory address where the program should begin loading e.g., memory[0x3000]
    size_t read = fread(p, sizeof(uint16_t), max_read, file); //reads up to max_read 16-bit words from the file into memory, starting at p

    // swap to little endian
    while (read-- > 0)
    {
        *p = swap16(*p);
        ++p;
    }


}


int read_image(const char* image_path){
    FILE* file = fopen(image_path, "rb");
    if (!file){
        return 0;
        };
    read_image_file(file);
    fclose(file);
    return 1;
}



void mem_write(uint16_t address, uint16_t val)
{
    memory[address] = val;
}

uint16_t mem_read(uint16_t address)
{
    if (address == MR_KBSR)
    {
        if (check_key())
        {
            memory[MR_KBSR] = (1 << 15);
            memory[MR_KBDR] = getchar();
        }
        else
        {
            memory[MR_KBSR] = 0;
        }
    }
    return memory[address];
}
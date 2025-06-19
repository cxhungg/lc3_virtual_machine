;; LC-3 Assembly: 2048 Game
;; A simplified implementation of the 2048 puzzle game
;; Controls: W/A/S/D for up/left/down/right movement
;; Goal: Combine tiles to reach 2048

.ORIG x3000

;; Game initialization
MAIN:
    JSR INIT_GAME           ; Initialize the game board
    JSR DISPLAY_BOARD       ; Show initial board
    
GAME_LOOP:
    JSR GET_INPUT           ; Get player input
    JSR PROCESS_MOVE        ; Process the move
    JSR ADD_RANDOM_TILE     ; Add new random tile
    JSR DISPLAY_BOARD       ; Update display
    JSR CHECK_WIN           ; Check for win condition
    JSR CHECK_LOSE          ; Check for lose condition
    BR GAME_LOOP

;; Initialize game board (4x4 grid)
;; Board stored as 16 consecutive memory locations
INIT_GAME:
    ST R7, SAVE_R7_1        ; Save return address
    
    ;; Clear the board
    LEA R0, BOARD
    AND R1, R1, #0          ; Clear value
    ADD R2, R0, #15         ; End of board
    
CLEAR_LOOP:
    STR R1, R0, #0          ; Store 0
    ADD R0, R0, #1          ; Next position
    NOT R3, R2
    ADD R3, R3, #1
    ADD R3, R0, R3          ; Compare with end
    BRnz CLEAR_LOOP
    
    ;; Add two initial tiles
    JSR ADD_RANDOM_TILE
    JSR ADD_RANDOM_TILE
    
    LD R7, SAVE_R7_1
    RET

;; Display the game board
DISPLAY_BOARD:
    ST R7, SAVE_R7_2
    
    ;; Clear screen and print header
    LEA R0, CLEAR_SCREEN
    PUTS
    LEA R0, HEADER
    PUTS
    
    ;; Print board (4x4 grid)
    LEA R1, BOARD           ; Board pointer
    AND R2, R2, #0          ; Row counter
    
ROW_LOOP:
    LEA R0, ROW_SEPARATOR
    PUTS
    LEA R0, PIPE_CHAR
    PUTS
    
    AND R3, R3, #0          ; Column counter
    
COL_LOOP:
    LDR R4, R1, #0          ; Load tile value
    ADD R4, R4, #0          ; Test if zero
    BRz PRINT_EMPTY
    
    ;; Print tile value
    JSR PRINT_NUMBER
    BR NEXT_COL
    
PRINT_EMPTY:
    LEA R0, EMPTY_TILE
    PUTS
    
NEXT_COL:
    LEA R0, PIPE_CHAR
    PUTS
    ADD R1, R1, #1          ; Next tile
    ADD R3, R3, #1          ; Increment column
    ADD R4, R3, #-4         ; Check if end of row
    BRn COL_LOOP
    
    LD R0, NEWLINE
    OUT
    
    ADD R2, R2, #1          ; Next row
    ADD R4, R2, #-4         ; Check if end of board
    BRn ROW_LOOP
    
    LEA R0, ROW_SEPARATOR
    PUTS
    LEA R0, CONTROLS
    PUTS
    
    LD R7, SAVE_R7_2
    RET

;; Get player input (W/A/S/D)
GET_INPUT:
    ST R7, SAVE_R7_3
    
INPUT_LOOP:
    LEA R0, INPUT_PROMPT
    PUTS
    GETC
    OUT
    LD R1, NEWLINE
    ADD R1, R1, #0
    OUT
    
    ;; Convert to uppercase if lowercase
    ADD R1, R0, #-97        ; Check if >= 'a'
    BRn CHECK_DIRECTION
    ADD R1, R0, #-122       ; Check if <= 'z'  
    BRp CHECK_DIRECTION
    ADD R0, R0, #-32        ; Convert to uppercase
    
CHECK_DIRECTION:
    ;; Store direction in MOVE_DIRECTION
    LD R1, CHAR_W
    NOT R1, R1
    ADD R1, R1, #1
    ADD R1, R0, R1          ; Compare with 'W'
    BRz SET_UP
    
    LD R1, CHAR_A
    NOT R1, R1
    ADD R1, R1, #1
    ADD R1, R0, R1          ; Compare with 'A'
    BRz SET_LEFT
    
    LD R1, CHAR_S
    NOT R1, R1
    ADD R1, R1, #1
    ADD R1, R0, R1          ; Compare with 'S'
    BRz SET_DOWN
    
    LD R1, CHAR_D
    NOT R1, R1
    ADD R1, R1, #1
    ADD R1, R0, R1          ; Compare with 'D'
    BRz SET_RIGHT
    
    ;; Invalid input
    LEA R0, INVALID_INPUT
    PUTS
    BR INPUT_LOOP
    
SET_UP:
    AND R0, R0, #0
    ST R0, MOVE_DIRECTION   ; 0 = up
    BR INPUT_DONE
    
SET_LEFT:
    AND R0, R0, #0
    ADD R0, R0, #1
    ST R0, MOVE_DIRECTION   ; 1 = left
    BR INPUT_DONE
    
SET_DOWN:
    AND R0, R0, #0
    ADD R0, R0, #2
    ST R0, MOVE_DIRECTION   ; 2 = down
    BR INPUT_DONE
    
SET_RIGHT:
    AND R0, R0, #0
    ADD R0, R0, #3
    ST R0, MOVE_DIRECTION   ; 3 = right
    
INPUT_DONE:
    LD R7, SAVE_R7_3
    RET

;; Process move based on direction
PROCESS_MOVE:
    ST R7, SAVE_R7_4
    
    LD R0, MOVE_DIRECTION
    ADD R0, R0, #0          ; Test direction
    BRz MOVE_UP
    ADD R0, R0, #-1
    BRz MOVE_LEFT
    ADD R0, R0, #-1
    BRz MOVE_DOWN
    BR MOVE_RIGHT           ; Must be right
    
MOVE_UP:
    JSR SLIDE_UP
    BR PROCESS_DONE
    
MOVE_LEFT:
    JSR SLIDE_LEFT
    BR PROCESS_DONE
    
MOVE_DOWN:
    JSR SLIDE_DOWN
    BR PROCESS_DONE
    
MOVE_RIGHT:
    JSR SLIDE_RIGHT
    
PROCESS_DONE:
    LD R7, SAVE_R7_4
    RET

;; Slide tiles left (simplified implementation)
SLIDE_LEFT:
    ST R7, SAVE_R7_5
    
    LEA R0, BOARD
    AND R1, R1, #0          ; Row counter
    
SLIDE_LEFT_ROW:
    ;; For each row, compact non-zero tiles to the left
    ADD R2, R0, #0          ; Current row start
    AND R3, R3, #0          ; Write position
    AND R4, R4, #0          ; Read position
    
SLIDE_LEFT_COL:
    ADD R5, R2, R4          ; Current read position
    LDR R6, R5, #0          ; Load tile value
    
    ADD R6, R6, #0          ; Check if non-zero
    BRz SKIP_TILE
    
    ;; Move tile to write position
    ADD R5, R2, R3          ; Write position
    STR R6, R5, #0          ; Store tile
    ADD R3, R3, #1          ; Increment write position
    
SKIP_TILE:
    ADD R4, R4, #1          ; Next read position
    ADD R6, R4, #-4         ; Check if end of row
    BRn SLIDE_LEFT_COL
    
    ;; Clear remaining positions in row
CLEAR_ROW:
    ADD R6, R3, #-4         ; Check if row is full
    BRzp NEXT_SLIDE_ROW
    ADD R5, R2, R3          ; Position to clear
    AND R6, R6, #0
    STR R6, R5, #0          ; Clear position
    ADD R3, R3, #1
    BR CLEAR_ROW
    
NEXT_SLIDE_ROW:
    ADD R0, R0, #4          ; Next row
    ADD R1, R1, #1          ; Increment row counter
    ADD R6, R1, #-4         ; Check if done
    BRn SLIDE_LEFT_ROW
    
    LD R7, SAVE_R7_5
    RET

;; Simplified versions of other slide functions
SLIDE_RIGHT:
SLIDE_UP:
SLIDE_DOWN:
    ;; For now, just call slide_left (placeholder)
    JSR SLIDE_LEFT
    RET

;; Add a random tile (2 or 4) to an empty position
ADD_RANDOM_TILE:
    ST R7, SAVE_R7_6
    
    ;; Find empty positions
    LEA R0, BOARD
    AND R1, R1, #0          ; Position counter
    AND R2, R2, #0          ; Empty count
    
COUNT_EMPTY:
    LDR R3, R0, #0          ; Load tile
    ADD R3, R3, #0          ; Check if empty
    BRnp NOT_EMPTY
    ADD R2, R2, #1          ; Count empty
    
NOT_EMPTY:
    ADD R0, R0, #1          ; Next position
    ADD R1, R1, #1          ; Increment counter
    ADD R3, R1, #-16        ; Check if done
    BRn COUNT_EMPTY
    
    ;; If no empty positions, return
    ADD R2, R2, #0
    BRz ADD_TILE_DONE
    
    ;; Place tile in first empty position (simplified)
    LEA R0, BOARD
    AND R1, R1, #0
    
FIND_EMPTY:
    LDR R3, R0, R1          ; Load tile
    ADD R3, R3, #0          ; Check if empty
    BRz PLACE_TILE
    ADD R1, R1, #1          ; Next position
    BR FIND_EMPTY
    
PLACE_TILE:
    AND R3, R3, #0
    ADD R3, R3, #2          ; Place tile with value 2
    STR R3, R0, R1
    
ADD_TILE_DONE:
    LD R7, SAVE_R7_6
    RET

;; Print a number (simplified - handles values 2, 4, 8, 16, 32, 64)
PRINT_NUMBER:
    ST R7, SAVE_R7_7
    ST R0, SAVE_R0
    
    ADD R4, R4, #-2
    BRz PRINT_2
    ADD R4, R4, #-2
    BRz PRINT_4
    ADD R4, R4, #-4
    BRz PRINT_8
    ADD R4, R4, #-8
    BRz PRINT_16
    
    ;; Default case - print as single digit
    LD R0, SAVE_R0
    ADD R0, R0, #48         ; Convert to ASCII
    OUT
    LEA R0, SPACE_CHAR
    PUTS
    BR PRINT_NUM_DONE
    
PRINT_2:
    LEA R0, NUM_2
    PUTS
    BR PRINT_NUM_DONE
    
PRINT_4:
    LEA R0, NUM_4
    PUTS
    BR PRINT_NUM_DONE
    
PRINT_8:
    LEA R0, NUM_8
    PUTS
    BR PRINT_NUM_DONE
    
PRINT_16:
    LEA R0, NUM_16
    PUTS
    
PRINT_NUM_DONE:
    LD R7, SAVE_R7_7
    RET

;; Check win condition (simplified)
CHECK_WIN:
    ;; For now, just return (placeholder)
    RET

;; Check lose condition (simplified)  
CHECK_LOSE:
    ;; For now, just return (placeholder)
    RET

;; Data section
MOVE_DIRECTION: .FILL #0
NEWLINE:        .FILL x0A
CHAR_W:         .FILL #87
CHAR_A:         .FILL #65
CHAR_S:         .FILL #83
CHAR_D:         .FILL #68

;; Save registers
SAVE_R7_1:      .FILL #0
SAVE_R7_2:      .FILL #0
SAVE_R7_3:      .FILL #0
SAVE_R7_4:      .FILL #0
SAVE_R7_5:      .FILL #0
SAVE_R7_6:      .FILL #0
SAVE_R7_7:      .FILL #0
SAVE_R0:        .FILL #0

;; Game board (4x4 = 16 tiles)
BOARD:          .BLKW #16

;; String messages
CLEAR_SCREEN:   .STRINGZ "\n\n\n"
HEADER:         .STRINGZ "=== 2048 Game ===\n"
ROW_SEPARATOR:  .STRINGZ "+----+----+----+----+\n"
PIPE_CHAR:      .STRINGZ "|"
EMPTY_TILE:     .STRINGZ "    "
SPACE_CHAR:     .STRINGZ " "
CONTROLS:       .STRINGZ "\nControls: W(up) A(left) S(down) D(right)\n"
INPUT_PROMPT:   .STRINGZ "Enter move: "
INVALID_INPUT:  .STRINGZ "Invalid input! Use W/A/S/D\n"

;; Number strings for display
NUM_2:          .STRINGZ "  2 "
NUM_4:          .STRINGZ "  4 "
NUM_8:          .STRINGZ "  8 "
NUM_16:         .STRINGZ " 16 "

.END
;; LC-3 Assembly: Guess the Number Game
;; A simple game where the player tries to guess a secret number (1-9)
;; Tests: I/O operations, branching, loops, arithmetic, memory operations

.ORIG x3000

;; Initialize game
START:
    LEA R0, WELCOME_MSG     ; Load welcome message
    PUTS                    ; Print welcome message
    
    LD R1, SECRET_NUM       ; Load the secret number (5)
    AND R2, R2, #0          ; Clear guess counter
    
GAME_LOOP:
    ;; Print prompt
    LEA R0, PROMPT_MSG
    PUTS
    
    ;; Get user input
    GETC                    ; Get character from keyboard
    ADD R4, R0, #0          ; Save original character in R4
    OUT                     ; Echo the character
    
    ;; Print newline
    LD R0, NEWLINE
    OUT
    
    ;; Convert ASCII to number (subtract '0')
    ADD R0, R4, #0          ; Restore original character
    LD R3, ASCII_OFFSET     ; Load -48 (negative of ASCII '0')
    ADD R0, R0, R3          ; Convert ASCII to digit
    
    ;; Check if input is valid (1-9)
    ADD R3, R0, #-1         ; Check if < 1
    BRn INVALID_INPUT
    ADD R3, R0, #-9         ; Check if > 9
    BRp INVALID_INPUT
    
    ;; Increment guess counter
    ADD R2, R2, #1
    
    ;; Compare guess with secret number
    NOT R3, R1              ; Get two's complement of secret
    ADD R3, R3, #1
    ADD R3, R0, R3          ; guess - secret
    
    BRz CORRECT_GUESS       ; If zero, correct guess
    BRn TOO_LOW             ; If negative, guess too low
    BRp TOO_HIGH            ; If positive, guess too high
    
TOO_LOW:
    LEA R0, LOW_MSG
    PUTS
    BR GAME_LOOP
    
TOO_HIGH:
    LEA R0, HIGH_MSG
    PUTS
    BR GAME_LOOP
    
CORRECT_GUESS:
    LEA R0, CORRECT_MSG
    PUTS
    
    ;; Display number of guesses
    LEA R0, GUESSES_MSG
    PUTS
    
    ;; Convert guess count to ASCII and display
    LD R3, ASCII_ZERO       ; Load ASCII '0'
    ADD R0, R2, R3          ; Convert to ASCII
    OUT
    
    LD R0, NEWLINE
    OUT
    
    ;; Ask if player wants to play again
    LEA R0, PLAY_AGAIN_MSG
    PUTS
    
    GETC                    ; Get response
    OUT                     ; Echo response
    
    LD R0, NEWLINE
    OUT
    
    ;; Check if 'y' or 'Y'
    LD R3, LOWER_Y          ; Load 'y' (ASCII 121)
    NOT R3, R3
    ADD R3, R3, #1
    ADD R3, R0, R3          ; Compare with input
    BRz RESTART
    
    LD R3, UPPER_Y          ; Load 'Y' (ASCII 89)  
    NOT R3, R3
    ADD R3, R3, #1
    ADD R3, R0, R3          ; Compare with input
    BRz RESTART
    
    ;; End game
    LEA R0, GOODBYE_MSG
    PUTS
    HALT
    
RESTART:
    ;; Reset guess counter and start over
    AND R2, R2, #0
    BR START
    
INVALID_INPUT:
    LEA R0, INVALID_MSG
    PUTS
    BR GAME_LOOP

;; Data section
SECRET_NUM:     .FILL #5
NEWLINE:        .FILL x0A
ASCII_OFFSET:   .FILL #-48      ; For converting ASCII to digit
ASCII_ZERO:     .FILL #48       ; ASCII value of '0'
LOWER_Y:        .FILL #121      ; ASCII value of 'y'
UPPER_Y:        .FILL #89       ; ASCII value of 'Y'

;; String messages
WELCOME_MSG:    .STRINGZ "Welcome to Guess the Number!\nI'm thinking of a number between 1 and 9.\n"
PROMPT_MSG:     .STRINGZ "Enter your guess: "
LOW_MSG:        .STRINGZ "Too low! Try again.\n"
HIGH_MSG:       .STRINGZ "Too high! Try again.\n"
CORRECT_MSG:    .STRINGZ "Congratulations! You got it!\n"
GUESSES_MSG:    .STRINGZ "You guessed it in "
PLAY_AGAIN_MSG: .STRINGZ "Play again? (y/n): "
GOODBYE_MSG:    .STRINGZ "Thanks for playing!\n"
INVALID_MSG:    .STRINGZ "Invalid input! Enter a number 1-9.\n"

.END
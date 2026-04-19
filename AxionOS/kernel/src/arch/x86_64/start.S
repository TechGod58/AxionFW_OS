\
.global _start
.extern kmain

.section .text
_start:
    mov $0x3f8, %dx
    mov $'K', %al
    outb %al, (%dx)
    mov $'E', %al
    outb %al, (%dx)
    mov $'R', %al
    outb %al, (%dx)
    mov $'N', %al
    outb %al, (%dx)
    mov $'_', %al
    outb %al, (%dx)
    mov $'E', %al
    outb %al, (%dx)
    mov $'N', %al
    outb %al, (%dx)
    mov $'T', %al
    outb %al, (%dx)
    mov $'R', %al
    outb %al, (%dx)
    mov $'Y', %al
    outb %al, (%dx)
    mov $'\n', %al
    outb %al, (%dx)

    mov %rdi, %rsi
    lea stack_top(%rip), %rsp
    mov %rsi, %rdi
    call kmain
.hang:
    hlt
    jmp .hang

.section .bss
    .align 16
stack:
    .skip 16384
stack_top:

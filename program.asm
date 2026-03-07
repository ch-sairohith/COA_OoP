.data
arr: .word 9,5,3,8,1,6,2,7,4,0,15,11,14,13,12,19,18,17,16,10
n:   .word 20
one: .word 1
four:.word 4
zero:.word 0

.text

la x10, arr
la x5, n
lw x11, 0(x5)        # n

la x5, zero
lw x12, 0(x5)        # i = 0

outer_loop:
slt x20, x12, x11
beq x20, x0, print_array

la x5, zero
lw x13, 0(x5)        # j = 0

addi x14, x11, -1
sub x14, x14, x12    # limit = n-1-i

add x16, x10, x0     # pointer = base address

inner_loop:
slt x21, x13, x14
beq x21, x0, next_outer

lw x17, 0(x16)
lw x18, 4(x16)

slt x22, x18, x17
beq x22, x0, no_swap

sw x18, 0(x16)
sw x17, 4(x16)

no_swap:

la x5, four
lw x6, 0(x5)
add x16, x16, x6     # pointer += 4

la x5, one
lw x6, 0(x5)
add x13, x13, x6     # j++

j inner_loop

next_outer:

la x5, one
lw x6, 0(x5)
add x12, x12, x6     # i++

j outer_loop


print_array:

la x5, zero
lw x13, 0(x5)

print_loop:

slt x23, x13, x11
beq x23, x0, exit

lw a0, 0(x10)

la x5, four
lw x6, 0(x5)
add x10, x10, x6

la a7, one
ecall

la x5, one
lw x6, 0(x5)
add x13, x13, x6

j print_loop

exit:
la a7, zero
ecall
.data:
arr: .word 9 5 3 8 1 6 2 7 4 2 15 11 14 13 12 19 18 17 16 10
n:   .word 20

.text:

la x10, arr          # x10 = base address of arr
la x5, n
lw x11, 0(x5)        # x11 = n = 20

addi x12, x0, 0      # i = 0  (no la+lw needed — immediate!)

outer_loop:
slt x20, x12, x11
beq x20, x0, exit    # if i >= n: exit

addi x13, x0, 0      # j = 0  (immediate)

addi x14, x11, -1
sub x14, x14, x12    # limit = n-1-i

add x16, x10, x0     # pointer = base address of arr

inner_loop:
slt x21, x13, x14
beq x21, x0, next_outer   # if j >= limit: go to next outer

lw x17, 0(x16)
lw x18, 4(x16)

slt x22, x18, x17
beq x22, x0, no_swap      # if arr[j] <= arr[j+1]: no swap

sw x18, 0(x16)
sw x17, 4(x16)

no_swap:
addi x16, x16, 4     # pointer += 4   (immediate — no la+lw!)
addi x13, x13, 1     # j++             (immediate — no la+lw!)

jal x0, inner_loop

next_outer:
addi x12, x12, 1     # i++             (immediate — no la+lw!)

jal x0, outer_loop

exit:
# Array is now sorted in memory.
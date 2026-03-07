.data:
val: .word 42

.text:
# Test 1: EX-EX Forwarding
# addi x1 = 5, then addi uses x1 immediately (1 gap)
# Expected: x2 = 8
addi x1 x0 5
addi x2 x1 3

# Test 2: MEM-WB + EX-EX Forwarding together
# x3 is 2 instructions before add, x4 is 1 instruction before
# Expected: x5 = 30
addi x3 x0 10
addi x4 x0 20
add x5 x3 x4

# Test 3: Load-Use Stall
# lw loads 42 from memory, addi uses it immediately (stall must happen)
# Expected: x7 = 42, x8 = 50
la x6 val
lw x7 0(x6)
addi x8 x7 8
# bubble_sort.asm
# ───────────────────────────────────────────────────────────────
# Bubble Sort — sorts a 5-element array stored in data memory.
#
# Input array  : [5, 3, 4, 1, 2]  loaded at base address 256
# Expected out : [1, 2, 3, 4, 5]  in memory after execution
#
# Register allocation:
#   x1  = n            (array size = 5)
#   x2  = base         (byte address of array start = 256)
#   x3  = i            (outer loop counter)
#   x4  = j            (inner loop counter)
#   x5  = limit        (n - i - 1, inner loop bound)
#   x6  = addr_j       (byte address of arr[j])
#   x7  = arr[j]
#   x8  = arr[j+1]
#   x9  = temp / diff
#   x10 = cmp_flag     (result of slti — 1 if no swap needed)
#   x20 = scratch      (array initialisation)
# ───────────────────────────────────────────────────────────────

# ── Setup constants ────────────────────────────────────────────
    addi x1,  x0, 5        # n = 5
    addi x2,  x0, 256      # base address = 256 (byte)

# ── Initialise array [5, 3, 4, 1, 2] in data memory ──────────
    addi x20, x0, 5
    sw   x20, 0(x2)        # mem[256] = 5
    addi x20, x0, 3
    sw   x20, 4(x2)        # mem[260] = 3
    addi x20, x0, 4
    sw   x20, 8(x2)        # mem[264] = 4
    addi x20, x0, 1
    sw   x20, 12(x2)       # mem[268] = 1
    addi x20, x0, 2
    sw   x20, 16(x2)       # mem[272] = 2

# ── Outer loop: i = 0 ─────────────────────────────────────────
    addi x3,  x0, 0        # i = 0

OUTER:
    # if i == n-1  →  (n-1) - i == 0  →  BNE does NOT branch → fall to DONE
    addi x9,  x1, -1       # x9 = n - 1 = 4
    sub  x9,  x9, x3       # x9 = (n-1) - i
    bne  x9,  x0, INNER_INIT
    jal  x0,  DONE

INNER_INIT:
    addi x4,  x0, 0        # j = 0
    sub  x5,  x1, x3       # x5 = n - i
    addi x5,  x5, -1       # x5 = n - i - 1  (inner loop bound)

# ── Inner loop ────────────────────────────────────────────────
INNER:
    # if j == n-i-1  →  (n-i-1) - j == 0  →  BNE does NOT branch → increment i
    sub  x9,  x5, x4       # x9 = (n-i-1) - j
    bne  x9,  x0, COMPARE
    addi x3,  x3, 1        # i++
    jal  x0,  OUTER

# ── Compare arr[j] and arr[j+1] ───────────────────────────────
COMPARE:
    # addr of arr[j] = base + j*4
    # compute j*4: j+j = 2j,  2j+2j = 4j
    add  x6,  x4, x4       # x6 = 2*j
    add  x6,  x6, x6       # x6 = 4*j
    add  x6,  x6, x2       # x6 = base + 4*j

    lw   x7,  0(x6)        # x7 = arr[j]
    lw   x8,  4(x6)        # x8 = arr[j+1]

    # swap if arr[j] > arr[j+1]
    # diff = arr[j] - arr[j+1]
    # slti x10, diff, 1  →  x10 = 1 if diff < 1  (i.e., arr[j] <= arr[j+1])
    # bne x10, x0, NO_SWAP → skip swap when x10 = 1
    sub  x9,  x7, x8       # x9 = arr[j] - arr[j+1]
    slti x10, x9, 1        # x10 = 1 if diff <= 0  (no swap needed)
    bne  x10, x0, NO_SWAP

    # Swap arr[j] and arr[j+1]
    sw   x8,  0(x6)        # arr[j]   = old arr[j+1]
    sw   x7,  4(x6)        # arr[j+1] = old arr[j]

NO_SWAP:
    addi x4,  x4, 1        # j++
    jal  x0,  INNER

# ── Program terminates when PC reaches DONE (out of bounds) ───
DONE:
    # PC = byte address of DONE; no more instructions → fetch returns invalid
    # Simulation halts cleanly.

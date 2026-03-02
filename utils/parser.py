from instruction import Instruction

def parser(input_file):

    lines = input_file.splitlines()
    label_map = {}
    clean_lines = []
    instr_index = 0
    instructions = []

    for single_line in lines:
        line = single_line.split("#")[0].strip()

        if not line:
            continue

        if ":" in line:
            label_part, _, rest = line.partition(":")
            label = label_part.strip()

            if label:
                label_map[label] = instr_index*4

            line = rest.strip()
            if not line:
                continue

        clean_lines.append(line)
        instr_index += 1

    instr_index = 0

    for line in clean_lines:

        words = line.replace(",", "").split()
        if words[0] == "add" or words[0] == "sub":
            instr = Instruction(words[0],instr_index*4,int(words[1][1:]),int(words[2][1:]),int(words[3][1:]))

        elif words[0] == "addi":
            instr = Instruction( words[0],instr_index*4,int(words[1][1:]),int(words[2][1:]),imm=int(words[3]))

        elif words[0] == "lw":
            rd = int(words[1][1:])
            offset, reg = words[2].split("(")
            imm = int(offset)
            rs1 = int(reg[:-1][1:])

            instr = Instruction(words[0],instr_index*4,rd,rs1,imm=imm)

        elif words[0] == "sw":
            rs2 = int(words[1][1:])
            offset, reg = words[2].split("(")
            imm = int(offset)
            rs1 = int(reg[:-1][1:])

            instr = Instruction(words[0],instr_index*4,rs1=rs1,rs2=rs2,imm=imm)

        elif words[0] == "beq" or words[0] == "bne":
            rs1 = int(words[1][1:])
            rs2 = int(words[2][1:])
            label = words[3]
            target = label_map[label]

            instr = Instruction(words[0],instr_index*4,rs1=rs1,rs2=rs2,imm=target)

        else:
            continue

        instructions.append(instr)
        instr_index += 1

    return instructions

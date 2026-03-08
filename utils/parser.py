from .Instruction import Instruction
from components.data_mem import Memory

def parser(input_file):
    lines = input_file.splitlines()
    label_map = {}
    clean_lines = []
    instr_index = 0
    instructions = []
    memory = Memory()
    data_label_map = {}
    mode = None

    # --- PASS 1: Extract Labels and Clean Code ---
    for single_line in lines:
        line = single_line.split("#")[0].strip()

        if not line:
            continue

        if line == ".data:":
            mode = "data"
            continue

        if line == ".text:":
            mode = "text"
            continue

        if mode == "data":
            label_part, _, rest_part = line.partition(":")
            label = label_part.strip()
            rest = rest_part.strip()

            if label:
                data_label_map[label] = memory.base_address
            else:
                raise Exception("Please keep a name to the assigned memory")

            words = rest.replace(",", "").split()

            if words[0] == ".word":
                for value in words[1:]:
                    memory.data_section_word(int(value))

            elif words[0] == ".byte":
                for value in words[1:]:
                    memory.data_section_byte(int(value))

            continue

        if ":" in line:
            label_part, _, rest = line.partition(":")
            label = label_part.strip()

            # Only treat as a label if label_part has no spaces (valid label names can't have spaces)
            if label and " " not in label:
                label_map[label] = instr_index * 4

                line = rest.strip()
                if not line:
                    continue

        clean_lines.append(line)
        instr_index += 1

    # --- PASS 2: Generate Instructions ---
    instr_index = 0

    for line in clean_lines:
        words = line.replace(",", "").split()
        current_pc = instr_index * 4

        if words[0] == "add" or words[0] == "sub":
            instr = Instruction(words[0], current_pc, int(words[1][1:]), int(words[2][1:]), int(words[3][1:]))

        elif words[0] == "addi":
            instr = Instruction(words[0], current_pc, int(words[1][1:]), int(words[2][1:]), imm=int(words[3]))

        elif words[0] == "lw":
            rd = int(words[1][1:])
            offset, reg = words[2].split("(")
            imm = int(offset)
            rs1 = int(reg[:-1][1:])
            instr = Instruction(words[0], current_pc, rd, rs1, imm=imm)

        elif words[0] == "sw":
            rs2 = int(words[1][1:])
            offset, reg = words[2].split("(")
            imm = int(offset)
            rs1 = int(reg[:-1][1:])
            instr = Instruction(words[0], current_pc, rs1=rs1, rs2=rs2, imm=imm)

        elif words[0] == "beq" or words[0] == "bne":
            rs1 = int(words[1][1:])
            rs2 = int(words[2][1:])
            label = words[3]
            target = label_map[label]
            
            # FIX: Calculate PC-relative offset instead of absolute target
            offset = target - current_pc 
            instr = Instruction(words[0], current_pc, rs1=rs1, rs2=rs2, imm=offset)

        elif words[0] == "la":
            rd = int(words[1][1:])
            label = words[2]

            if label in data_label_map:
                imm = data_label_map[label]
            elif label in label_map:
                imm = label_map[label]
            else:
                raise Exception(f"Label '{label}' not found")                       

            instr = Instruction(words[0], current_pc, rd, imm=imm)

        elif words[0] == "slt":
            instr = Instruction(words[0], current_pc, int(words[1][1:]), int(words[2][1:]), int(words[3][1:]))
            
        elif words[0] == "jal":
            rd = int(words[1][1:])
            label = words[2]
            target = label_map[label]
            
            # FIX: Calculate PC-relative offset for jump
            offset = target - current_pc
            instr = Instruction(words[0], current_pc, rd=rd, imm=offset)

        elif words[0] == "j":
            label = words[1]
            target = label_map[label]
            
            # FIX: Calculate PC-relative offset and convert 'j' to 'jal x0'
            offset = target - current_pc
            instr = Instruction("jal", current_pc, rd=0, imm=offset)

        else:
            print(f"Warning: Unrecognized instruction '{words[0]}'")
            continue

        instructions.append(instr)
        instr_index += 1

    return instructions, memory
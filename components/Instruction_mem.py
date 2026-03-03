class InstructionMemory:
    def __init__(self, instructions):
        """
        Stores the parsed instructions.
        """
        self.instructions = instructions

    def read(self, pc):
        """
        Returns the Instruction object for the given PC.
        Since RISC-V instructions are 32 bits (4 bytes), we divide by 4.
        """
        index = pc // 4
        
        if index < 0 or index >= len(self.instructions):
            return None
            
        return self.instructions[index]
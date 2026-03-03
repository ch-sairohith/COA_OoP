
class RegisterFile:
    def __init__(self):
        """
        Initializes the 32 integer registers (x0 to x31) to zero.
        """
        self.registers = [0] * 32

    def read(self, reg_addr: int) -> int:
        """
        Reads the value from a specific register.
        
        :param reg_addr: The register number (0 to 31).
        :return: The integer value stored in the register.
        """
        if reg_addr is None:
            return 0
        if reg_addr == 0:
            return 0
            
        return self.registers[reg_addr]

    def write(self, reg_addr: int, value: int):
        """
        Writes a value to a specific register.
        
        :param reg_addr: The register number (0 to 31).
        :param value: The integer value to write.
        """
        if reg_addr is None:
            return

        if reg_addr == 0:
            return
            
        self.registers[reg_addr] = value

    def dump(self):
        """
        Helper method to print the contents of the registers.
        Very useful for debugging at the end of the simulation!
        """
        print("--- Register File State ---")
        for i in range(32):
            if self.registers[i] != 0: 
                print(f"x{i:02d}: {self.registers[i]}")
        print("---------------------------")
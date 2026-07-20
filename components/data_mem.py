
class Memory:

    def __init__(self,size=4096):
        self.size=size
        self.mem=bytearray(size)
        self.base_address=1024

    def read_byte(self,address):

        if address >= self.size:
            raise Exception("Memory out of bounds")

        return self.mem[address]
    
    def store_byte(self,address,val):

        if address >= self.size:
            raise Exception("Memory out of bounds")

        self.mem[address]=val & 255

    def read_word(self,address):
        if(address%4!=0):
            raise Exception("The starting address for memory access is multiple of 4")
        if address + 4 > self.size:
            raise Exception("Memory out of bounds")
        
        value = 0

        for i in range(4):
            value += self.mem[address+i]<<(8*i)

        # Sign-extend: interpret as 32-bit signed integer
        if value >= 0x80000000:
            value -= 0x100000000

        return value
    
    def store_word(self,address,val):
        if(address%4!=0):
            raise Exception("The starting address for memory access is multiple of 4")
        if address + 4 > self.size:
            raise Exception("Memory out of bounds")

        # Mask to 32 bits to handle negative (signed) values correctly
        val = val & 0xFFFFFFFF
        for i in range(4):
            self.mem[address+i]=val & 255
            val=val>>8

    def data_section_word(self,val):

        if self.base_address%4 != 0:
            self.base_address +=4-self.base_address%4

        if self.base_address + 4 > self.size:
            raise Exception("Memory out of bounds")
        
        for i in range(4):
            self.mem[self.base_address+i]=val & 255
            val=val>>8

        self.base_address+=4
    
    def data_section_byte(self,val):

        if self.base_address >= self.size:
            raise Exception("Memory out of bounds")
        
        self.mem[self.base_address]=val & 255
        self.base_address+=1         
        
from core.latches import IF_ID_Latch, ID_EX_Latch, EX_MEM_Latch, MEM_WB_Latch
from stages import FetchStage, DecodeStage, ExecuteStage, MemStage, WritebackStage
from components.register import RegisterFile
class Simulator:
    def __init__(self, inst_mem, data_mem):
        self.clock = 0
        self.pc = 0
        self.register_file = RegisterFile()
        self.data_mem = data_mem
        
        self.if_id_latch = IF_ID_Latch()  
        self.id_ex_latch = ID_EX_Latch()
        self.ex_mem_latch = EX_MEM_Latch()
        self.mem_wb_latch = MEM_WB_Latch()
  
        self.fetch_stage = FetchStage(inst_mem)
        self.decode_stage = DecodeStage(self.register_file)
        self.execute_stage = ExecuteStage()
        self.mem_stage = MemStage()
        self.writeback_stage = WritebackStage()

    def run(self):
        while True:
            max_pc = len(self.fetch_stage.inst_mem.instructions) * 4
            instructions_left = self.pc < max_pc
            
            pipeline_empty = (self.if_id_latch.is_nop and 
                              self.id_ex_latch.is_nop and 
                              self.ex_mem_latch.is_nop and 
                              self.mem_wb_latch.is_nop)
            
            if not instructions_left and pipeline_empty:
                break 
            self.writeback_stage.step(self.mem_wb_latch, self.register_file, stall=False)
            
            self.mem_stage.step(self.ex_mem_latch, self.mem_wb_latch, self.data_mem)
            
            self.execute_stage.step(self.id_ex_latch, self.ex_mem_latch)
            
            self.decode_stage.step(self.if_id_latch, self.id_ex_latch, stall=False)
            
            self.pc = self.fetch_stage.step(self.pc, self.if_id_latch, stall=False)
            
            self.clock += 1
        print(f"Simulation complete in {self.clock} cycles.")
        print("Final Register State:")
        for i in range(32):
            print(f"x{i}: {self.register_file.read(i)}") 
        print("Final Memory State (non-zero values):")
        for addr in range(0, len(self.data_mem.mem), 4):
            word = self.data_mem.read_word(addr)
            if word != 0:
                print(f"0x{addr:08x}: 0x{word:08x}") 
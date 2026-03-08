from core.latches import IF_ID_Latch, ID_EX_Latch, EX_MEM_Latch, MEM_WB_Latch
from stages import FetchStage, DecodeStage, ExecuteStage, MemStage, WritebackStage
from components.register import RegisterFile
from core.hazard_unit import HazardUnit
import json

with open('config.json', 'r') as file:
    config = json.load(file)

hazard = HazardUnit()
isforward = config.get("forwarding_enabled", True)

class Simulator:
    def __init__(self, inst_mem, data_mem):
        self.clock = 0
        self.pc = 0
        # Performance counters
        self.instructions_retired = 0
        self.load_use_stalls    = 0   # lw followed by dependent instruction
        self.branch_data_stalls = 0   # branch depends on recently produced value
        self.flush_cycles       = 0   # taken branch or JAL flushed IF stage
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
                
            forwardA, forwardB, forwardC,forwardD,stall = hazard.detect(self.if_id_latch, self.id_ex_latch, self.ex_mem_latch, self.mem_wb_latch)
            
            if not isforward:
                forwardA = "NONE"
                forwardB = "NONE"
                forwardC="NONE"
                forwardD="NONE"
                if not self.if_id_latch.is_nop and self.if_id_latch.instruction:
                    instr = self.if_id_latch.instruction
                    
                    src_regs = []
                    if getattr(instr, 'rs1', None) not in [None, 0]: src_regs.append(instr.rs1)
                    if getattr(instr, 'rs2', None) not in [None, 0]: src_regs.append(instr.rs2)
                    
                    conflict_ex = (not self.id_ex_latch.is_nop and self.id_ex_latch.reg_write and self.id_ex_latch.rd_addr in src_regs)
                    conflict_mem = (not self.ex_mem_latch.is_nop and self.ex_mem_latch.reg_write and self.ex_mem_latch.rd_addr in src_regs)
                    conflict_wb = (not self.mem_wb_latch.is_nop and self.mem_wb_latch.reg_write and self.mem_wb_latch.rd_addr in src_regs)
                    
                    if conflict_ex or conflict_mem or conflict_wb:
                        stall = True
            # forwarding
            stall_if=False
            stall_de=False
            stall_exe=False
            if stall=="execute":
              stall_exe=True
              stall_de=True
              stall_if=True
            elif stall=="decode":
                stall_de=True
                stall_if=True
            if not isforward:
              stall_if=stall
              stall_de=stall
              stall_exe=False
            old_mem_wb_latch = self.mem_wb_latch
            old_ex_mem_latch=self.ex_mem_latch

            # Count instructions retiring this cycle
            if not self.mem_wb_latch.is_nop:
                self.instructions_retired += 1

            self.writeback_stage.step(self.mem_wb_latch, self.register_file, stall=False)
            
            self.mem_wb_latch = self.mem_stage.step(self.ex_mem_latch, self.data_mem, stall=False)
            
            self.execute_stage.step(self.id_ex_latch, self.ex_mem_latch, old_mem_wb_latch, forwardA, forwardB, stall_exe)
        
            target_pc, flush_if = self.decode_stage.step(self.if_id_latch, self.id_ex_latch,old_ex_mem_latch,old_mem_wb_latch,forwardC,forwardD, stall_de)

            self.pc = self.fetch_stage.step(self.pc, self.if_id_latch, stall_if)
          
            if flush_if and stall is False:
                self.if_id_latch.is_nop = True
                self.pc = target_pc
                self.flush_cycles += 1

            # Granular stall classification
            if stall == "decode":
                # Could be load-use OR branch-data hazard
                # Distinguish: if ID/EX has an lw, it's a load-use stall
                if not self.id_ex_latch.is_nop and self.id_ex_latch.alu_op == "lw":
                    self.load_use_stalls += 1
                else:
                    self.branch_data_stalls += 1
            elif stall == "execute":
                # Branch after a lw — always a branch data stall
                self.branch_data_stalls += 1
            elif stall is True:
                # Non-forwarding mode generic stall
                self.load_use_stalls += 1

            self.clock += 1
            
        ipc = self.instructions_retired / self.clock if self.clock > 0 else 0
        total_stalls = self.load_use_stalls + self.branch_data_stalls + self.flush_cycles

        print(f"\nTotal cycles : {self.clock}")
        print(f"Total stalls : {total_stalls}")
        print(f"IPC          : {ipc:.3f}")
        print(f"CPI          : {(1/ipc):.3f}" if ipc > 0 else "CPI          : N/A")
        print("Final Register State (non-zero):")
        for i in range(32):
            val = self.register_file.read(i)
            if val != 0:
                print(f"  x{i}: {val}")
        print("\nFinal Memory State (non-zero words):")
        for addr in range(0, len(self.data_mem.mem), 4):
            word = self.data_mem.read_word(addr)
            if word != 0:
                print(f"  [{addr:4d}]: {word}")

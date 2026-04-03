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
    def __init__(self, inst_mem, data_mem, cache_hierarchy):
        self.clock = 0
        self.pc = 0
        self.cache_hierarchy = cache_hierarchy
        # Performance counters
        self.instructions_retired = 0
        self.load_use_stalls    = 0   
        self.branch_data_stalls = 0   
        self.flush_cycles       = 0   
        self.execution_stalls   = 0   # Track stalls caused by multi-cycle latencies!
        
        self.register_file = RegisterFile()
        self.data_mem = data_mem
        
        self.if_id_latch = IF_ID_Latch()  
        self.id_ex_latch = ID_EX_Latch()
        self.ex_mem_latch = EX_MEM_Latch()
        self.mem_wb_latch = MEM_WB_Latch()
  
        self.fetch_stage = FetchStage(inst_mem, self.cache_hierarchy)
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
                
            forwardA, forwardB, forwardC, forwardD, stall = hazard.detect(self.if_id_latch, self.id_ex_latch, self.ex_mem_latch, self.mem_wb_latch)
            
            if not isforward:
                forwardA, forwardB, forwardC, forwardD = "NONE", "NONE", "NONE", "NONE"
                # Only check non-forwarding hazards if latency hasn't already stalled us
                if stall not in ["memory", "execute"]:
                    if hazard.detect_nonforwarding(self.if_id_latch, self.id_ex_latch, self.ex_mem_latch, self.mem_wb_latch):
                        stall = True

            # Performance counter logic
            if stall in ["memory", "execute"]:
                self.execution_stalls += 1
            elif stall == "decode" or stall is True:
                if not self.id_ex_latch.is_nop and self.id_ex_latch.alu_op == "lw":
                    self.load_use_stalls += 1
                else:
                    self.branch_data_stalls += 1

            if not self.mem_wb_latch.is_nop:
                self.instructions_retired += 1

            old_mem_wb_latch = self.mem_wb_latch
            old_ex_mem_latch = self.ex_mem_latch

            # 1. Writeback (always moves forward)
            self.writeback_stage.step(self.mem_wb_latch, self.register_file, stall=False)
            
            # 2. Memory Stage
            if stall == "memory":
                # MEM is busy calculating. Output a bubble.
                # Do NOT overwrite ex_mem_latch so it holds its counter!
                self.mem_wb_latch = MEM_WB_Latch(is_nop=True)
            else:
                self.mem_wb_latch, mem_latency = self.mem_stage.step(self.ex_mem_latch, stall=False, cache_hierarchy=self.cache_hierarchy)
            
            # 3. Execute Stage
            if stall == "memory":
                pass # ID_EX is frozen waiting for memory. Do nothing.
            elif stall == "execute":
                # EX is busy calculating. Output a bubble.
                # Do NOT overwrite id_ex_latch so it holds its counter!
                self.ex_mem_latch = EX_MEM_Latch(is_nop=True)
            else:
                self.ex_mem_latch = self.execute_stage.step(self.id_ex_latch, old_ex_mem_latch, old_mem_wb_latch, forwardA, forwardB, stall=False)
        
            # 4. Decode Stage
            if stall in ["memory", "execute"]:
                pass # ID is frozen waiting for downstream stages.
            elif stall == "decode" or stall is True:
                # Data hazard. Output a bubble to EX.
                target_pc, flush_if = self.decode_stage.step(self.if_id_latch, self.id_ex_latch, old_ex_mem_latch, old_mem_wb_latch, forwardC, forwardD, stall=True)
            else:
                target_pc, flush_if = self.decode_stage.step(self.if_id_latch, self.id_ex_latch, old_ex_mem_latch, old_mem_wb_latch, forwardC, forwardD, stall=False)

            # 5. Fetch Stage
            if stall:
                pass # Fetch is frozen for any stall type
            else:
                self.pc, fetch_latency = self.fetch_stage.step(self.pc, self.if_id_latch, stall=False)
          
            if flush_if and stall is False:
                self.if_id_latch.is_nop = True
                self.pc = target_pc
                self.flush_cycles += 1

            self.clock += 1
            
        ipc = self.instructions_retired / self.clock if self.clock > 0 else 0
        total_stalls = self.load_use_stalls + self.branch_data_stalls + self.execution_stalls + self.flush_cycles

        print(f"\nSimulation complete in {self.clock} cycles.")
        print(f"Total Stalls          : {total_stalls}")
        print(f"  - Load-Use Stalls   : {self.load_use_stalls}")
        print(f"  - Branch/Data Stalls: {self.branch_data_stalls}")
        print(f"  - Execution Stalls  : {self.execution_stalls}")
        print(f"  - Branch Flushes    : {self.flush_cycles}")
        print(f"IPC                   : {ipc:.3f}")
        print(f"CPI                   : {(1/ipc):.3f}" if ipc > 0 else "CPI: N/A")
        
        print("\nFinal Register State (non-zero):")
        for i in range(32):
            val = self.register_file.read(i)
            if val != 0:
                print(f"  x{i}: {val}")
        print("\nFinal Memory State (non-zero words):")
        for addr in range(0, len(self.data_mem.mem), 4):
            word = self.data_mem.read_word(addr)
            if word != 0:
                print(f"  [{addr:4d}]: {word}")
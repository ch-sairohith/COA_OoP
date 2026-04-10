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

        self._mem_wb_buffer = None
        self._mem_bubbles_remaining = 0

    def run(self):
        latency_lw = config["latencies"].get("lw", 1)
        latency_sw = config["latencies"].get("sw", 1)

        while True:
            max_pc = len(self.fetch_stage.inst_mem.instructions) * 4
            instructions_left = self.pc < max_pc or self.fetch_stage.is_pending()
            
            pipeline_empty = (self.if_id_latch.is_nop and 
                              self.id_ex_latch.is_nop and 
                              self.ex_mem_latch.is_nop and 
                              self.mem_wb_latch.is_nop and
                              not self.fetch_stage.is_pending())
            
            if not instructions_left and pipeline_empty:
                break 

            mem_latency_stall = self._mem_bubbles_remaining > 0
                
            forwardA, forwardB, forwardC, forwardD, stall = hazard.detect(self.if_id_latch, self.id_ex_latch, self.ex_mem_latch, self.mem_wb_latch)
            if mem_latency_stall:
                stall = "memory"
            
            if not isforward:
                forwardA, forwardB, forwardC, forwardD = "NONE", "NONE", "NONE", "NONE"
                if stall not in ["memory", "execute"]:
                    if hazard.detect_nonforwarding(self.if_id_latch, self.id_ex_latch, self.ex_mem_latch, self.mem_wb_latch):
                        stall = True
            if stall in ["memory", "execute"]:
                self.execution_stalls += 1
            elif stall == "decode" or stall is True:
                if not self.id_ex_latch.is_nop and self.id_ex_latch.alu_op == "lw":
                    self.load_use_stalls += 1
                else:
                    self.branch_data_stalls += 1
                    
            if not self.ex_mem_latch.is_nop and self.ex_mem_latch.mem_write and self.mem_stage.is_sb_full() and stall != "memory":
                stall = "memory"
                self._mem_bubbles_remaining = 1 # give it a small bump to wait for drain

            if not self.mem_wb_latch.is_nop:
                self.instructions_retired += 1

            old_mem_wb_latch = self.mem_wb_latch
            old_ex_mem_latch = self.ex_mem_latch

            # 1. Writeback (always moves forward)
            self.writeback_stage.step(self.mem_wb_latch, self.register_file, stall=False)
            
            # 2. Memory Stage (D-cache latency: first cycle performs access; remaining cycles bubble)
            if stall == "memory":
                if self._mem_bubbles_remaining > 0:
                    self._mem_bubbles_remaining -= 1
                    if self._mem_bubbles_remaining == 0 and self._mem_wb_buffer is not None:
                        self.mem_wb_latch = self._mem_wb_buffer
                        self._mem_wb_buffer = None
                    else:
                        self.mem_wb_latch = MEM_WB_Latch(is_nop=True)
                else:
                    self.mem_wb_latch = MEM_WB_Latch(is_nop=True)
            else:
                raw_wb, cache_lat = self.mem_stage.step(
                    self.ex_mem_latch, stall=False, cache_hierarchy=self.cache_hierarchy
                )
                if (
                    not self.ex_mem_latch.is_nop
                    and (self.ex_mem_latch.mem_read or self.ex_mem_latch.mem_write)
                ):
                    cfg_lat = latency_lw if self.ex_mem_latch.mem_read else latency_sw
                    effective = max(cfg_lat, cache_lat)
                    if effective > 1:
                        self._mem_wb_buffer = raw_wb
                        self._mem_bubbles_remaining = effective - 1
                        self.mem_wb_latch = MEM_WB_Latch(is_nop=True)
                    else:
                        self.mem_wb_latch = raw_wb
                else:
                    self.mem_wb_latch = raw_wb

            if stall == "memory":
                pass
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

            # Branch / jal: resolve PC before fetch so the next instruction is not fetched from the
            # fall-through path (non-speculative: no wrong-path fetch to "flush" later).
            if flush_if and stall is False:
                self.if_id_latch.is_nop = True
                self.pc = target_pc
                self.flush_cycles += 1
                # Drop any in-flight multi-cycle I-fetch still tied to the old sequential PC.
                self.fetch_stage.cancel_pending()

            # 5. Fetch Stage
            if stall:
                pass  # Fetch frozen for hazard stalls
            else:
                self.pc, fetch_latency = self.fetch_stage.step(self.pc, self.if_id_latch, stall=False)

            self.clock += 1
            # Tick background buffers
            self.mem_stage.tick(self.cache_hierarchy)
            self.cache_hierarchy.tick()
            
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
                
        self.mem_stage.flush_all(self.cache_hierarchy)
        self.cache_hierarchy.flush_all()
        
        print("\nFinal Memory State (non-zero words):")
        for addr in range(0, len(self.data_mem.mem), 4):
            word = self.data_mem.read_word(addr)
            if word != 0:
                print(f"  [{addr:4d}]: {word}")
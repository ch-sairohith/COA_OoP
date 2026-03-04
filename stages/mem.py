from core.latches import MEM_WB_Latch

class MemStage:

    def step(self, ex_mem_latch, stall,memory):
        """
        Executes one clock cycle of the Memory stage.
        """
        if stall or ex_mem_latch.is_nop:
            return MEM_WB_Latch(is_nop=True)
        
        mem_data=0
        
        if ex_mem_latch.mem_read:
            if ex_mem_latch.mem_size==1:
                mem_data=memory.read_byte(ex_mem_latch.alu_result)
            elif ex_mem_latch.mem_size==4:
                mem_data=memory.read_word(ex_mem_latch.alu_result)
        elif ex_mem_latch.mem_write:
            if ex_mem_latch.mem_size==1:
                memory.store_byte(ex_mem_latch.alu_result,ex_mem_latch.rs2_val)
            elif ex_mem_latch.mem_size==4:
                memory.store_word(ex_mem_latch.alu_result,ex_mem_latch.rs2_val)
        
        return MEM_WB_Latch(is_nop=False,
                            alu_result=ex_mem_latch.alu_result,
                            mem_data=mem_data,
                            rd_addr=ex_mem_latch.rd_addr,
                            reg_write=ex_mem_latch.reg_write,
                            mem_to_reg=ex_mem_latch.mem_read)

        
        

class WritebackStage:

    def step(self, mem_wb_latch, registers, stall):

        if stall or mem_wb_latch.is_nop:
            return
        
        if mem_wb_latch.reg_write:

            if mem_wb_latch.mem_to_reg:
                registers.write(mem_wb_latch.rd_addr, mem_wb_latch.mem_data)
            else:
                registers.write(mem_wb_latch.rd_addr, mem_wb_latch.alu_result)

# stages/fetch.py

class FetchStage:
    def __init__(self, inst_mem):
        """
        Initializes Fetch with access to instruction memory.
        Notice we no longer store self.pc here!
        """
        self.inst_mem = inst_mem

    def step(self, current_pc: int, if_id_latch, stall: bool):
        """
        Executes one clock cycle of the Fetch stage.
        Returns the next PC value.
        """
        if stall:
            return current_pc

        instr = self.inst_mem.read(current_pc)

        if instr is None:
            if_id_latch.is_nop = True
            if_id_latch.instruction = None
        else:
            if_id_latch.is_nop = False
            if_id_latch.instruction = instr
            if_id_latch.pc = current_pc

        return current_pc + 4
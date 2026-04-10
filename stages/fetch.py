from utils.Instruction import Instruction


class FetchStage:
    def __init__(self, inst_mem,cache_hierarchy):
        """
        Initializes Fetch with access to instruction memory.
        Notice we no longer store self.pc here!
        """
        self.inst_mem = inst_mem
        self.cache_hierarchy = cache_hierarchy
        self._pending_if_cycles = 0
        self._buffer_instr = None
        self._buffer_pc = 0

    def is_pending(self) -> bool:
        return self._pending_if_cycles > 0 or self._buffer_instr is not None

    def cancel_pending(self):
        """Call on branch flush so a new PC does not inherit an in-flight I-fetch."""
        self._pending_if_cycles = 0
        self._buffer_instr = None

    def step(self, current_pc: int, if_id_latch, stall: bool):
        """
        Executes one clock cycle of the Fetch stage.
        Returns (next_pc, reported_latency_for_last_completed_access).
        When stall is True (hazard freeze), IF pending state does not advance.
        """
        if stall:
            return current_pc, 0

        if self._pending_if_cycles > 0:
            self._pending_if_cycles -= 1
            if self._pending_if_cycles == 0:
                if_id_latch.is_nop = False
                if_id_latch.instruction = self._buffer_instr
                if_id_latch.pc = self._buffer_pc
                self._buffer_instr = None
                return current_pc + 4, 0
            if_id_latch.is_nop = True
            if_id_latch.instruction = None
            return current_pc, 0

        instr, latency = self.cache_hierarchy.fetch(current_pc)
        # Unified L2 may alias I- and D-lines; recover architectural instruction if needed.
        if instr is not None and not isinstance(instr, Instruction):
            instr = self.inst_mem.read(current_pc)

        if instr is None:
            if_id_latch.is_nop = True
            if_id_latch.instruction = None
            return current_pc + 4, latency

        if latency <= 1:
            if_id_latch.is_nop = False
            if_id_latch.instruction = instr
            if_id_latch.pc = current_pc
            return current_pc + 4, latency

        self._pending_if_cycles = latency - 1
        self._buffer_instr = instr
        self._buffer_pc = current_pc
        if_id_latch.is_nop = True
        if_id_latch.instruction = None
        return current_pc, latency
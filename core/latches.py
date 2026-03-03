from dataclasses import dataclass
from  utils.Instruction import Instruction
@dataclass
class IF_ID_Latch:
  is_nop:bool=True
  pc: int=0
  instruction: Instruction=None
@dataclass
class ID_EX_Latch:
  is_nop:bool=True
  pc:int =0
  instruction :Instruction=None
  rs1_val:int =0
  rs2_val:int =0
  rs1_addr:int=0
  rs2_addr:int=0
  imm:int=0
  alu_op:str=""
  reg_write:bool=False
  mem_read:bool=False
  mem_write:bool=False
  is_branch:bool=Flase
  @dataclass 
  class EX_MEM_Latch:
    is_nop:bool=True
    alu_result:int=0
    rs2_val:int=0
    rd_addr:int=0
    reg_write:bool=False
    mem_read:bool=False
    mem_write:bool=False
  @dataclass
  class MEM_WB_Latch:
    is_nop:bool=True
    alu_result:int=0
    mem_data:int=0
    rd_addr:int=0
    reg_write:bool=False
    mem_to_reg:bool=False




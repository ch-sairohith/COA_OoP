from core.simulator import Simulator
from utils.parser import parser
from components.data_mem import Memory
from components.Instruction_mem import InstructionMemory
with open("program.asm", "r") as f:
  instructions,memory=parser(f.read())
inst_mem=InstructionMemory(instructions) 
sim = Simulator(inst_mem, memory)
sim.run()
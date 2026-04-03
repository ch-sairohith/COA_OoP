import json
from core.simulator import Simulator
from utils.parser import parser
from components.data_mem import Memory
from components.Instruction_mem import InstructionMemory
from components.cache_hierarchy import CacheHierarchy

with open("config.json", "r") as f:
    config = json.load(f)

with open("program.asm", "r") as f:
    instructions, memory = parser(f.read())
  
inst_mem = InstructionMemory(instructions) 
cache_hierarchy = CacheHierarchy(config, memory, inst_mem)

sim = Simulator(inst_mem, memory, cache_hierarchy)
sim.run()

# Ensure we spit out cache evaluations at the very end
stats = cache_hierarchy.get_stats()
print("\n--- Cache Statistics ---")
for key, val in stats.items():
    print(f"{key}: {val*100:.2f}%")
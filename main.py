import sys
import json
import configparser
from core.simulator import Simulator
from utils.parser import parser
from components.data_mem import Memory
from components.Instruction_mem import InstructionMemory
from components.cache_system.cache_hierarchy import CacheHierarchy
from vm.address_translator import AddressTranslator

with open("config.json", "r") as f:
    config = json.load(f)

# ── Detect Mode ────────────────────────────────────────────────────────
is_trace_mode = "--trace" in sys.argv

if is_trace_mode:
    trace_idx = sys.argv.index("--trace")
    if trace_idx + 1 >= len(sys.argv):
        print("Error: Missing trace file path after --trace")
        sys.exit(1)
    file_path = sys.argv[trace_idx + 1]
    
    with open(file_path, "r") as f:
        # We modified parser() to handle both! But wait, standard parser uses label_map.
        # Trace files don't have .text/.data. We just pass it to parser.
        instructions, memory = parser(f.read())
        
    # Resize memory based on VM config
    phys_size = config["vm"]["physical_size_bytes"]
    memory.size = phys_size
    memory.mem = bytearray(phys_size)

else:
    file_path = "program.asm"
    with open(file_path, "r") as f:
        instructions, memory = parser(f.read())

inst_mem = InstructionMemory(instructions) 

# Create Translator
# config.json contains VM config now, but AddressTranslator currently expects configparser format.
# Let's create a wrapper or just use configparser for AddressTranslator:
cfg = configparser.ConfigParser()
cfg.read("config_vm.ini")
translator = AddressTranslator(cfg, data_mem=memory)

cache_hierarchy = CacheHierarchy(config, memory, inst_mem)

sim = Simulator(inst_mem, memory, cache_hierarchy, translator=translator)
sim.run()

# ── Reporting ───────────────────────────────────────────────────────────
stats = cache_hierarchy.get_stats()
print("\n--- Cache Statistics ---")
for key, val in stats.items():
    print(f"{key}: {val*100:.2f}%")

if is_trace_mode:
    print(f"\n--- VM Statistics ---")
    print(f"TLB Hits                  : {translator.tlb_hits}")
    print(f"TLB Misses                : {translator.tlb_misses}")
    print(f"Page Walks                : {translator.page_walks}")
    print(f"Page Faults               : {translator.page_faults}")
    print(f"Page Evictions            : {translator.page_evictions}")
    print(f"Dirty Evictions           : {translator.dirty_evictions}")
    print(f"Swap Outs (to disk)       : {translator.swap_outs}")
    print(f"Swap Ins  (from disk)     : {translator.swap_ins}")
    print(f"Total Penalty Cycles      : {translator.total_penalty_cycles}")
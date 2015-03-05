import time
import multiprocessing
import router
import data_proc
import forward
import reg_proc
from commands import getoutput as bash

bash('mkdir '+LOCAL_DIR)

funcs = [router.run,
         data_proc.run,
         forward.run,
         reg_proc.run]

print forward.run.__name__

procs = [multiprocessing.Process(target = i) for i in funcs]

for p in procs:
    p.start()

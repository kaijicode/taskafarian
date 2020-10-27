import time

t1 = time.perf_counter()
time.sleep(0.5)
t2 = time.perf_counter()

print(f'{t2 - t1:.3f}s')


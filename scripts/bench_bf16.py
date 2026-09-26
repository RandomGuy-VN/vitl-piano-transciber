#!/usr/bin/env python3
"""A/B benchmark: fp32 vs bfloat16 autocast trên cùng audio piano tổng hợp."""
import sys
import time

sys.path.insert(0, "/home/z/my-project/vitl-piano-transciber")
import torch

torch.set_num_threads(2)
from services.transkun_service import TranskunService  # noqa: E402
import numpy as np  # noqa: E402


def piano_audio(dur):
    sr = 44100
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    notes = [261.63, 329.63, 392.0, 523.25]
    y = np.zeros_like(t)
    for i, start in enumerate(np.arange(0, dur, 4.0)):
        mask = (t >= start) & (t < start + 4.0)
        env = np.exp(-(t[mask] - start) * 1.2)
        f = notes[i % len(notes)]
        seg = np.zeros(mask.sum())
        for h in (1, 2, 3, 4):
            seg += np.sin(2 * np.pi * f * h * t[mask]) / h
        y[mask] = seg * env * 0.4
    return np.float32(y * 32767 / 2 ** 15).reshape(-1, 1)


model = TranskunService._load_model("cpu")
x = torch.from_numpy(piano_audio(60))


def run(dtype_ctx):
    t1 = time.time()
    with torch.inference_mode(), dtype_ctx:
        notes = model.transcribe(x, stepInSecond=12.0, segmentSizeInSecond=16.0, discardSecondHalf=False)
    dt = time.time() - t1
    # transcribe trả list[Note] sau khi flatten
    n_notes = len(notes)
    return dt, n_notes, notes


# fp32 (baseline)
fp32 = run(torch.autocast("cpu", enabled=False))
print(f"fp32     : {fp32[0]:.2f}s | notes={fp32[1]}")

# bfloat16 autocast
bf16 = run(torch.autocast("cpu", dtype=torch.bfloat16))
print(f"bfloat16 : {bf16[0]:.2f}s | notes={bf16[1]}")
print(f"Speedup  : {fp32[0]/bf16[0]:.2f}x | notes diff: {abs(fp32[1]-bf16[1])}/{fp32[1]}")

# chạy lại lần 2 để chắc chắn (steady state)
fp32b = run(torch.autocast("cpu", enabled=False))
bf16b = run(torch.autocast("cpu", dtype=torch.bfloat16))
print(f"Round 2  : fp32={fp32b[0]:.2f}s ({fp32b[1]} notes) | bf16={bf16b[0]:.2f}s ({bf16b[1]} notes) | speedup {fp32b[0]/bf16b[0]:.2f}x")

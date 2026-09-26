#!/usr/bin/env python3
"""Benchmark tốc độ in-process Transkun qua API /transcribe (multipart upload)."""
import io
import sys
import time
import wave
import numpy as np
import urllib.request


def make_wav(path, duration, kind):
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    if kind == "sine":
        y = (np.sin(2 * np.pi * 440 * t) * 0.5)
    else:  # piano-like: hợp âm C-E-G với envelope decay, đổi hợp âm mỗi 4s
        notes = [261.63, 329.63, 392.0, 523.25]
        y = np.zeros_like(t)
        for i, start in enumerate(np.arange(0, duration, 4.0)):
            mask = (t >= start) & (t < start + 4.0)
            env = np.exp(-((t[mask] - start)) * 1.2)
            f = notes[i % len(notes)]
            seg = np.zeros(mask.sum())
            for h in (1, 2, 3, 4):
                seg += np.sin(2 * np.pi * f * h * t[mask]) / h
            y[mask] = seg * env * 0.4
    pcm = (y * 32767).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def post_file(path, name):
    boundary = "----benchboundary1234"
    with open(path, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        "http://localhost:5000/transcribe",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read())
    return time.time() - t0, result


import json  # noqa: E402

tests = [("sine", 3), ("piano", 60)]
for kind, dur in tests:
    path = f"/tmp/bench_{kind}_{dur}.wav"
    make_wav(path, dur, kind)
    # Chạy 2 lần: lần 1 (nếu model chưa warm) + lần 2 (fully warm)
    for run in (1, 2):
        dt, res = post_file(path, f"{kind}_{dur}.wav")
        ok = res.get("success")
        el = res.get("elapsed_time_sec")
        size = res.get("midi_size_bytes")
        print(f"[{kind} {dur}s | run {run}] wall={dt:.2f}s | server_elapsed={el}s | midi={size}B | success={ok}")

# Realtime factor test với bài dài hơn
path = "/tmp/bench_piano_120.wav"
make_wav(path, 120, "piano")
dt, res = post_file(path, "piano_120.wav")
print(f"[piano 120s] wall={dt:.2f}s | server_elapsed={res.get('elapsed_time_sec')}s | RTF={dt/120:.3f}x realtime")

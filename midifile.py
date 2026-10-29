"""Write notes to a standard MIDI file with nothing but the standard library."""
import os
import re
import struct

PPQ = 96
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def note_name(pitch):
    return "%s%d" % (NAMES[pitch % 12], pitch // 12 - 1)


def describe(notes):
    return " ".join("%s@%g" % (note_name(int(n["pitch"])), float(n.get("start", 0))) for n in notes[:24]) + (
        " …" if len(notes) > 24 else "")


def encode(notes, bpm=120, name="Agent Composer"):
    events = []
    for n in notes:
        p = max(0, min(127, int(n["pitch"])))
        start = round(float(n.get("start", 0)) * PPQ)
        end = start + max(1, round(float(n.get("length", 1)) * PPQ))
        vel = max(1, min(127, round(float(n.get("velocity", 0.8)) * 127)))
        events.append((start, 1, bytes([0x90, p, vel])))
        events.append((end, 0, bytes([0x80, p, 0])))
    events.sort(key=lambda e: (e[0], e[1]))  # note-offs before note-ons at the same tick
    tempo = round(60_000_000 / float(bpm))
    title = name.encode("utf-8")[:120]
    trk = b"\x00\xff\x03" + _vlq(len(title)) + title
    trk += b"\x00\xff\x51\x03" + tempo.to_bytes(3, "big")
    last = 0
    for t, _, data in events:
        trk += _vlq(t - last) + data
        last = t
    trk += b"\x00\xff\x2f\x00"
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, PPQ) + b"MTrk" + struct.pack(">I", len(trk)) + trk


def write(folder, name, notes, bpm=120):
    safe = re.sub(r"[^\w\- ]+", "", name).strip() or "notes"
    p = os.path.join(folder, safe + ".mid")
    i = 2
    while os.path.exists(p):
        p = os.path.join(folder, "%s %d.mid" % (safe, i))
        i += 1
    with open(p, "wb") as f:
        f.write(encode(notes, bpm, name))
    return p

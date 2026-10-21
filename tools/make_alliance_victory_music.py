"""Alliance victory theme: the finale of Star Control II's ending theme.

The ending theme ("Final Victory Theme", base/cutscene/ending/victoryf.mod in
the UQM content) is a tracker module whose patterns are 7.68 s each. The cut
is its finale, orders 14-19 (1:47.52-2:27.20), and then pattern 8, a closing
chord that the song never reaches because its last pattern jumps back to
order 9.

The finale is taken from SC2MusicHomage's recording of the original PC
module ("Star Control II - Final Victory Music (Original PC MOD) - High
Quality"), which sounds like the game: the samples are played without
interpolation, as the PC game did, where ffmpeg's libopenmpt smooths them
and loses their bite. The recording loops at the jump back, so the closing
chord is rendered from the module by openmpt123 with interpolation off,
which matches the recording's pitch and timbre, and spliced on at the
pattern boundary, with the recording's 16 kHz MP3 roll-off.

    python3 tools/make_alliance_victory_music.py path/to/recording.mp3 path/to/victoryf.mod

Needs ffmpeg and openmpt123. Writes sounds/sc/alliance-victory.ogg.
"""

import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

OUT = "sounds/sc/alliance-victory.ogg"
RATE = 44100
PATTERN = 7.68         # seconds per pattern
LEAD = 0.0797          # the recording starts this much later than the module
ORDERS = [10, 4, 3, 9, 6, 7, 8]   # orders 14-19, then pattern 8
XFADE = 0.01


def read_wav(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16)
        return a.reshape(-1, w.getnchannels()).astype(np.float64) / 32768


def write_wav(path, a):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((np.clip(a, -1, 32767 / 32768) * 32768).astype(np.int16).tobytes())


def render_cut(mod_path, tmp):
    """The module with ORDERS as its order list, no interpolation."""
    with open(mod_path, "rb") as f:
        mod = bytearray(f.read())
    mod[950] = len(ORDERS)
    mod[952:1080] = bytes(ORDERS + [0] * (128 - len(ORDERS)))
    for pat in set(ORDERS):                               # drop position jumps (Bxx)
        for cell in range(1084 + pat * 1024, 1084 + (pat + 1) * 1024, 4):
            if mod[cell + 2] & 15 == 0xB:
                mod[cell + 2] &= 0xF0
                mod[cell + 3] = 0
    path = os.path.join(tmp, "cut.mod")
    with open(path, "wb") as f:
        f.write(mod)
    subprocess.run(["openmpt123", "-q", "--render", "--no-float", "--output-type", "wav",
                    "--samplerate", str(RATE), "--filter", "1", "--", path],
                   check=True, stdout=subprocess.DEVNULL)
    # The recording is an MP3 with nothing above about 16 kHz; so is the chord.
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path + ".wav",
                    "-af", "firequalizer=gain='if(gt(f,15800),-120,0)'", path + ".lp.wav"], check=True)
    return read_wav(path + ".lp.wav")


def main():
    recording, mod_path = sys.argv[1:3]
    with tempfile.TemporaryDirectory() as tmp:
        rec_wav = os.path.join(tmp, "rec.wav")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", recording,
                        "-ar", str(RATE), "-ac", "2", rec_wav], check=True)
        rec = read_wav(rec_wav)
        cut = render_cut(mod_path, tmp)

        # The finale from the recording, up to the start of pattern 8.
        finale_len = 5 * PATTERN + 1.28                   # orders 14-19 (order 17 is 1.28 s)
        start = round((14 * PATTERN + LEAD) * RATE)
        n = round(finale_len * RATE)
        head = rec[start:start + n]
        assert len(head) == n, "recording too short"

        # The closing chord from the render, brought to the recording's level
        # (measured over the last pattern, which both have).
        p7 = slice(n - round(PATTERN * RATE), n)
        gain = np.sqrt((head[p7] ** 2).mean() / (cut[p7] ** 2).mean())
        tail = cut[n:] * gain

        x = round(XFADE * RATE)
        ramp = np.linspace(0, 1, x)[:, None]
        tail[:x] = head[-x:] * (1 - ramp) + tail[:x] * ramp
        out = np.concatenate([head[:-x], tail])

        joined = os.path.join(tmp, "joined.wav")
        write_wav(joined, out)
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", joined,
                        "-af", "silenceremove=stop_periods=1:stop_threshold=-60dB:stop_duration=0.5",
                        "-q:a", "6", OUT], check=True)
    print(f"ok: {OUT}, closing chord gain {20 * np.log10(gain):+.1f} dB")


if __name__ == "__main__":
    main()

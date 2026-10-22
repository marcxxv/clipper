"""Local speech worker: float32 little-endian 16 kHz audio on stdin, JSON on stdout.

Keep PyAV's native libraries out of the process that imports OpenCV. No network
AI calls; faster-whisper may download the selected speech model on its first run.
"""
import json
import sys


def main():
    import numpy as np
    from faster_whisper import WhisperModel

    audio = np.frombuffer(sys.stdin.buffer.read(), dtype="<f4").copy()
    model = WhisperModel(sys.argv[1], device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
    words, lines = [], []
    for segment in segments:
        for word in segment.words or []:
            words.append({"w": word.word.strip(), "s": float(word.start), "e": float(word.end)})
        if segment.text.strip():
            lines.append((float(segment.start), segment.text.strip()))
    sys.stdout.write(json.dumps({"lang": info.language, "words": words, "lines": lines}))


if __name__ == "__main__":
    main()

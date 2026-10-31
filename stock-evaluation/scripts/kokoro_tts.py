"""Kokoro-82M neural narration for make_video.py (runs in its own venv: ~/.venvs/kokoro, Python 3.12).

usage: kokoro_tts.py <text file> <out.wav> [--voice af_heart] [--speed 1.0] [--lang a]
Voices: af_heart / af_bella (US female), am_michael / am_fenrir (US male), bf_emma (UK female), bm_george (UK male).
Setup once:  uv venv --python 3.12 ~/.venvs/kokoro && uv pip install --python ~/.venvs/kokoro/bin/python kokoro soundfile
             brew install espeak-ng   (fallback phonemiser for words outside the dictionary)
"""
import argparse
import warnings

warnings.filterwarnings("ignore")
import numpy as np
import soundfile as sf
from kokoro import KPipeline

ap = argparse.ArgumentParser()
ap.add_argument("text"); ap.add_argument("out")
ap.add_argument("--voice", default="af_heart"); ap.add_argument("--speed", type=float, default=1.0)
ap.add_argument("--lang", default="a", help="a = American English, b = British English")
a = ap.parse_args()

text = open(a.text, encoding="utf-8").read().strip()
pipe = KPipeline(lang_code=a.lang, repo_id="hexgrad/Kokoro-82M")
chunks = []
gap = np.zeros(int(24000 * 0.35), dtype=np.float32)      # a short breath between sentences
for _, _, audio in pipe(text, voice=a.voice, speed=a.speed, split_pattern=r"(?<=[.!?])\s+"):
    chunks.append(np.asarray(audio, dtype=np.float32)); chunks.append(gap)
sf.write(a.out, np.concatenate(chunks[:-1]), 24000)

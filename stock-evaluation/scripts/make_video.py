"""Narrated slide video for a ticker evaluation, in the 美投 valuation-video format.

Input: a list of slides, each {"id", "html" (slide body markup), "narration" (spoken text), optional "chart" (Plotly
figure dict rendered into <div id="chart">)}. Output: <outdir>/<name>.mp4 (1920x1080, H.264 + AAC, burnt-in subtitles),
<name>.srt, <name>.md (the script) and the slide PNGs.

Pipeline (all local): slide HTML -> headless Chrome screenshot; narration -> macOS `say` or Kokoro-82M neural TTS
(kokoro_tts.py, far more natural) -> ffmpeg; per-slide
durations from ffprobe; subtitles timed by sentence length; one ffmpeg pass muxes the image sequence, the audio and the
subtitles. Requirements: Google Chrome, ffmpeg with libass, macOS `say`. Python 3.9 compatible.
"""
import json
import os
import re
import shutil
import subprocess
import sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1920, 1080
PAD = 0.9          # seconds of silence after each slide's narration
VOICE = "Samantha"
RATE = 172
KOKORO_PY = os.path.expanduser("~/.venvs/kokoro/bin/python")   # see kokoro_tts.py for the one-time setup
KOKORO_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kokoro_tts.py")

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1920px;height:1080px;overflow:hidden;background:#0b1220;color:#e8eef7;
 font-family:-apple-system,"Helvetica Neue",Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
.slide{position:relative;width:1920px;height:1080px;padding:72px 96px 60px}
.kicker{font-size:26px;letter-spacing:.14em;text-transform:uppercase;color:#f0574a;font-weight:600;margin-bottom:14px}
h1{font-size:62px;line-height:1.12;font-weight:700;letter-spacing:-.01em;max-width:1500px}
h2{font-size:46px;line-height:1.15;font-weight:700;margin-bottom:34px;max-width:1700px}
.sub{font-size:30px;color:#9fb0c6;margin-top:22px;max-width:1500px;line-height:1.4}
.cols{display:flex;gap:64px;height:800px}
.col{flex:1;min-width:0}
.col.narrow{flex:0 0 720px}
.col.wide{flex:1 1 auto}
ul.b{list-style:none;font-size:32px;line-height:1.42}
ul.b li{position:relative;padding-left:40px;margin-bottom:22px;color:#dfe7f2}
ul.b li:before{content:"";position:absolute;left:0;top:18px;width:16px;height:16px;border-radius:3px;background:#f0574a}
ul.b li b{color:#fff}
.big{font-size:112px;font-weight:800;letter-spacing:-.02em;line-height:1}
.num{font-variant-numeric:tabular-nums}
.tiles{display:flex;gap:28px;margin-top:36px}
.tile{flex:1;background:#121c30;border:1px solid #223050;border-radius:14px;padding:28px 30px}
.tile .l{font-size:24px;color:#9fb0c6;text-transform:uppercase;letter-spacing:.08em}
.tile .v{font-size:60px;font-weight:800;margin-top:8px;letter-spacing:-.01em}
.tile .d{font-size:24px;color:#9fb0c6;margin-top:6px}
.red{color:#f0574a}.green{color:#3ecf8e}.amber{color:#f5b942}.blue{color:#6aa8ff}.muted{color:#9fb0c6}
table{border-collapse:collapse;width:100%;font-size:30px}
th,td{padding:16px 18px;text-align:right;border-bottom:1px solid #223050}
th{color:#9fb0c6;font-weight:600;font-size:26px;text-transform:uppercase;letter-spacing:.06em}
td:first-child,th:first-child{text-align:left}
tr.hl td{background:#172338;font-weight:700}
#chart{width:100%;height:100%}
.foot{position:absolute;left:96px;right:96px;bottom:28px;display:flex;justify-content:space-between;font-size:22px;color:#6f819a}
.callout{background:#172338;border-left:8px solid #f0574a;border-radius:10px;padding:26px 32px;font-size:32px;line-height:1.4;margin-top:30px}
.center{display:flex;flex-direction:column;justify-content:center;height:860px}
"""

def _plotly_src():
    """The plotly.js bundled with the Python plotly package (offline); falls back to the CDN."""
    try:
        import plotly
        p = os.path.join(os.path.dirname(plotly.__file__), "package_data", "plotly.min.js")
        if os.path.exists(p):
            return "file://" + p
    except ImportError:
        pass
    return "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"


PLOTLY = _plotly_src()


def _html(slide, foot_left, foot_right, n, total):
    chart = ""
    if slide.get("chart"):
        fig = json.dumps(slide["chart"])
        chart = (f"<script src='{PLOTLY}'></script><script>var f={fig};f.layout=f.layout||{{}};"
                 "f.layout.paper_bgcolor='rgba(0,0,0,0)';f.layout.plot_bgcolor='rgba(0,0,0,0)';"
                 "f.layout.font=Object.assign({color:'#dfe7f2',size:24,family:'Helvetica Neue, Helvetica, Arial'},f.layout.font||{});"
                 "f.layout.margin=f.layout.margin||{l:90,r:30,t:110,b:70};f.layout.title=Object.assign({x:0,y:0.98,yanchor:'top',font:{size:26}},f.layout.title||{});"
                 "Plotly.newPlot('chart',f.data,f.layout,{staticPlot:true});</script>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='slide'>"
            f"{slide['html']}<div class='foot'><span>{foot_left}</span><span>{foot_right} · {n}/{total}</span></div></div>{chart}</body></html>")


def _run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def _duration(path):
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).stdout.strip()
    return float(out)


def _sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def build(slides, outdir, name, foot_left="", foot_right="", tts="say", voice=None, rate=RATE, speed=1.0, keep=False):
    """tts: "say" (macOS voice, `voice` e.g. Samantha, `rate` wpm) or "kokoro" (Kokoro-82M neural, `voice` e.g. af_heart,
    `speed` 0.8-1.2; needs the venv described in kokoro_tts.py)."""
    voice = voice or ("af_heart" if tts == "kokoro" else VOICE)
    os.makedirs(outdir, exist_ok=True)
    work = os.path.join(outdir, "_build")
    os.makedirs(work, exist_ok=True)
    total = len(slides)
    pngs, wavs, durs = [], [], []
    for i, sl in enumerate(slides, 1):
        html = os.path.join(work, f"{i:02d}.html")
        png = os.path.join(work, f"{i:02d}.png")
        with open(html, "w", encoding="utf-8") as fh:
            fh.write(_html(sl, foot_left, foot_right, i, total))
        _run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
              f"--window-size={W},{H}", "--virtual-time-budget=6000", f"--screenshot={png}", "file://" + html])
        raw = os.path.join(work, f"{i:02d}." + ("aiff" if tts == "say" else "raw.wav"))
        wav = os.path.join(work, f"{i:02d}.wav")
        if tts == "kokoro":
            txt = os.path.join(work, f"{i:02d}.txt")
            with open(txt, "w", encoding="utf-8") as fh:
                fh.write(sl["narration"])
            _run([KOKORO_PY, KOKORO_SCRIPT, txt, raw, "--voice", voice, "--speed", str(speed)])
        else:
            _run(["say", "-v", voice, "-r", str(rate), "-o", raw, sl["narration"]])
        _run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", f"apad=pad_dur={PAD}", "-ar", "44100", "-ac", "2", wav])
        pngs.append(png); wavs.append(wav); durs.append(_duration(wav))
        print(f"slide {i}/{total}: {durs[-1]:.1f}s", file=sys.stderr)

    # subtitles: each slide's sentences share the slide's spoken time in proportion to their length
    srt, t, idx = [], 0.0, 1
    for sl, d in zip(slides, durs):
        spoken = d - PAD
        sents = _sentences(sl["narration"])
        chars = sum(len(s) for s in sents) or 1
        t0 = t
        for s in sents:
            dur = spoken * len(s) / chars
            srt.append(f"{idx}\n{_ts(t0)} --> {_ts(t0 + dur - 0.05)}\n{s}\n")
            t0 += dur; idx += 1
        t += d
    srt_path = os.path.join(outdir, name + ".srt")
    with open(srt_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(srt))

    # image sequence (concat demuxer) + concatenated audio
    lst = os.path.join(work, "video.txt")
    with open(lst, "w") as fh:
        for p, d in zip(pngs, durs):
            fh.write(f"file '{p}'\nduration {d:.3f}\n")
        fh.write(f"file '{pngs[-1]}'\n")
    alst = os.path.join(work, "audio.txt")
    with open(alst, "w") as fh:
        for wv in wavs:
            fh.write(f"file '{wv}'\n")
    audio = os.path.join(work, "audio.wav")
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", alst, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", audio])
    mp4 = os.path.join(outdir, name + ".mp4")
    style = "FontName=Helvetica Neue,FontSize=9.5,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=1.2,Shadow=0,MarginV=30,Bold=0"
    sub = srt_path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
          "-vf", f"fps=30,subtitles='{sub}':force_style='{style}',format=yuv420p",
          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-tune", "stillimage",
          "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest", mp4])

    with open(os.path.join(outdir, name + ".md"), "w", encoding="utf-8") as fh:
        fh.write(f"# {name}\n\n")
        for i, (sl, d) in enumerate(zip(slides, durs), 1):
            fh.write(f"## {i}. {sl.get('id', '')}  ({d:.0f}s)\n\n{sl['narration']}\n\n")
    if not keep:
        for f in os.listdir(work):
            if not f.endswith(".png"):
                os.remove(os.path.join(work, f))
    print(f"{mp4}  {sum(durs) / 60:.1f} min, {total} slides", file=sys.stderr)
    return mp4

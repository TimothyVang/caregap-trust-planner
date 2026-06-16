#!/usr/bin/env python3
"""Build a narrated placeholder demo video for CareGap Trust Planner.

ElevenLabs TTS narration over app-screenshot slides + title/close cards,
assembled with ffmpeg. Intended as a "good enough now, replace with a real
screen recording later" demo for the Devpost submission.

Requires: ffmpeg, the DejaVu font, and an ElevenLabs key in ELEVENLABS_API_KEY
(or ~/.elevenlabs_key). The key is read from the environment/file only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORK = Path("/tmp/caregap_video")
OUT = REPO / "docs" / "caregap_demo.mp4"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Sarah
MODEL = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
API = "https://api.elevenlabs.io/v1/text-to-speech"
W, H, BG = 1280, 720, "0x0d1117"
SHOTS = REPO / "assets" / "screenshots"

BEATS = [
    {"card": "title", "text": (
        "CareGap Trust Planner helps healthcare planners separate real care gaps "
        "from data uncertainty. A blank spot on the map is not automatically a "
        "medical desert. It may just be a data desert.")},
    {"img": SHOTS / "plan_tab.png", "text": (
        "In the Plan tab, you choose a capability and a region. Instead of simply "
        "counting facilities, CareGap aggregates trust-weighted evidence and labels "
        "each region as sufficient evidence, a likely care desert, or a data-poor "
        "area, with the planning confidence behind it.")},
    {"img": Path("/tmp/cg_refer.png"), "text": (
        "In the Refer tab, coordinators get referral candidates ranked by evidence, "
        "not just distance. Every candidate shows its trust level, the citations that "
        "support it, and what is missing or suspicious.")},
    {"img": SHOTS / "review_tab.png", "text": (
        "The Review tab surfaces the records that need a human. Facilities that claim "
        "a capability with no supporting evidence, or contradictory claims, are queued "
        "for review, and every override and decision is saved.")},
    {"card": "close", "text": (
        "Built as a Databricks app on the provided facility dataset, CareGap Trust "
        "Planner turns messy data into evidence-backed planning. We do not turn weak "
        "data into confident recommendations. We turn it into visible uncertainty and "
        "human review.")},
]


def get_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        p = Path.home() / ".elevenlabs_key"
        key = p.read_text().strip() if p.exists() else ""
    if not key:
        sys.exit("ELEVENLABS_API_KEY not set (and no ~/.elevenlabs_key)")
    return key.strip()


def tts(text: str, dst: Path, key: str) -> None:
    body = json.dumps({
        "text": text, "model_id": MODEL,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8,
                           "style": 0.0, "use_speaker_boost": True},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/{VOICE}", data=body, method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as exc:
        sys.exit(f"ElevenLabs HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')[:200]}")
    if len(audio) < 2000:
        sys.exit(f"suspiciously small audio for {text[:40]!r}")
    dst.write_bytes(audio)


def _drawtext(lines: list[tuple[str, int, str, int]]) -> str:
    parts = []
    for text, size, color, y in lines:
        safe = text.replace("'", "’")  # avoid breaking the single-quoted arg
        parts.append(
            f"drawtext=fontfile={FONT}:text='{safe}':fontcolor={color}"
            f":fontsize={size}:x=(w-text_w)/2:y={y}")
    return ",".join(parts)


def make_card(path: Path, lines: list[tuple[str, int, str, int]]) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", f"color=c={BG}:s={W}x{H}", "-frames:v", "1",
                    "-vf", _drawtext(lines), str(path)], check=True)


def make_clip(img: Path, mp3: Path, dst: Path) -> None:
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG},format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
                    "-framerate", "30", "-i", str(img), "-i", str(mp3),
                    "-c:v", "libx264", "-tune", "stillimage", "-r", "30",
                    "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
                    "-vf", vf, "-shortest", str(dst)], check=True)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    key = get_key()

    title_png, close_png = WORK / "title.png", WORK / "close.png"
    make_card(title_png, [
        ("CareGap Trust Planner", 64, "white", 250),
        ("Evidence-backed healthcare planning for messy facility data", 28, "0x8b949e", 350),
        ("Medical deserts vs. data deserts", 32, "0x1f6feb", 420)])
    make_card(close_png, [
        ("We turn weak data into visible uncertainty,", 38, "white", 250),
        ("not false confidence.", 38, "white", 305),
        ("Databricks Apps & Agents for Good 2026", 26, "0x8b949e", 420),
        ("github.com/TimothyVang/caregap-trust-planner", 24, "0x1f6feb", 470)])

    clips = []
    for i, beat in enumerate(BEATS, 1):
        img = {"title": title_png, "close": close_png}.get(beat.get("card")) or beat["img"]
        if not Path(img).exists():
            sys.exit(f"missing image: {img}")
        mp3 = WORK / f"beat_{i}.mp3"
        tts(beat["text"], mp3, key)
        clip = WORK / f"clip_{i}.mp4"
        make_clip(Path(img), mp3, clip)
        clips.append(clip)
        print(f"beat {i}: narrated + clip built")

    listing = WORK / "list.txt"
    listing.write_text("".join(f"file '{c}'\n" for c in clips))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", str(listing), "-c", "copy", str(OUT)], check=True)
    print(f"\nOUTPUT: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

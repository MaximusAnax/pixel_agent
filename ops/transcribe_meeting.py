#!/usr/bin/env python3
"""Transcribe a recorded meeting into a committed Markdown transcript.

Local-only by design: the audio never leaves your machine. Uses faster-whisper
(CTranslate2), which runs comfortably on CPU for the small/base models.

What it does
------------
1. Resolves a meeting date (from --date, the filename, or today).
2. Creates ops/meetings/<YYYY-MM-DD>/ if needed and seeds notes.md from the
   template (so a human/agent can add structured notes the synthesizer reads).
3. Transcribes the audio to transcript.md with [hh:mm:ss] segment timestamps.

Usage
-----
    python ops/meetings  # (see below — needs an audio file)
    python ops/transcribe_meeting.py path/to/recording.m4a
    python ops/transcribe_meeting.py rec.mp4 --date 2026-06-22 --model small.en

Models (accuracy vs speed): tiny.en < base.en < small.en < medium.en < large-v3.
`small.en` is a good default for English research meetings on CPU.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
MEETINGS_DIR = OPS_DIR / "meetings"
TEMPLATE = MEETINGS_DIR / "_TEMPLATE_notes.md"

_DATE_RE = re.compile(r"(\d{4})[-_]?(\d{2})[-_]?(\d{2})")


def resolve_date(explicit: str | None, audio: Path) -> dt.date:
    if explicit:
        return dt.date.fromisoformat(explicit)
    m = _DATE_RE.search(audio.stem)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return dt.date.today()


def fmt_ts(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def seed_notes(meeting_dir: Path, date: dt.date) -> None:
    notes = meeting_dir / "notes.md"
    if notes.exists():
        return
    if TEMPLATE.exists():
        text = TEMPLATE.read_text().replace("{{DATE}}", date.isoformat())
    else:
        text = f"# Meeting notes — {date.isoformat()}\n"
    notes.write_text(text)
    print(f"Seeded {notes}", file=sys.stderr)


def transcribe(audio: Path, model_name: str) -> list[tuple[float, str]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print(
            "faster-whisper is not installed. Run:\n"
            "    pip install -r ops/requirements.txt\n"
            "(and ensure `ffmpeg` is available for non-wav inputs).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    print(f"Loading model '{model_name}' (first run downloads weights)…", file=sys.stderr)
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio), vad_filter=True)
    print(
        f"Detected language '{info.language}' "
        f"(p={info.language_probability:.2f}); transcribing…",
        file=sys.stderr,
    )
    out: list[tuple[float, str]] = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            out.append((seg.start, text))
            print(f"  [{fmt_ts(seg.start)}] {text}", file=sys.stderr)
    return out


def render_transcript(date: dt.date, audio: Path, model_name: str,
                      segments: list[tuple[float, str]]) -> str:
    lines = [
        f"# Meeting transcript — {date.isoformat()}",
        "",
        f"> Auto-transcribed from `{audio.name}` with faster-whisper "
        f"(`{model_name}`) on {dt.date.today().isoformat()}. "
        "Verbatim; may contain errors. Structured human notes live in `notes.md`.",
        "",
    ]
    for start, text in segments:
        lines.append(f"- **[{fmt_ts(start)}]** {text}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audio", type=Path, help="path to the meeting recording (audio/video)")
    ap.add_argument("--date", help="meeting date YYYY-MM-DD (else inferred from filename/today)")
    ap.add_argument("--model", default="small.en", help="whisper model (default small.en)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing transcript.md")
    args = ap.parse_args()

    if not args.audio.exists():
        print(f"No such file: {args.audio}", file=sys.stderr)
        return 1

    date = resolve_date(args.date, args.audio)
    meeting_dir = MEETINGS_DIR / date.isoformat()
    meeting_dir.mkdir(parents=True, exist_ok=True)
    seed_notes(meeting_dir, date)

    transcript_path = meeting_dir / "transcript.md"
    if transcript_path.exists() and not args.force:
        print(f"{transcript_path} already exists (use --force to overwrite).", file=sys.stderr)
        return 1

    segments = transcribe(args.audio, args.model)
    transcript_path.write_text(render_transcript(date, args.audio, args.model, segments))
    print(f"Wrote {transcript_path} ({len(segments)} segments)", file=sys.stderr)
    print(f"\nNext: fill in {meeting_dir / 'notes.md'}, then run "
          f"`python ops/synthesize_state.py` to update Hermes' context.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

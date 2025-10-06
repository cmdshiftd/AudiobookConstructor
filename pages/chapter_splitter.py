#!/usr/bin/env python3
"""Chapter detection and splitting using Whisper transcription."""

import os
import re
import subprocess
import sys
import whisper


def load_chapter_titles(filename="chapter_titles.txt"):
    """Read chapter_titles.txt to obtain chronological chapters."""
    titles = []
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    titles.append(line)
    return titles


def find_sections(
    audio_file,
    pattern=r"(chapter (\d+)|introduction|conclusion|prologue|epilogue|foreword|afterword|dedication|acknowledgement|appendix|addendum|glossary|bibliography|index|preface)",
    model_size="base",
):
    """
    Transcribe the audio file and return matches of the regex pattern.
    Returns a list of dicts with 'start', 'end', 'text', and 'match' (the regex match object).
    """
    model = whisper.load_model(model_size)

    print(f"\n Transcribing '{audio_file}'... this may take a while")

    result = model.transcribe(audio_file)
    total_duration = result.get("duration")
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []

    # Debug: collect segments that might be chapters
    debug_segments = []

    for seg in result["segments"]:
        # Progress reporting
        if total_duration:
            progress = (seg["end"] / total_duration) * 100
            mm = int(seg["end"] // 60)
            ss = int(seg["end"] % 60)
            print(f"Progress: {progress:.0f}% ({mm:02d}:{ss:02d})")
        text = seg["text"]

        # Debug: check for any mention of "chapter" or just numbers
        if re.search(r'\bchapter\b|\b(one|two|three|four|five|1|2|3|4|5)\b', text, re.IGNORECASE):
            debug_segments.append((seg["start"], text.strip()))

        for match in regex.finditer(text):
            matches.append(
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "match": match,
                }
            )
            # Debug output
            print(f"  Found: '{match.group(0)}' at {int(seg['start']//60):02d}:{int(seg['start']%60):02d}")

    # Debug: show potential chapter segments
    if not matches and debug_segments:
        print("\n  Debug: Found segments containing 'chapter' or numbers (first 10):")
        for start, text in debug_segments[:10]:
            mm = int(start // 60)
            ss = int(start % 60)
            print(f"    {mm:02d}:{ss:02d} - {text}")

    # Sort matches by start time
    matches.sort(key=lambda m: m["start"])

    # Find the first and last real chapter timestamps
    first_chapter_start = None
    last_chapter_start = None
    for m in matches:
        if m["match"].group(2):  # has a chapter number
            if first_chapter_start is None:
                first_chapter_start = m["start"]
            last_chapter_start = m["start"]

    # Only group/print non-chapter keywords
    non_chapter_keywords = [
        "introduction",
        "conclusion",
        "prologue",
        "epilogue",
        "foreword",
        "afterword",
        "preface",
        "appendix",
        "addendum",
        "glossary",
        "bibliography",
        "index",
        "dedication",
        "acknowledgement",
    ]
    non_chapters = {}

    for m in matches:
        kw = m["match"].group(1)
        if not kw:
            continue
        kw_lower = kw.strip().lower()
        if kw_lower in non_chapter_keywords:

            # Must occur before the first chapter
            if kw_lower in ["introduction", "prologue", "foreword", "preface"]:
                if (
                    first_chapter_start is not None
                    and m["start"] >= first_chapter_start
                ):
                    continue

            # Must occur after the last chapter
            if kw_lower in [
                "conclusion",
                "epilogue",
                "afterword",
                "appendix",
                "addendum",
                "glossary",
                "bibliography",
                "index",
            ]:
                if last_chapter_start is not None and m["start"] <= last_chapter_start:
                    continue

            # Dedication & Acknowledgement allowed before first OR after last chapter
            if kw_lower in ["dedication", "acknowledgement"]:
                if (
                    first_chapter_start is not None
                    and m["start"] >= first_chapter_start
                ) and (
                    last_chapter_start is not None and m["start"] <= last_chapter_start
                ):
                    continue

            key = kw.strip().capitalize()
            if key not in non_chapters:
                non_chapters[key] = []
            non_chapters[key].append(m["start"])

    return matches, result, non_chapters


def split_chapters(audio_file, output_dir=None, model_size="base", use_titles=True):
    r"""
    Splits the audio file into chapters based on 'chapter (\d+)' markers.
    Returns a list of dicts with chapter number, start time, end time, and output file.
    """
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(audio_file))

    pattern = r"(chapter (\d+)|introduction|prologue|epilogue|preface|conclusion)"
    matches, result, non_chapters = find_sections(
        audio_file, pattern=pattern, model_size=model_size
    )
    if not matches:
        print("\n ⚠️  No chapter markers found in the audio file.")
        print("   Will convert as a single audiobook file without chapters.\n")
        return [], non_chapters

    os.makedirs(output_dir, exist_ok=True)

    titles = load_chapter_titles() if use_titles else []
    seen_chapters = set()

    # Sort by start time
    matches.sort(key=lambda m: m["start"])

    chapters = []
    for idx, m in enumerate(matches):
        if m["match"].group(2):
            chapter_num = int(m["match"].group(2))
            if chapter_num in seen_chapters:
                continue
            seen_chapters.add(chapter_num)
            if use_titles and 1 <= chapter_num <= len(titles):
                chapter_label = f"Chapter {chapter_num} - {titles[chapter_num - 1]}"
            else:
                chapter_label = f"Chapter {chapter_num}"
        else:
            # Skip non-chapter keywords
            continue
        start = m["start"]
        # End is the start of the next chapter, or end of audio
        if idx + 1 < len(matches):
            end = matches[idx + 1]["start"]
        else:
            # Use last segment end time as the end
            if "segments" in result and result["segments"]:
                end = result["segments"][-1]["end"]
            else:
                end = None  # fallback
        input_ext = os.path.splitext(audio_file)[1]
        output_filename = os.path.join(output_dir, f"{chapter_label}{input_ext}")
        chapters.append(
            {
                "chapter": chapter_label,
                "start": start,
                "end": end,
                "file": output_filename,
            }
        )

    # Sort chapters numerically BEFORE exporting
    def chapter_sort_key(ch):
        match = re.match(r"Chapter (\d+)", ch["chapter"])
        if match:
            return int(match.group(1))
        return 9999

    chapters.sort(key=chapter_sort_key)

    # Check if any actual chapters were found
    if not chapters:
        print("\n ⚠️  No numbered chapters found in the audio file.")
        print("   Will convert as a single audiobook file without chapters.\n")
        return [], non_chapters

    # Now export in sorted order
    for ch in chapters:
        start = ch["start"]
        end = ch["end"]
        output_filename = ch["file"]
        chapter_label = ch["chapter"]

        if end is not None:
            duration = end - start
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                audio_file,
                "-ss",
                str(start),
                "-t",
                str(duration),
                "-c",
                "copy",
                output_filename,
            ]
        else:
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                audio_file,
                "-ss",
                str(start),
                "-c",
                "copy",
                output_filename,
            ]

        start_min = int(start // 60)
        start_sec = int(start % 60)
        try:
            subprocess.run(
                ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            print(f"  ✅   Exported: {chapter_label}: {start_min:02d}:{start_sec:02d}")
        except subprocess.CalledProcessError as e:
            print(f"\n ❌ Error: ffmpeg failed for {chapter_label}: {e}\n\n")
            continue

    return chapters, non_chapters

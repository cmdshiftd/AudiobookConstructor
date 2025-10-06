#!/usr/bin/env python3
"""Audio processing functions using FFmpeg and pydub."""

import os
import re
import subprocess
import sys
import time
from tqdm import tqdm


def sort_chapters_numerically(s):
    """Sort chapters into numerical order."""
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)
    ]


def get_codec(audio_dir, file_path):
    """Get audio codec of a file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    print(f"\n Converting '{audio_dir.split('/')[-1]}' ({result.stdout.strip()})...")

    return result.stdout.strip()


def get_duration(file_path):
    """Return duration of file in milliseconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        capture_output=True,
        text=True,
    )
    return int(float(result.stdout.strip()) * 1000)


def write_concat_list(audio_dir, temp_files):
    """Write concat list file with absolute paths."""
    concat_list_path = os.path.join(audio_dir, "temp_concat_list.txt")
    with open(concat_list_path, "w") as concatlist:
        for temp_file in temp_files:
            if not os.path.exists(temp_file):
                print("\n ❌ Error: temp file not found:\n\n", temp_file)
                sys.exit(1)

            concatlist.write(
                f"file '{os.path.abspath(temp_file).replace("'", "''")}'\n"
            )

    return concat_list_path


def generate_lists(audio_dir, original_files):
    """Write filelist.txt and chapters.txt."""
    filelist = os.path.join(audio_dir, "filelist.txt")
    chapters = os.path.join(audio_dir, "chapters.txt")

    with open(filelist, "w") as filelisttxt:
        for fn in original_files:
            filelisttxt.write(f"{os.path.join(audio_dir, fn)}\n")

    total_duration = sum(
        get_duration(os.path.join(audio_dir, fn)) for fn in original_files
    )
    concat_list_path = os.path.join(audio_dir, "temp_concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        f.write("")

    start = 0
    with open(chapters, "w") as chapterstxt:
        chapterstxt.write(";FFMETADATA1\n")

        # If only one file, create a single chapter with the book title
        if len(original_files) == 1:
            end = total_duration
            title = os.path.basename(audio_dir)  # Use audiobook name as chapter title
            chapterstxt.write(
                f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={title}\n\n"
            )
        else:
            # Multiple chapters - use filenames as titles
            for _, fn in enumerate(original_files, 1):
                end = start + get_duration(os.path.join(audio_dir, fn))
                chapterstxt.write(
                    f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={fn.replace(' - ', ': ')}\n\n"
                )
                start = end

    return filelist, chapters, total_duration, concat_list_path


def re_encode(concat_list_path, output_file):
    """Concatenate with re-encode (safer than copy)."""
    concat_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        concat_list_path,
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        output_file,
    ]
    subprocess.run(concat_command, check=True)


def add_metadata(
    audio_dir, book_cover, chapters, output_file, concat_list_path, author=None, has_chapters=True
):
    """Add chapters metadata into a new file (ffmpeg cannot edit in-place)."""
    final_file = os.path.join(audio_dir, f"{os.path.basename(audio_dir)}.m4b")
    temp_final_file = os.path.join(
        audio_dir, f"{os.path.basename(audio_dir)}_with_chapters.m4b"
    )

    chapter_command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        final_file,
        "-i",
        chapters,
        "-i",
        book_cover,
    ]
    chapter_command.extend(
        [
            "-map_metadata",
            "1",
            "-c:a",
            "copy",
            "-metadata",
            f"title={os.path.basename(audio_dir)}",
            "-metadata",
            f"album={os.path.basename(audio_dir)}",
            "-metadata",
            f"author={author}",
            "-metadata",
            f"artist={author}",
        ]
    )
    chapter_command.extend(
        [
            "-map",
            "0:a",
            "-map",
            "2",
            "-c:v",
            "mjpeg",
            "-disposition:v",
            "attached_pic",
        ]
    )

    if has_chapters:
        print(f"\n Encoding, organising chapters and adding cover...")
    else:
        print(f"\n Encoding and adding cover...")
    re_encode(concat_list_path, output_file)

    chapter_command.append(temp_final_file)
    result = subprocess.run(chapter_command, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(temp_final_file):
        print("FFmpeg failed to add chapters and/or cover:\n", result.stderr)
        sys.exit(1)
    os.replace(temp_final_file, output_file)


def convert_mp3(
    author,
    filelist,
    chapters,
    audio_dir,
    audio_file,
    book_cover,
    total_duration,
    files,
    temp_files,
    cumulative_duration,
    start_time,
    output_file,
    concat_list_path,
    use_titles=True,
):
    """Convert mp3 files to m4a, then concatenate with chapters metadata into m4b."""
    with open(filelist, "r") as f:
        for line in f:
            path = line.strip()
            if path.startswith("'") and path.endswith("'"):
                path = path[1:-1]
            elif path.startswith('"') and path.endswith('"'):
                path = path[1:-1]
            files.append(path)

    with tqdm(files, unit="file") as pbar:
        for input_file in pbar:
            duration = get_duration(input_file)
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            temp_file = os.path.join(audio_dir, f"{base_name}.m4a")

            if os.path.exists(temp_file):
                os.remove(temp_file)
            temp_files.append(temp_file)

            with open(
                os.path.join(audio_dir, "temp_concat_list.txt"), "a", encoding="utf-8"
            ) as templist:
                safe_path = os.path.abspath(temp_file).replace("'", "'\\''")
                templist.write(f"file '{safe_path}'\n")

            command = [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                input_file,
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-ac",
                "2",
                temp_file,
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"\nFFmpeg failed for {input_file}:\n{result.stderr}")
                sys.exit(1)

            if not os.path.exists(temp_file):
                print("\n ❌ Error: Failed to create temp file:\n\n", temp_file)
                sys.exit(1)

            cumulative_duration += duration
            percentage = cumulative_duration / total_duration * 100
            elapsed_time = time.time() - start_time
            if cumulative_duration > 0:
                estimated_total_time = elapsed_time / (
                    cumulative_duration / total_duration
                )
                eta_seconds = int(estimated_total_time - elapsed_time)
                eta_minutes = eta_seconds // 60
                eta_seconds = eta_seconds % 60
                eta_str = f"{eta_minutes}m {eta_seconds}s"

                pbar.set_postfix({"Progress": f"{percentage:.1f}%", "ETA": eta_str})
                pbar.write(f"  ✅   {base_name}")

    # Determine if we have multiple chapters or just one file
    has_chapters = len(files) > 1
    add_metadata(audio_dir, book_cover, chapters, output_file, concat_list_path, author, has_chapters)

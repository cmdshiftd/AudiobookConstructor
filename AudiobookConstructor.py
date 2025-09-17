#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import time
import warnings
import whisper
import zipfile

from datetime import datetime
from tqdm import tqdm


# Validate files and directories
def error_checking(audio_dir, audio_file):
    if os.path.isdir(audio_dir):
        print(f"\n ❌ Error: Directory '{audio_dir}' already exists.\n\n")
        sys.exit(1)

    if audio_file not in str(os.listdir(".")) or not os.path.isfile(audio_file):
        print(f"\n ❌ Error: The audio file '{audio_file}' does not exist.\n\n")
        sys.exit(1)

    if not audio_file.endswith(".mp3"):
        print(f"\n ❌ Error: The audio file does not have an mp3 extension.\n\n")
        sys.exit(1)

    if not os.path.exists(f"{audio_file.split(".")[0]}.jpg"):
        print(
            f"\n ❌ Error: Book cover '{audio_file.split(".")[0]}.jpg' could not be found.\n\n"
        )
        sys.exit(1)

    return f"{audio_file.split(".")[0]}.jpg"


# Read chapter_titles.txt to obtain chorniclogical chapters
def load_chapter_titles(filename="chapter_titles.txt"):
    titles = []
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    titles.append(line)
    return titles


# Identify occurances of chapter titles
def find_sections(
    audio_file,
    pattern=r"(chapter (\d+)|introduction|conclusion|prologue|epilogue|foreword|afterword|dedication|acknowledgement|appendix|addendum|glossary|bibliography|index|preface)",
    model_size="base",
):
    # Transcribe the audio file and return matches of the regex pattern.
    # Returns a list of dicts with 'start', 'end', 'text', and 'match' (the regex match object).
    model = whisper.load_model(model_size)

    print(f"\n Transcribing '{audio_file}'... this may take a while")

    result = model.transcribe(audio_file)
    total_duration = result.get("duration")
    regex = re.compile(pattern, re.IGNORECASE)
    matches = []

    for seg in result["segments"]:
        # Progress reporting
        if total_duration:
            progress = (seg["end"] / total_duration) * 100
            mm = int(seg["end"] // 60)
            ss = int(seg["end"] % 60)
            print(f"Progress: {progress:.0f}% ({mm:02d}:{ss:02d})")
        text = seg["text"]

        for match in regex.finditer(text):
            matches.append(
                {
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "match": match,
                }
            )

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


# Extract chapters from original file
def split_chapters(audio_file, output_dir=None, model_size="base"):
    # Splits the audio file into chapters based on 'chapter (\d+)' markers.
    # Returns a list of dicts with chapter number, start time, end time, and output file.
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(audio_file))
    os.makedirs(output_dir, exist_ok=True)

    pattern = r"(chapter (\d+)|introduction|prologue|epilogue|preface|conclusion)"
    matches, result, non_chapters = find_sections(
        audio_file, pattern=pattern, model_size=model_size
    )
    if not matches:
        print("No chapter markers found.")
        return []

    titles = load_chapter_titles()
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
            if 1 <= chapter_num <= len(titles):
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


# Sort chapters into numerical order
def sort_chapters_numerically(s):
    return [
        int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)
    ]


# Handle awkward characters in file names
def replace_special_characters(audio_dir, original_files):
    for i, filename in enumerate(original_files):
        if "'" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("'", "’")),
            )
            original_files[i] = filename.replace("'", "’")
        if "\\" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("\\", "-")),
            )
            original_files[i] = filename.replace("\\", "-")
        if "%" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("%", "pc")),
            )
            original_files[i] = filename.replace("%", "pc")

    return original_files


# Function to get audio codec of a file using ffprobe
def get_codec(audio_dir, file_path):
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


# Function to get duration of audio file in milliseconds using ffprobe
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


# Write concat list file with absolute paths
def write_concat_list(audio_dir, temp_files):
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


# Write filelist.txt and chapters.txt
def generate_lists(audio_dir, original_files):
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
        for _, fn in enumerate(original_files, 1):
            end = start + get_duration(os.path.join(audio_dir, fn))
            chapterstxt.write(
                f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={fn.replace(' - ', ': ')}\n\n"
            )
            start = end

    return filelist, chapters, total_duration, concat_list_path


# Concatenate with re-encode (safer than copy)
def re_encode(concat_list_path, output_file):
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


# Add chapters metadata into a new file (ffmpeg cannot edit in-place)
def add_metadata(
    audio_dir, book_cover, chapters, output_file, concat_list_path, author=None
):
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

    print(f"\n Encoding, organising chapters and adding cover...")
    re_encode(concat_list_path, output_file)

    chapter_command.append(temp_final_file)
    result = subprocess.run(chapter_command, capture_output=True, text=True)
    if result.returncode != 0 or not os.path.exists(temp_final_file):
        print("FFmpeg failed to add chapters and/or cover:\n", result.stderr)
        sys.exit(1)
    os.replace(temp_final_file, output_file)


def back_up(audio_dir, audio_file):
    # Copy Audiobook file
    shutil.copy2(
        os.path.join(f"{audio_dir}", f"{audio_file.split(".")[0]}.m4b"),
        f"{audio_file.split(".")[0]}.m4b",
    )

    # Copy chapter_titles
    shutil.copy2(
        "chapter_titles.txt",
        os.path.join(f"{audio_dir}", "chapter_titles.txt"),
    )

    # Copy original file
    os.rename(
        f"{audio_file}",
        os.path.join(f"{audio_dir}", f"{audio_file}"),
    )

    # Copy book cover
    os.rename(
        f"{audio_file.split(".")[0]}.jpg",
        os.path.join(f"{audio_dir}", f"{audio_file.split(".")[0]}.jpg"),
    )


# Cleanup temporary files
def clean_up(audio_dir, audio_file):
    for textfile in os.listdir(audio_dir):
        if textfile.endswith(".txt"):
            os.remove(os.path.join(audio_dir, textfile))

    back_up(audio_dir, audio_file)

    with zipfile.ZipFile(
        os.path.join(f"{os.path.basename(audio_dir)}.orig.zip"),
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        for root, _, files in os.walk(audio_dir):
            for file in files:
                archive.write(
                    os.path.join(root, file),
                    arcname=os.path.relpath(os.path.join(root, file), audio_dir),
                )

    shutil.rmtree(audio_dir)


# Convert mp3 files to m4a, then concatenate with chapters metadata into m4b
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
):
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

    add_metadata(audio_dir, book_cover, chapters, output_file, concat_list_path, author)
    clean_up(audio_dir, audio_file)


def main():
    subprocess.Popen(["clear"])
    time.sleep(0.1)

    if len(sys.argv) < 3:
        print("Usage: python3 AudiobookConstructor_new.py <audiobook_file> <author>")
        sys.exit(1)

    warnings.filterwarnings("ignore")
    audio_file = sys.argv[1]
    author = sys.argv[2]
    audio_dir = audio_file.split(".")[0]

    book_cover = error_checking(audio_dir, audio_file)

    os.makedirs(audio_dir, exist_ok=True)

    # Extract chapters from orignal single audio file
    chapters, non_chapters = split_chapters(audio_file, output_dir=audio_dir)

    print(
        f"\n Chapters 1 through {str(len(chapters))} have been extracted successfully."
    )

    if len(non_chapters) > 0:
        print(
            "\n   Manual extraction is required for non-chapters.\n    === Potential non-chapter occurrences ==="
        )
        for keyword, timestamps in non_chapters.items():
            formatted_times = []
            for t in timestamps:
                start_min = int(t // 60)
                start_sec = int(t % 60)
                formatted_times.append(f"{start_min:02d}:{start_sec:02d}")
            print(f"    - '{keyword}':\t{', '.join(formatted_times)}")
        time.sleep(20)
        print()

        input("    Press any key to continue...\n")

    time.sleep(2)
    subprocess.Popen(["clear"])
    time.sleep(0.1)

    # Begin conversion and amalgamation of extracted chapters into single m4b file
    files = []
    temp_files = []
    cumulative_duration = 0
    start_time = time.time()
    output_file = os.path.join(audio_dir, f"{os.path.basename(audio_dir)}.m4b")

    original_files = sorted(
        [
            f
            for f in os.listdir(audio_dir)
            if f.lower().endswith((".mp3", ".m4a", ".aac"))
        ],
        key=sort_chapters_numerically,
    )
    if not original_files:
        print("No audio files found.")

    original_files = replace_special_characters(audio_dir, original_files)

    filelist, chapters, total_duration, concat_list_path = generate_lists(
        audio_dir, original_files
    )

    codec = get_codec(audio_dir, os.path.join(audio_dir, original_files[-1]))
    if codec == "mp3":
        convert_mp3(
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
        )
    else:
        print(f"File codec for {audio_dir} is not mp3 and is not supported.")
        sys.exit(1)

    print(f"\n Completed conversion for '{audio_dir.split('/')[-1]}'\n\n\n")


if __name__ == "__main__":
    main()

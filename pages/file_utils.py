#!/usr/bin/env python3
"""File validation and utility functions."""

import os
import shutil
import sys
import zipfile


def error_checking(audio_dir, audio_file):
    """Validate files and directories."""
    if os.path.isdir(audio_dir):
        print(f"\n ❌ Error: Directory '{audio_dir}' already exists.\n\n")
        sys.exit(1)

    if audio_file not in str(os.listdir(".")) or not os.path.isfile(audio_file):
        print(f"\n ❌ Error: The audio file '{audio_file}' does not exist.\n\n")
        sys.exit(1)

    if not audio_file.endswith(".mp3"):
        print(f"\n ❌ Error: The audio file does not have an mp3 extension.\n\n")
        sys.exit(1)

    if not os.path.exists(f"{audio_file.split('.')[0]}.jpg"):
        print(
            f"\n ❌ Error: Book cover '{audio_file.split('.')[0]}.jpg' could not be found.\n\n"
        )
        sys.exit(1)

    return f"{audio_file.split('.')[0]}.jpg"


def replace_special_characters(audio_dir, original_files):
    """Handle awkward characters in file names."""
    for i, filename in enumerate(original_files):
        if "'" in filename:
            os.rename(
                os.path.join(audio_dir, filename),
                os.path.join(audio_dir, filename.replace("'", "'")),
            )
            original_files[i] = filename.replace("'", "'")
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


def back_up(audio_dir, audio_file, use_titles=True):
    """Back up audiobook file and related files."""
    # Copy Audiobook file
    shutil.copy2(
        os.path.join(f"{audio_dir}", f"{audio_file.split('.')[0]}.m4b"),
        f"{audio_file.split('.')[0]}.m4b",
    )

    # Copy chapter_titles if they were used
    if use_titles and os.path.exists("chapter_titles.txt"):
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
        f"{audio_file.split('.')[0]}.jpg",
        os.path.join(f"{audio_dir}", f"{audio_file.split('.')[0]}.jpg"),
    )


def clean_up(audio_dir, audio_file, use_titles=True):
    """Cleanup temporary files."""
    for textfile in os.listdir(audio_dir):
        if textfile.endswith(".txt"):
            os.remove(os.path.join(audio_dir, textfile))

    back_up(audio_dir, audio_file, use_titles)

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

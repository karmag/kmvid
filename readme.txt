Setup

    ffmpeg and ffprobe executables needed in your path, can be
    downloaded at https://ffmpeg.org/download.html

Tests

    Run tests with test.bat or use command

        > uv run pytest

Build

    Generate source and binary into dist/

        > uv build

lint check

    Run check

        > uv tool run ruff check src

Generate doc

    Output placed in doc/ directory

        > uv run doc

Examples

    Generates video file

        > uv run example\cards.py
        > uv run example\text_blocks.py

    Prints fonts with variants found on the system to console

        > uv run example\fonts.py

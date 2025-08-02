Setup

    ffmpeg and ffprobe executables needed in bin/ directory, can be
    downloaded at https://ffmpeg.org/download.html

Tests

    Run tests with test.bat or use command

        > uv run python -m unittest discover --start-directory test -v

Build

    Generate source and binary into dist/

        > uv build

lint check

    Install ruff

        > uv tool install ruff

    Run check

        > uv tool run ruff check kmvid

Generate doc

    Output placed in doc/ directory

        > uv run doc

Examples

    Generates video file

        > uv run python example\cards.py
        > uv run python example\text_blocks.py

    Prints fonts with variants found on the system to console

        > uv run python example\fonts.py

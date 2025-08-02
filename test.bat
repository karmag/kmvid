@echo off

cls

uv run python -m unittest discover --start-directory test -v

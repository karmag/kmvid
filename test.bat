@echo off

if not defined VIRTUAL_ENV (
   call Scripts\activate.bat
)

cls

python -m unittest discover --start-directory test -v

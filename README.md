# random-stuff
Some random scripts and programs written by myself for various daily (and not really) purposes or for single use.
They reflect the way I used to learn python programming, and might be helpful for someone. If any bugs're spotted,
feel free to report it.

Most of these scripts were written from scratch for some one-time task, or some for automation. They are not supposed 
to be full-fledged problem solvers. If you like any of them, freely copy, modify, and do whatever you like! :)
They are all MIT licensed.

## EagleCAD Recover Script
* `eagle_recover.py`
Status: almost all features working, no thorough testing

Very simple tool I wrote for single use, when accidently erased the full project directory with all work done.
It might come in use some time for anybody. Needs some tuning, no performance measurements taken.

## HTTP File Extract
Another yet simple script, that extracts files embedded inside stored-email files or raw HTTP responses.

## Arduino Morse Beeper w/Codegen
Time spent: 2hr
Status: almost all features working, no thorough testing

A simple Morse encoder with static sentences. Should take the index of a sentence to transmit from external DIP-switch,
and then periodically beeps it using externally attached buzzer.

This sketch comes with simplistic code generator that takes the dict of characters with corresponding codes and packs 
it into condensed binary representation as 2 tables: one for the Morse sequences themselves, and other one for sequence 
lengths. The charactes in these tables are sorted by their ASCII-code (got with `ord` function), and written in sequence.
The selection of particular character code is made with generated `if` operator.

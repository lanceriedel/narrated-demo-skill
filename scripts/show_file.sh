#!/usr/bin/env bash
# Page a text file in the current terminal with a 1 Hz clock line, so screencapture -V keeps advancing.   show_file.sh <file> [first-line]
# Ctrl-C to stop. Use inside a pane you are recording with record_screen.sh (e.g. via `herdr pane run`).
F=$1; FROM=${2:-1}
clear; while :; do tput cup 0 0; sed -n "${FROM},$(( $(tput lines) + FROM - 3 ))p" "$F" | cut -c1-"$(tput cols)"; printf '\n\033[2m%s\033[0m\n' "$(date +%T)"; sleep 1; done

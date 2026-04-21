#!/bin/bash

export PYGAME_HIDE_SUPPORT_PROMPT='hide'

./disc_jockey.py \
  --ollama \
  --model 'gemma4:latest' \
  -n 16 \
  -d $HOME/Desktop/Disney \
  -r 1.0

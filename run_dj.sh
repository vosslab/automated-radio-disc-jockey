#!/bin/bash

export PYGAME_HIDE_SUPPORT_PROMPT='hide'

./disc_jockey.py \
  --ollama --model 'gemma4:e4b-it-q8_0' \
  -n 24 \
  -d $HOME/Documents/ipod/ \
  -r 1.2

#!/usr/bin/env bash

# Python 3.12 runtime defaults for this repo
unset PYTHONHOME
unset PYTHONPATH
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHON_VERSION=3.12
export PATH="/opt/homebrew/opt/python@3.12/libexec/bin:$PATH"
export PIP_DISABLE_PIP_VERSION_CHECK=1
alias py312="/opt/homebrew/opt/python@3.12/bin/python3.12"

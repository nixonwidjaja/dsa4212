#!/bin/bash

venv_dir="./env"

if [ ! -d $venv_dir ]; then
    python -m venv $venv_dir
    source $venv/bin/activate
    pip install -r requirements.txt
fi

source $venv_dir/bin/activate
python lstm_train.py
deactivate
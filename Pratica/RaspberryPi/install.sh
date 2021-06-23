#!/bin/bash
sudo apt install -y libhdf5-dev libhdf5-103
sudo apt install -y libatlas-base-dev liblapacke-dev gfortran
pip3 install https://github.com/lhelontra/tensorflow-on-arm/releases/download/v2.4.0/tensorflow-2.4.0-cp37-none-linux_armv7l.whl
pip3 install -r SGU-requirements.txt

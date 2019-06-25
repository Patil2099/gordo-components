#!/usr/bin/env bash

set -e
set -x

if [[ "$TRAVIS_OS_NAME" == "osx" ]]; then
	# You can change what anaconda version you want at
    # https://repo.continuum.io/archive/
    curl -Ok https://repo.continuum.io/archive/Anaconda3-4.1.1-MacOSX-x86_64.sh
    bash Anaconda3-4.1.1-MacOSX-x86_64.sh -b -p ~/anaconda
    rm Anaconda3-4.1.1-MacOSX-x86_64.sh
else
    # You can change what anaconda version you want at
    # https://repo.continuum.io/archive/
    wget https://repo.continuum.io/archive/Anaconda3-5.0.1-Linux-x86_64.sh --quiet
    bash Anaconda3-5.0.1-Linux-x86_64.sh -b -p ~/anaconda
    rm Anaconda3-5.0.1-Linux-x86_64.sh
fi

~/anaconda/bin/conda create -n py python=$PYTHON_VERSION -y
~/anaconda/bin/conda activate py

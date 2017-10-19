#SHELL = /bin/bash -x

all:
	export PYTHONWARNINGS="ignore:Unverified HTTPS request"
	python peer.py
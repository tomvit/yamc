# Makefile for res2-service
# uses version from git with commit hash

help:
	@echo "make <target>"
	@echo "build	build platformw package in 'dist' directory."
	@echo "clean	clean all temporary directories."
	@echo ""

build:
	python setup.py egg_info sdist	

plugins:
	python plugins/yamc-oracle/setup.py egg_info sdist	

check:
	pylint yamc 

clean:
	rm -fr build
	rm -fr dist
	rm -fr yamc/*.egg-info



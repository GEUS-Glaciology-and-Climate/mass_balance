container_cmd ?= docker
container_args ?= run -it --user $(shell id -u):$(shell id -g) --mount type=bind,src="${DATADIR}",dst=/data --mount type=bind,src="$(shell pwd)",dst=/home/user --env PARALLEL="--delay 0.1 -j -1"

# --user $(shell id -u):$(shell id -g) --mount type=bind,src=$${DATADIR},dst=/data --mount type=bind,src=$(shell pwd),dst=/home/user --env PARALLEL="--delay 0.1 -j -1"

org-babel = emacsclient --eval "(progn                  \
        (find-file \"$(1)\")                            \
        (org-babel-goto-named-src-block \"$(2)\")       \
        (org-babel-execute-src-block)                   \
        (save-buffer))"
# Usage: $(call org-babel,<file.org>,<named_babel_block>)

SHELL = bash
.DEFAULT_GOAL := help
.PHONY: help
TANGLED := $(shell grep -Eo ":tangle.*" code.org | cut -d" " -f2 | grep -Ev 'identity|no')



PROMICE_MB: setup_init grass_hirham grass_mar grass_bmb SMB BMB dist
# dist

docker: Force
	docker pull hillerup/mass_balance

setup_init: FORCE
	mkdir -p tmp dat

grass_hirham: FORCE
        # set up
	${container_cmd} ${container_args} mass_balance:latest grass -e -c EPSG:4326 G_HIRHAM
	${container_cmd} ${container_args} mass_balance:latest grass ./G_HIRHAM/PERMANENT/ --exec ./HIRHAM.sh
	${container_cmd} ${container_args} mass_balance:latest grass -e -c XY G_HIRHAM_XY


grass_mar: FORCE
	${container_cmd} ${container_args} mass_balance:latest grass -e -c EPSG:3413 G_MAR
	${container_cmd} ${container_args} mass_balance:latest grass ./G_MAR/PERMANENT --exec ./MAR.sh
	${container_cmd} ${container_args} mass_balance:latest grass -e -c EPSG:3413 G_RACMO
	${container_cmd} ${container_args} mass_balance:latest grass ./G_RACMO/PERMANENT --exec ./RACMO.sh



grass_bmb: FORCE # BMB setup on the MAR grid
	${container_cmd} ${container_args} mass_balance:latest grass ./G_MAR/PERMANENT --exec ./BMB.sh

SMB: FORCE # partition RCM by Zwally sectors, Mouginot basins, and Mouginot regions
	${container_cmd} ${container_args} mass_balance:latest grass ./G_HIRHAM_XY/PERMANENT --exec ./SMB_HIRHAM_ROI.sh
	${container_cmd} ${container_args} mass_balance:latest grass ./G_MAR/PERMANENT --exec ./SMB_MAR_ROI.sh
	${container_cmd} ${container_args} mass_balance:latest grass ./G_RACMO/PERMANENT --exec ./SMB_RACMO_ROI.sh
	./SMB_merge.sh
	${container_cmd} ${container_args} mass_balance:latest python ./SMB_bsv2nc.py

BMB: FORCE
	${container_cmd} ${container_args} mass_balance:latest grass ./G_MAR/PERMANENT --exec ./BMB_MAR.sh
	./BMB_merge.sh
	${container_cmd} ${container_args} mass_balance:latest python ./BMB_bsv2nc.py

update: FORCE # remove previously forecasted MAR 
	for n in $$(seq -10 10); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/MAR/*_$${d}.bsv; done
	RECENT=true make SMB
	for n in $$(seq -10 10); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/BMB/*_$${d}.bsv; done
	RECENT=true make BMB
	make dist


validate: FORCE
	${container_cmd} ${container_args} mankoff/ice_discharge:grass grass -e -c EPSG:3413 G

dist: FORCE
	mkdir -p TMB
        # create end-user data product
	${container_cmd} ${container_args} mass_balance:latest python ./build_TMB_nc.py
        # python ./upload_to_DV.py
	${container_cmd} ${container_args} mass_balance:latest python ./twitfig.py
        # python ./twitbot.py


FORCE: # dummy target

clean_30:
        # Rebuild the last 30 days
	for n in $$(seq -10 30); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/MAR/*_$${d}.bsv; done
	for n in $$(seq -10 30); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/RACMO/*_$${d}.bsv; done
	for n in $$(seq -10 30); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/BMB/*_$${d}.bsv; done
	make update


clean_all:
	rm -fR G G_RACMO G_HIRHAM G_HIRHAM_XY G_MAR G_tmp tmp dat TMB

clean_SMB:
	rm -fR tmp/HIRHAM tmp/MAR tmp/RACMO




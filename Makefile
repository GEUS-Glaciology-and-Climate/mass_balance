container_cmd ?= docker
container_args ?= run --user $(shell id -u):$(shell id -g) \
	--env RECENT=${RECENT} \
	--env PARALLEL="--delay 0.1 -j -1" \
	--mount type=bind,src=${DATADIR},dst=/home/user/data \
	--mount type=bind,src="$(shell pwd)",dst=/home/user

RECENT ?= false

grass_hirham    = ${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_HIRHAM/PERMANENT    --exec
grass_hirham_xy = ${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_HIRHAM_XY/PERMANENT --exec
grass_mar       = ${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_MAR/PERMANENT       --exec
grass_racmo     = ${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_RACMO/PERMANENT     --exec
conda_run       = ${container_cmd} ${container_args} hillerup/tmb_conda python

SHELL  = bash
STAMPS = .stamps
.DEFAULT_GOAL := help
.PHONY: help all docker setup SMB BMB dist update clean_30 clean_SMB clean_all

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

all: docker setup SMB BMB dist ## Full pipeline from scratch

docker: ## Pull Docker images
	docker pull hillerup/tmb_grass:latest
	${container_cmd} ${container_args} hillerup/tmb_grass
	docker pull hillerup/tmb_conda:latest
	${container_cmd} ${container_args} hillerup/tmb_conda conda env export -n base


## --- One-time GRASS setup (stamp-based, re-runs only when script changes) ---

$(STAMPS):
	mkdir -p $(STAMPS)

G_HIRHAM:
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:4326 G_HIRHAM

G_HIRHAM_XY:
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c XY G_HIRHAM_XY

G_MAR:
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:3413 G_MAR

G_RACMO:
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:3413 G_RACMO

setup: ## Set up GRASS locations and import ROIs (one-time)
setup: $(STAMPS)/setup_hirham $(STAMPS)/setup_mar $(STAMPS)/setup_racmo $(STAMPS)/setup_bmb

$(STAMPS)/setup_hirham: scripts/setup_hirham.sh scripts/common.sh | G_HIRHAM G_HIRHAM_XY $(STAMPS)
	${grass_hirham} scripts/setup_hirham.sh
	touch $@

$(STAMPS)/setup_mar: scripts/setup_mar.sh scripts/common.sh | G_MAR $(STAMPS)
	${grass_mar} scripts/setup_mar.sh
	touch $@

$(STAMPS)/setup_racmo: scripts/setup_racmo.sh scripts/common.sh | G_RACMO $(STAMPS)
	${grass_racmo} scripts/setup_racmo.sh
	touch $@

$(STAMPS)/setup_bmb: scripts/setup_bmb.sh scripts/common.sh $(STAMPS)/setup_mar | $(STAMPS)
	${grass_mar} scripts/setup_bmb.sh
	touch $@


## --- SMB ---

SMB: ## Extract SMB from all RCMs, merge, and convert to NetCDF
	${grass_hirham_xy} scripts/smb_hirham.sh
	${grass_mar}       scripts/smb_mar.sh
	${grass_racmo}     scripts/smb_racmo.sh
	scripts/smb_merge.sh
	${conda_run} scripts/smb_bsv2nc.py


## --- BMB ---

BMB: ## Compute basal melt from MAR runoff, merge, and convert to NetCDF
	${grass_mar} scripts/bmb_mar.sh
	scripts/bmb_merge.sh
	${conda_run} scripts/bmb_bsv2nc.py


## --- Distribution ---

dist: ## Build TMB NetCDF and upload to THREDDS
	mkdir -p TMB
	${conda_run} scripts/build_tmb_nc.py
	/home/shl/miniconda3/envs/TMB/bin/python upload_cli.py \
		--url https://thredds01.geus.dk/thredds_upload \
		--destination tmb \
		--token $$(cat ~/.new_thredds_token) \
		--file TMB/*


## --- Operational update ---

update: ## Reprocess recent data (~30 days) and upload
	for n in $$(seq -10 10); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/MAR/*_$${d}.bsv; done
	RECENT=true make SMB
	for n in $$(seq -10 10); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/BMB/*_$${d}.bsv; done
	RECENT=true make BMB
	make dist


## --- Cleanup ---

clean_30: ## Rebuild the last 30 days of SMB and BMB
	for n in $$(seq -10 30); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/MAR/*_$${d}.bsv; done
	for n in $$(seq -10 30); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/RACMO/*_$${d}.bsv; done
	for n in $$(seq -10 30); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/BMB/*_$${d}.bsv; done
	make update

clean_SMB: ## Remove SMB intermediate files (forces re-extraction)
	rm -fR tmp/HIRHAM tmp/MAR tmp/RACMO

clean_all: ## Remove all generated files including GRASS databases and stamps
	rm -fR G_HIRHAM G_HIRHAM_XY G_MAR G_RACMO tmp dat TMB .stamps

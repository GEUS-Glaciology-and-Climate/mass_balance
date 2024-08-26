RECENT ?= false
container_cmd ?= docker
container_args ?= run --user $(shell id -u):$(shell id -g) --env RECENT=${RECENT} --mount type=bind,src=${DATADIR},dst=/home/user/data --mount type=bind,src="$(shell pwd)",dst=/home/user --env PARALLEL="--delay 0.1 -j -1"

org-babel = emacsclient --eval "(progn                  \
        (find-file \"$(1)\")                            \
        (org-babel-goto-named-src-block \"$(2)\")       \
        (org-babel-execute-src-block)                   \
        (save-buffer))"
# Usage: $(call org-babel,<file.org>,<named_babel_block>)


PROMICE_MB: all
# dist

docker: FORCE
	docker pull hillerup/tmb_grass:latest
	${container_cmd} ${container_args} hillerup/tmb_grass
	docker pull hillerup/tmb_conda:latest
	${container_cmd} ${container_args} hillerup/tmb_conda conda env export -n base

all: FORCE
	make docker
	mkdir -p tmp dat
	# set up
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:4326 G_HIRHAM
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_HIRHAM/PERMANENT/ --exec ./HIRHAM.sh
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c XY G_HIRHAM_XY
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:3413 G_MAR
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_MAR/PERMANENT --exec ./MAR.sh

	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:3413 G_RACMO
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_RACMO/PERMANENT --exec ./RACMO.sh

	# BMB setup on the MAR grid
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_MAR/PERMANENT --exec ./BMB.sh

	make SMB
	make BMB
	make dist

SMB: FORCE
	# partition RCM by Zwally sectors, Mouginot basins, and Mouginot regions
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_HIRHAM_XY/PERMANENT --exec ./SMB_HIRHAM_ROI.sh
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_MAR/PERMANENT --exec ./SMB_MAR_ROI.sh
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_RACMO/PERMANENT --exec ./SMB_RACMO_ROI.sh
	./SMB_merge.sh
	${container_cmd} ${container_args} hillerup/tmb_conda python ./SMB_bsv2nc.py

BMB: FORCE
	${container_cmd} ${container_args} hillerup/tmb_grass grass ./G_MAR/PERMANENT --exec ./BMB_MAR.sh
	./BMB_merge.sh
	${container_cmd} ${container_args} hillerup/tmb_conda python ./BMB_bsv2nc.py


test_tmp: FORCE
	./BMB_merge.sh
	${container_cmd} ${container_args} hillerup/tmb_conda python ./BMB_bsv2nc.py

update: FORCE
	# remove previously forecasted MAR 
	for n in $$(seq -10 10); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/MAR/*_$${d}.bsv; done
	RECENT=true make SMB
	for n in $$(seq -10 10); do d=$$(date --date="$${n} days ago" --iso-8601); rm -f ./tmp/BMB/*_$${d}.bsv; done
	RECENT=true make BMB
	make dist


validate: FORCE
	${container_cmd} ${container_args} hillerup/tmb_grass grass -e -c EPSG:3413 G

dist: FORCE
	mkdir -p TMB
	# create end-user data product
	${container_cmd} ${container_args} hillerup/tmb_conda python ./build_TMB_nc.py
	#cp ./TMB/* /mnt/thredds_fileshare/mass_balance/
	# python ./upload_to_DV.py
	#python ./twitfig.py
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


FROM ubuntu:20.04

LABEL authors="Signe Hillerup Larsen"
LABEL maintainer="shl@geus.dk"

# system environment
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y update && apt-get install -y --no-install-recommends --no-install-suggests \
      bash \
      cdo \
      datamash \
      gawk \
      gdal-bin \
      grass-gui \
      nco \
      netcdf-bin \
      parallel \
      proj-bin \
      sed \
      python-is-python3 \
      wget \
      git \
  && apt-get autoremove -y \
  && apt-get clean -y \ 
  && rm -rf /var/lib/apt/lists/*

RUN echo LANG="en_US.UTF-8" > /etc/default/locale

ENV LANGUAGE en_US.UTF-8
ENV LANG C
ENV LC_ALL C
ENV LC_CTYPE C

ENV SHELL /bin/bash

# create a user
RUN useradd --create-home user && chmod a+rwx /home/user
ENV HOME /home/user
WORKDIR /home/user

RUN mkdir -p /data
ENV DATADIR /data

# Install grass addons
RUN grass -e -c EPSG:3413 $HOME/G_tmp \ 
  g.extension r.stream.basins \ 
  url= https://trac.osgeo.org/grass/browser/grass-addons/grass7/raster/r.stream.basins \ 
  g.extension r.stream.distance \   
  url=https://trac.osgeo.org/grass/browser/grass-addons/grass7/raster/r.stream.distance

RUN rm -r $HOME/G_tmp 


ENV PATH=/home/user/.local/bin:$PATH

ENV CONDA_DIR /opt/conda

RUN wget --no-check-certificate\
    https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
    && rm -f Miniconda3-latest-Linux-x86_64.sh 

ENV PATH=$CONDA_DIR/bin:$PATH
RUN conda --version


RUN conda install -c conda-forge \
  xarray \
  pandas \
  matplotlib \ 
  jupyter \
  tabulate \
  pint \
  bottleneck \
  uncertainties \
  scipy \
  cfchecker \
  geopandas


# switch the user
USER user

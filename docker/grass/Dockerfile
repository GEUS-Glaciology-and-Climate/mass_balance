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
      grass-core \
      grass-dev \
      grass-gui \
      nco \
      netcdf-bin \
      parallel \
      proj-bin \
      sed \
      python3 \
      python3-pip \
      python3-distutils \
      build-essential \
      subversion \
      ca-certificates \
      git \
  && apt-get autoremove -y \
  && apt-get clean -y \ 
  && rm -rf /var/lib/apt/lists/*

# Set the default Python version
RUN ln -s /usr/bin/python3 /usr/bin/python

# Upgrade pip to ensure compatibility with the latest packages
RUN pip3 install --no-cache-dir --upgrade pip

# Install a compatible version of numpy, pandas, and xarray
RUN pip3 install --no-cache-dir numpy>=1.20 netcdf4 scipy h5netcdf pandas xarray

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
RUN mkdir -p /home/user/data && chown user:user /home/user/data
ENV DATADIR /home/user/data

# Clone grass-addons and list directory structure
RUN git clone https://github.com/OSGeo/grass-addons.git \
  && ls -R grass-addons \
  && cd grass-addons/src/raster/r.stream.basins || echo "Directory not found" \
  && grass --config path \
  && MODULE_TOPDIR=/usr/lib/grass78 \
  && make MODULE_TOPDIR=$MODULE_TOPDIR \
  && cd ../r.stream.distance \
  && make MODULE_TOPDIR=$MODULE_TOPDIR \
  && rm -rf /home/user/grass-addons

# switch the user
USER user

CMD ["/usr/bin/grass", "--version"]

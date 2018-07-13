Asterisk PBX Docker image
=========================

The smallest Docker image with Asterisk PBX https://hub.docker.com/r/andrius/asterisk/

This image is based on Alpine Linux image, which is only a 5MB image, and contains
[Asterisk PBX](http://www.asterisk.org/get-started/features).

Total size of this image is only:

[![](https://images.microbadger.com/badges/image/andrius/asterisk.svg)](https://microbadger.com/images/andrius/asterisk "Get your own image badge on microbadger.com")

# Versions

Based on Alpine linux:

- `docker pull andrius/asterisk:11.6.1` for Asterisk 11.x (stable release), on Alpine 2.6
- `docker pull andrius/asterisk:11` for Asterisk 11.x (stable release), on Alpine 2.7
- `docker pull andrius/asterisk:14` for Asterisk 14.x, on Alpine 3.6
- `docker pull andrius/asterisk:15.2.2` for Asterisk 15.2.2, on Alpine 3.7
- `docker pull andrius/asterisk:15` for Asterisk 15.x, on Alpine 3.8
- `docker pull andrius/asterisk:latest` for Asterisk 15.x, on Alpine latest
- `docker pull andrius/asterisk:edge` for latest Asterisk 15.x, based on Alpine edge

# What's missing

Only base Asterisk packages installed. If you want to add sounds, it's recommended to mount them as volume or data container, however you may install additional packages with `apk` command:

- asterisk-sounds-en
- asterisk-sounds-moh
- asterisk-alsa
- asterisk-srtp
- asterisk-curl
- asterisk-tds
- asterisk-mobile
- asterisk-dahdi
- asterisk-fax
- asterisk-speex
- asterisk-pgsql
- asterisk-odbc

# Custom UID/GID

By default, Asterisk will run as default user (asterisk) with UID and GID assigned by alpine linux, but it's possible to specify then through environment variables:

- `ASTERISK_UID`
- `ASTERISK_GID`

Default asterisk user will be re-created with new UID and GID

In given example, ID's of current host user will be used to start, that will fix permissions issues on logs volume:

```bash
docker run -ti --rm \
  -e ASTERISK_UID=`id -u` \
  -e ASTERISK_GID=`id -g` \
  -v ${PWD}/logs:/var/log/asterisk \
  andrius/asterisk
```

# Alternative user

It is possible to specifty other than asterisk user to start through environment variable `ASTERISK_USER`:

```bash
docker run -ti --rm -e ASTERISK_USER=root andrius/asterisk
```
# Database support

By default, Asterisk PBX store CDR's to the CSV file, but also support databases. Refer Asterisk PBX documentation for ODBC support.

For Postgre SQL include following lines to your Dockerfile:

```bash
RUN apk add --update less psqlodbc asterisk-odbc asterisk-pgsql \
&&  rm -rf /var/cache/apk/*
```

And For MySQL:

```bash
RUN apk add --update psqlodbc asterisk-odbc \
&&  apk add mysql-connector-odbc --update-cache --repository http://dl-4.alpinelinux.org/alpine/edge/testing/ --allow-untrusted \
&&  rm -rf /var/cache/apk/*
```



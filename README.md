Asterisk PBX 11.17.1 Docker image
=================================

The smallest Docker image with Asterisk PBX 11.17.1 (~17MB) https://hub.docker.com/r/andrius/alpine-asterisk/

This image is based on Alpine Linux (2.7) image, which is only a 5MB image, and contains
[Asterisk PBX 11.17.1](http://www.asterisk.org/get-started/features).

*[Due of bug](https://bugs.alpinelinux.org/issues/3503), this image based on latest Alpine Linux version (2.7), where everything works: SIP stack, calls, AGI, AMI. Author uing this image for ongoing VoIP systems development with Adhearsion.*

Total size of this image is only:

[![](https://badge.imagelayers.io/andrius/alpine-asterisk:latest.svg)](https://imagelayers.io/?images=andrius/alpine-asterisk:latest 'Get your own badge on imagelayers.io')

What's missing
---------------

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

Database support
----------------

By default, Asterisk PBX strre CDR's to the CSV file, but also support databases. Refer Asterisk PBX documentation for ODBC support. 

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


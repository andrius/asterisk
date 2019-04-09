#!/bin/sh

TAG=$1

cd ${TAG} && \
docker build --pull --force-rm -t andrius/asterisk:${TAG} --file ./Dockerfile . && \
docker run -d --rm --name asterisk-${TAG} andrius/asterisk:${TAG} && \
sleep 3 && \
docker exec -ti asterisk-${TAG} sh -c 'cat /etc/iss*' && \
docker exec -ti asterisk-${TAG} sh -c 'asterisk -rx "core show version"; exit $?' && echo "ok $?" || echo "not ok" ; \
docker stop asterisk-${TAG}; \
cd ..

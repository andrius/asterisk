#!/bin/sh

TAG=$1
docker pull andrius/asterisk:${TAG} && \
docker run -d --rm --name asterisk-${TAG} andrius/asterisk:${TAG} && \
sleep 2 && \
docker exec -ti asterisk-${TAG} sh -c "asterisk -rx 'core show version'"; \
docker stop asterisk-${TAG}; \
docker rmi andrius/asterisk:${TAG}

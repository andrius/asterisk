#!/bin/sh

# https://stackoverflow.com/questions/4000613/bash-for-each-directory
for DIR in *; do
  if [ -d "${DIR}" ]; then
    TAG=${DIR}
    cd ${TAG}

    docker build --pull --force-rm -t andrius/asterisk:${TAG} --file ./Dockerfile . && \
    docker run -d --rm --name asterisk-${TAG} andrius/asterisk:${TAG} && \
    sleep 5 && \
    docker exec -ti asterisk-${TAG} sh -c 'cat /etc/iss*' && \
    docker exec -ti asterisk-${TAG} sh -c 'asterisk -rx "core show version"; exit $?' && echo "ok $?" || echo "not ok" ; \
    docker stop asterisk-${TAG}; \
    docker push andrius/asterisk:${TAG}; \
    docker rmi -f andrius/asterisk:${TAG}

    cd ..
  fi
done


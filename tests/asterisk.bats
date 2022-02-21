#!/usr/bin/env bats

@test "asterisk is installed" {
  run docker run -ti --rm $IMAGE asterisk -V 2>&1 >&3

  EXPECTED_VERSION="$(echo "$VERSION" | awk -F '-' '{print $NF}')"
  CONTAINER_VERSION="$(echo "$output" | awk '{print $NF}')"

  echo "# docker image:     $IMAGE"             >&3
  echo "# expected version: $EXPECTED_VERSION"  >&3
  echo "# running version:  $CONTAINER_VERSION" >&3

  [ "$status" -eq 0 ]
}

# @test "asterisk runs ok" {
#   CONTAINER_NAME="$(date +%s | sha256sum | base64 | head -c 32 ; echo)"
#   docker run --rm --detach --name $CONTAINER_NAME $IMAGE
#   sleep 2s
#   run docker exec -ti $CONTAINER_NAME asterisk -V 2>&1 >&3
#   docker stop $CONTAINER_NAME

#   EXPECTED_VERSION="$(echo "$VERSION" | awk -F '-' '{print $NF}')"
#   CONTAINER_VERSION="$(echo "$output" | awk '{print $NF}')"

#   echo "# docker image:     $IMAGE"             >&3
#   echo "# expected version: $EXPECTED_VERSION"  >&3
#   echo "# running version:  $CONTAINER_VERSION" >&3

#   [ "$status" -eq 0 ]
#   if [[ "$EXPECTED_VERSION" != "edge" && "$EXPECTED_VERSION" != "latest" && ! "$EXPECTED_VERSION" =~ glibc ]]; then
#     [[ "$VERSION" =~ "${output}" ]]
#   fi
# }

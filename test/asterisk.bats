#!/usr/bin/env bats

@test "asterisk is installed" {
  run docker run -ti --rm $IMAGE asterisk -V
  [ "$status" -eq 0 ]
}

@test "asterisk runs ok" {
  run docker run -ti --rm $IMAGE sh -c 'asterisk; sleep 5; asterisk -rx "core show version"'
  [ "$status" -eq 0 ]
}

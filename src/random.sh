#!/bin/bash

SIZE=1024

if [[ $# -gt 0 ]]
then
    SIZE=$1
fi

# make space for the new line char
((SIZE_MINUS=SIZE-1))

dd if=/dev/urandom  | tr -dc 'a-zA-Z0-9' | head -c $SIZE_MINUS ; echo

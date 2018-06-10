#!/bin/bash

PATH_PREFIX="../dir"
PING_NAME="ping"

DIR=3
LEN=3

SIZE_MIN=1924           # 1 KB
SIZE_MAX=131072         # 64 KB
SIZE_GIGANTIC=10485760  # 10 MB

CB_PORT=9010
CB_RES_BODY="I know that the TARBALL has been created."

# set working dir
DIR_RUN="$(cd "$(dirname "$0")" && pwd)"
cd $DIR_RUN

# see 'man shuf'
# range [min-max]

k=0

for ((i=1; i<=$DIR; i++))
do
    mkdir -p "${PATH_PREFIX}-${i}"

    for ((j=1; j<=$LEN; j++))
    do
        ((k++))
        SIZE=$(shuf -i $SIZE_MIN-$SIZE_MAX -n 1)
        ./random.sh $SIZE > "${PATH_PREFIX}-${i}/db-log-${k}.txt"
    done
done

# gigantic file into first directory only
./random.sh $SIZE_GIGANTIC > "${PATH_PREFIX}-1/db-dump.sql"

# callback HTTP server
mkdir -p "${PATH_PREFIX}-${PING_NAME}"
cd "${PATH_PREFIX}-${PING_NAME}"
echo "${CB_RES_BODY}" > "${PING_NAME}"
python -m SimpleHTTPServer $CB_PORT

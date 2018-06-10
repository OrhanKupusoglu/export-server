#!/bin/bash

echo "stopping"

wget -qO- http://localhost:9006/stop

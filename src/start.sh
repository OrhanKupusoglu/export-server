#!/bin/bash

echo "starting"

nohup python export_server.py > /dev/null 2>&1 &

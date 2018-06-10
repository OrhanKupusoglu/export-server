#!/bin/sh

pid=$(ps aux | grep "python export_server.py" | grep -v "grep"  | awk '{print $2}')

if [ ! -z ${pid} ]; then
    echo "killing"
    kill -9 ${pid}
else
    echo "unknwon pid"
fi

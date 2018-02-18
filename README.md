In the Python world, to publish a directory's listing over the HTTP interface one does even not need a program.

Here the contents of the working directory is listed on port 9008, the default port is 8000.

```
$ python -m SimpleHTTPServer 9008
Serving HTTP on 0.0.0.0 port 9008 ...
```

In Python 3 the module's are renamed.

```
$ python3 -m http.server 9008
Serving HTTP on 0.0.0.0 port 9008 ...
```
But if machine-to-machine communication is intended an **API** is required.

This simple Python 2 class is designed to use *only native modules* with no other dependencies. It is tested with **Python 2.4.3** dating from Sep 29 2010.

### Directories

The **EXPORT_DIRS** list contains directory names. A missing directory raises a fatal error.

### Start

The application can be started like any Python application. In this case the console prints some logs.

A rotating logger is used, **server.log** contains the current logs. Numbered log files are ordered from newest to oldest.

See the **start script** [start.sh](./start.sh) for [nohup](https://en.wikipedia.org/wiki/Nohup) starting which allows closing the terminal. Default port is **9006** which can be overwritten by supplying an argument.

```
$ python export_server.py 9008

================================================================================
2018-02-11 23:41:08
Export server started on port: 9008
```

### Directory Listing: /list

The directory listing for a given directory listed with the path **/list**. The directory name is mandatory. The prefix and suffix query parameters give fine control over the listing.

```
$ wget -qO- "http://localhost:9006/list?dir=dir_1&prefix=db-log&suffix=txt"
[{"name":"db-log-01.txt","size":489254},{"name":"db-log-03.txt","size":2269},{"name":"db-log-02.txt","size":503}]

```

### Get Ordinary File: /get

A relatively small file can be requested with **/get** right away. In-Memory compression is optional, **zip** and **gz** are supported.

```
$ wget -O db-log-01.zip "http://localhost:9006/get?dir=dir_1&name=db-log-01.txt&compress=zip"
--2018-02-18 12:17:00--  http://localhost:9006/get?dir=dir_1&name=db-log-01.txt&compress=zip
Resolving localhost... 127.0.0.1
Connecting to localhost|127.0.0.1|:9006... connected.
HTTP request sent, awaiting response... 200 OK
Length: 44380 (43K) [application/zip]
Saving to: `db-log-01.zip'

100%[=====================================================================================>] 44,380      --.-K/s   in 0s

2018-02-18 11:17:00 (559 GB/s) - `db-log-01.zip' saved [44380/44380]

```

### Compress Gigantic File: /tar

A gigantic file, for example a large DB dump text file, is preferably compressed but this may cause HTTP timeouts. With the supplied callback parameters, **host-port-path**, an HTTP 200 response is sent immediately.

```
$ wget -qO- "http://localhost:9006/list?dir=dir_1&suffix=sql"
[{"name":"db-dump.sql","size":713332332}]

$ $ wget -O db-dump.tgz "http://localhost:9006/tar?dir=dir_1&name=db-dump.sql"
--2018-02-18 11:21:47--  http://localhost:9006/tar?dir=dir_1&name=db-dump.sql
Resolving localhost... 127.0.0.1
Connecting to localhost|127.0.0.1|:9006... connected.
HTTP request sent, awaiting response... 400 ERROR - CALLBACK PARAMETERS ARE MISSING: /tar?dir=dir_1&name=db-dump.sql
2018-02-18 11:21:47 ERROR 400: ERROR - CALLBACK PARAMETERS ARE MISSING: /tar?dir=dir_1&name=db-dump.sql.

# remove the falsely created output file
$ rm db-dump.tgz

```

Once the compressed file is ready, an HTTP callback request will be sent to ping the user.

Parameters, like **?id=A1B2C3**, are optional.

```
$ wget -qO- "http://localhost:9006/tar?dir=dir_1&name=db-dump.sql&host=localhost&port=9010&path=/ping?id=A1B2C3"
working ...

```

The ping-back has a response body: *I know that the TARBALL has been created.*

```
2018-02-18 11:21:47,510 - DEBUG - 127.0.0.1:32786 - Thread-1 - "GET /tar?dir=dir_1&name=db-dump.sql HTTP/1.0" 400 -
2018-02-18 11:21:53,628 - DEBUG - 127.0.0.1:32788 - Thread-2 - "GET /tar?dir=dir_1&name=db-dump.sql&host=localhost&port=9010&path=/ping?id=A1B2C3 HTTP/1.0" 200 -
2018-02-18 11:21:56,563 - DEBUG - 127.0.0.1:32788 - Thread-2 - CALLBACK: 200 - OK: I know that the TARBALL has been created.

```

The user then may ask for a directory listing and can download the file without any further compression.

```
$ wget -qO- "http://localhost:9006/list?dir=dir_1&prefix=db-dump&suffix=tgz"
[{"name":"db-dump.tgz","size":63689766}]

$ wget -O db-dump.tgz "http://localhost:9006/get?dir=dir_1&name=db-dump.tgz"
--2018-02-18 11:23:50--  http://localhost:9006/get?dir=dir_1&name=db-dump.tgz
Resolving localhost... 127.0.0.1
Connecting to localhost|127.0.0.1|:9006... connected.
HTTP request sent, awaiting response... 200 OK
Length: 14852617 (14M) [text/plain]
Saving to: `db-dump.tgz'

100%[=====================================================================================>] 14,852,617  --.-K/s   in 0.08s

2018-02-18 11:23:50 (185 MB/s) - `db-dump.tgz' saved [14852617/14852617]

```

### Delete Files: /delete

Files can be deleted either with **name** or **prefix** or **suffix**. With **prefix=*** and **suffix=*** all files within the directory will be deleted.

```
$ wget -qO- "http://localhost:9006/delete?dir=dir_1&prefix=db-log&suffix=txt"
deleted 3 files
$ wget -qO- "http://localhost:9006/list?dir=dir_1&prefix=db-log&suffix=txt"
[]
```

### Stop

The application can be stopped from **localhost only** with a simple HTTP stop request. If the application is started simply with the python command then **SIGINT** signal, **CTRL + C**, will close it.

See the **stop script** [stop.sh](./stop.sh).

If the Python version is lower than 2.5 then exiting a multi-thread application gracefully is problematic. In this case a shell script is called to kill the application.

See the **kill script** [kill.sh](./kill.sh).

```
$ wget -qO- http://localhost:9006/stop
```

### favicon.ico

A [favicon icon](https://en.wikipedia.org/wiki/Favicon.ico) is borrowed from [Icon Finder](https://www.iconfinder.com/icons/299060/folder_icon#size=128) with license [Creative Commons (Attribution 3.0 Unported)](http://creativecommons.org/licenses/by/3.0/). It is included to prevent annoying HTTP 404 responses sent to Internet browsers.

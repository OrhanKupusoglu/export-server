# Python 2.4 REST API

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

This simple Python 2 class is designed to use *only native modules* with no other dependencies. It is tested with **Python 2.4.3** dating from September 29, 2010.

### Directories

The array **EXPORT_DIRS** in the Python source file lists directory names. A missing directory raises a fatal error. For the gigantic file case a callback HTTP server is required.

For convenience a **shell script** [generate.sh](./src/generate.sh) is provided to generate directories and the callback HTTP server. 

```
$ cd src/
$ ./generate.sh 
Serving HTTP on 0.0.0.0 port 9010 ...
```

### Start

The application can be started like any Python application. In this case the console prints some logs.

A rotating logger is used, **server.log** contains the current logs. Numbered log files are ordered from newest to oldest.

See the **start script** [start.sh](./src/start.sh) for [nohup](https://en.wikipedia.org/wiki/Nohup) starting which allows closing the terminal. Default port is **9006** which can be overwritten by supplying an argument.

```
$ cd src
$ python export_server.py 9006

--------------------------------------------------------------------------------
2018-06-10 23:09:24,027 - DEBUG - MainThread - started @ port 9006
^C
2018-06-10 23:09:47,055 - DEBUG - MainThread - stopped

$ ./start.sh
starting
```

### Directory Listing: /list

The directory listing for a given directory listed with the path **/list**. The directory name is mandatory. The prefix and suffix query parameters give fine control over the listing.

```
$ wget -qO- "http://localhost:9006/list?dir=../dir-1&prefix=db-log&suffix=txt"
[{"name":"db-log-3.txt","size":29370},{"name":"db-log-2.txt","size":18616},{"name":"db-log-1.txt","size":27391}]

```

### Get Ordinary File: /get

A relatively small file can be requested with **/get** right away. In-Memory compression is optional, **zip** and **gz** are supported.

```
$ wget -O db-log-01.zip "http://localhost:9006/get?dir=../dir-1&name=db-log-1.txt&compress=zip"
--2018-06-10 23:14:44--  http://localhost:9006/get?dir=../dir-1&name=db-log-1.txt&compress=zip
Resolving localhost (localhost)... 127.0.0.1
Connecting to localhost (localhost)|127.0.0.1|:9006... connected.
HTTP request sent, awaiting response... 200 OK
Length: 20717 (20K) [application/zip]
Saving to: ‘db-log-01.zip’

db-log-01.zip                                               100%[=========================================================================================================================================>]  20,23K  --.-KB/s    in 0s      

2018-06-10 23:14:44 (198 MB/s) - ‘db-log-01.zip’ saved [20717/20717]
```

### Compress Gigantic File: /tar

A gigantic file, for example a large DB dump text file, is preferably compressed but this may cause HTTP timeouts. With the supplied callback parameters, **host-port-path**, an HTTP 200 response is sent immediately. Missing callback parameters cause an **HTTP 400-Bad Request** error.

```
$ wget -qO- "http://localhost:9006/list?dir=../dir-1&suffix=sql"
[{"name":"db-dump.sql","size":10485760}]

$ wget -O db-dump.tgz "http://localhost:9006/tar?dir=../dir-1&name=db-dump.sql"
--2018-06-10 23:39:10--  http://localhost:9006/tar?dir=../dir-1&name=db-dump.sql
Resolving localhost (localhost)... 127.0.0.1
Connecting to localhost (localhost)|127.0.0.1|:9006... connected.
HTTP request sent, awaiting response... 400 ERROR - CALLBACK PARAMETERS ARE MISSING: /tar?dir=../dir-1&name=db-dump.sql
2018-06-10 23:39:10 ERROR 400: ERROR - CALLBACK PARAMETERS ARE MISSING: /tar?dir=../dir-1&name=db-dump.sql.

# remove the falsely created output file
$ rm db-dump.tgz
```

Once the compressed file is ready, an HTTP callback request will be sent to ping the client. Parameters, like **?id=A1B2C3**, are optional, and can be used to identify the request.

```
$ wget -qO- "http://localhost:9006/tar?dir=../dir-1&name=db-dump.sql&host=localhost&port=9010&path=/ping?id=A1B2C3"
working ...
```

Check the server log file **src/server.log** to see that the ping-back has a response body: *I know that the TARBALL has been created.*

```
2018-06-10 23:58:17,634 - DEBUG - 127.0.0.1:45428 - Thread-5 - "GET /list?dir=../dir-1&suffix=sql HTTP/1.1" 200 -
2018-06-10 23:58:30,739 - DEBUG - 127.0.0.1:45430 - Thread-6 - code 400, message ERROR - CALLBACK PARAMETERS ARE MISSING: /tar?dir=../dir-1&name=db-dump.sql
2018-06-10 23:58:30,740 - DEBUG - 127.0.0.1:45430 - Thread-6 - "GET /tar?dir=../dir-1&name=db-dump.sql HTTP/1.1" 400 -
2018-06-10 23:59:34,418 - DEBUG - 127.0.0.1:45432 - Thread-7 - "GET /tar?dir=../dir-1&name=db-dump.sql&host=localhost&port=9010&path=/ping?id=A1B2C3 HTTP/1.1" 200 -
2018-06-10 23:59:34,876 - DEBUG - 127.0.0.1:45432 - Thread-7 - CALLBACK: 200 - OK: I know that the TARBALL has been created.
```

The client then may ask for a directory listing and can download the file without any further compression.

```
$ wget -qO- "http://localhost:9006/list?dir=../dir-1&prefix=db-dump&suffix=tgz"
[{"name":"db-dump.tgz","size":7878153}]

$ wget -O db-dump.tgz "http://localhost:9006/get?dir=../dir-1&name=db-dump.tgz"
--2018-06-11 00:00:26--  http://localhost:9006/get?dir=../dir-1&name=db-dump.tgz
Resolving localhost (localhost)... 127.0.0.1
Connecting to localhost (localhost)|127.0.0.1|:9006... connected.
HTTP request sent, awaiting response... 200 OK
Length: 7878153 (7,5M) [text/plain]
Saving to: ‘db-dump.tgz’

db-dump.tgz                                                 100%[=========================================================================================================================================>]   7,51M  --.-KB/s    in 0,01s   

2018-06-11 00:00:26 (524 MB/s) - ‘db-dump.tgz’ saved [7878153/7878153]
```

### Delete Files: /delete

Files can be deleted either with **name** or **prefix** or **suffix**. With **prefix=*** and **suffix=*** all files within the directory will be deleted.

```
$ wget -qO- "http://localhost:9006/delete?dir=../dir-1&prefix=db-log&suffix=txt"
deleted 3 files
$ wget -qO- "http://localhost:9006/list?dir=../dir-1&prefix=db-log&suffix=txt"
[]
```

### Stop

The application can be stopped from **localhost only** with a simple HTTP stop request. If the application is started simply with the python command then **SIGINT** signal, **CTRL + C**, will close it.

See the **stop script** [stop.sh](./src/stop.sh).

```
$ ./stop.sh 
stopping
stopped
```

If the Python version is lower than 2.5 then exiting a multi-thread application gracefully is problematic. In this case a shell script is called to kill the application.

See the **kill script** [kill.sh](./src/kill.sh).

```
$ ./kill.sh 
killing
```

### favicon.ico

A [favicon icon](https://en.wikipedia.org/wiki/Favicon.ico) is borrowed from [Icon Finder](https://www.iconfinder.com/icons/299060/folder_icon#size=128) with license [Creative Commons (Attribution 3.0 Unported)](http://creativecommons.org/licenses/by/3.0/). It is included to prevent annoying HTTP 404 responses sent to Internet browsers.

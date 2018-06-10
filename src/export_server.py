#!/usr/bin/python

import BaseHTTPServer
import os
import urlparse
import cgi
import sys
import errno
import gzip
import zipfile
import cStringIO
import datetime
import subprocess
import httplib
import SocketServer
import thread
import threading
import logging
import logging.handlers
import signal

# ------------------------------------------------------------------------------
EXPORT_DIRS = ['../dir-1',
               '../dir-2',
               '../dir-3']

PORT_NUMBER = 9006
# ------------------------------------------------------------------------------

EXPORT_DIR_ABS = os.getcwd()
LOG_DATA = {'file_name': EXPORT_DIR_ABS + os.sep + 'server.log',
            'max_bytes': 1024 * 1024,
            'backup_count': 10}
HTTP_CB_TIMEOUT = 10
LOCAL_HOST = '127.0.0.1'
SEP_LINE = 80 * '-'

_port_num = 0

# the optional first argument determines the port number of the HTTP server
if len(sys.argv) == 1:
    _port_num = PORT_NUMBER
else:
    try:
        _port_num = int(sys.argv[1])
    except ValueError:
        _port_num = PORT_NUMBER

# set logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console = logging.StreamHandler()
console.setLevel(logging.DEBUG)

handler = logging.handlers.RotatingFileHandler(filename=LOG_DATA['file_name'],
                                               maxBytes=LOG_DATA['max_bytes'],
                                               backupCount=LOG_DATA['backup_count'])
handler.setLevel(logging.DEBUG)

logger.addHandler(handler)
logger.addHandler(console)

formatter = logging.Formatter('%(message)s')
console.setFormatter(formatter)
handler.setFormatter(formatter)

logger.debug('\n%s', SEP_LINE)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console.setFormatter(formatter)
handler.setFormatter(formatter)

logger.debug('%s - started @ port %s', threading.currentThread().getName(), _port_num)

# helper functions
def does_dir_exist(exp_dir):
    path_abs = EXPORT_DIR_ABS + os.sep + exp_dir
    return os.path.exists(path_abs) and os.path.isdir(path_abs)

def does_file_exist(curr_dir, file_name):
    if curr_dir:
        path_abs = EXPORT_DIR_ABS + os.sep + curr_dir + os.sep + file_name
    else:
        path_abs = file_name
    return os.path.exists(path_abs) and os.path.isfile(path_abs)

def load_binary(file_path):
    if does_file_exist('', file_path):
        f = None
        d = None

        try:
            try:
                f = open(file_path, 'r')
                d = f.read()
            finally:
                if f is not None:
                    f.close()
        except:
            logger.error('BINARY FILE OPEN ERROR: %s', file_path)

        return d
    else:
        return None

class ThreadedHTTPServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass

class ThreadedRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    # class variables
    does_favicon_exist = does_file_exist('.', 'favicon.ico')
    favicon_data = load_binary('favicon.ico')

    def log_message(self, format, *args):
        #pass
        logger.debug('%s:%d - %s - %s', self.client_address[0], self.client_address[1],
                     threading.currentThread().getName(), format%args)

    def get_size(self, fileobj):
        if hasattr(os, 'SEEK_END'):
           SEEK_END = os.SEEK_END
        else:
            SEEK_END = 2
        if hasattr(os, 'SEEK_SET'):
            SEEK_SET = os.SEEK_SET
        else:
            SEEK_SET = 0
        fileobj.seek(0, SEEK_END)
        filesize = fileobj.tell()
        fileobj.seek(0, SEEK_SET)
        return filesize

    def gz_content(self, name, content):
        fgz = cStringIO.StringIO()
        gzip_obj = gzip.GzipFile(filename=name, mode='wb', fileobj=fgz)
        gzip_obj.write(content)
        gzip_obj.close()
        return fgz

    def zip_content(self, name, content):
        fzip = cStringIO.StringIO()
        zip_obj = zipfile.ZipFile(file=fzip, mode='w', compression=zipfile.ZIP_DEFLATED)
        zip_obj.writestr(name, content)
        zip_obj.close()
        return fzip

    def call_shell(self, args):
        try:
            return subprocess.call(args, stderr=subprocess.STDOUT, shell=True)
        except OSError, e:
            logger.error('SHELL ERROR: {0} - {1}'.format(e.errno, e.strerror))
            return e.errno

    def http_get(self, cb_url):
        try:
            if sys.version_info < (2,6):
                conn = httplib.HTTPConnection(host=cb_url['host'], port=cb_url['port'])
            else:
                conn = httplib.HTTPConnection(host=cb_url['host'], port=cb_url['port'], timeout=cb_url['timeout'])
            if '?' in cb_url['path']:
                sep = '&'
            else:
                sep = '?'
            conn.request('GET', cb_url['path'] + sep + cb_url['query'] + '&tar=' + cb_url['tar'])
            res = conn.getresponse()
            data = res.read()
            conn.close()
            self.log_message('CALLBACK: %d - %s: %s', res.status, res.reason, data)
            return res.status
        except Exception, e:
            logger.error(str(e))
            logger.error('CALLBACK FAILURE: %s:%s%s', cb_url['host'], cb_url['port'], cb_url['path'])

    def do_GET(self):
        url = urlparse.urlsplit(self.path)
        query = dict(cgi.parse_qsl(url[3]))

        index_query = self.path.find('?')
        if index_query == -1:
            curr_path = self.path
        else:
            curr_path = self.path[:index_query]

        # non-command line HTTP clients, i.e. Internet browsers, may request a favorite icon
        if curr_path == '/favicon.ico':
            if ThreadedRequestHandler.does_favicon_exist:
                self.send_response(200)
                self.send_header('Content-Type', 'image/x-icon')
                self.end_headers()
                self.wfile.write(ThreadedRequestHandler.favicon_data)
                self.wfile.close()
            else:
                self.send_error(404, 'ERROR - ICON NOT FOUND: %s' % self.path)

        # stop the server, if only called from localhost
        elif curr_path == '/stop':
            if self.client_address[0] == LOCAL_HOST:
                body = 'stopped\n'

                self.send_response(200)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                self.wfile.close()

                if sys.version_info < (2,5):
                    self.call_shell('./kill.sh')
                else:
                    thread.interrupt_main()
            else:
                self.send_error(403, 'FORBIDDEN: not localhost')

        # get the directory listing as JSON {name, size}
        elif curr_path == '/list':
            file_dir = query.get('dir')
            file_prefix = query.get('prefix')
            file_suffix = query.get('suffix')

            check = False

            if not file_dir:
                self.send_error(400, 'ERROR - DIRECTORY NAME IS MISSING: %s' % self.path)
            elif not does_dir_exist(file_dir):
                self.send_error(400, 'ERROR - DIRECTORY DOES NOT EXIST: %s' % self.path)
            else:
                # De Morgan's Laws
                # https://en.wikipedia.org/wiki/De_Morgan%27s_laws
                #if not file_prefix and not file_suffix:
                if not (file_prefix or file_suffix):
                    check = False
                else:
                    if not file_prefix:
                        file_prefix = ''
                    if not file_suffix:
                        file_suffix = ''
                    check = True

                file_info = []

                curr_dir = EXPORT_DIR_ABS + os.sep + file_dir

                for file_name in os.listdir(curr_dir):
                    add = False

                    if os.path.isfile(curr_dir + os.sep + file_name):
                        if check:
                            add = (file_name.startswith(file_prefix) and file_name.endswith(file_suffix))
                        else:
                            add = True

                    if add:
                        file_info.append('{"name":"' + file_name
                                         + '","size":' + str(os.path.getsize(curr_dir + os.sep + file_name)) + '}')

                if len(file_info) > 0:
                    list_json = '['
                    list_json += ','.join(file_info)
                    list_json += ']'
                else:
                    list_json = '[]'
                list_json += '\n'

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(list_json)
                self.wfile.close()

        # get the file, optionally as compressed
        elif curr_path == '/get':
            file_dir = query.get('dir')
            file_name = query.get('name')
            comp_ext = query.get('compress')

            compress = False

            if comp_ext:
                if comp_ext in ['zip', 'gz']:
                    compress = True

            if not file_dir:
                self.send_error(400, 'ERROR - DIRECTORY NAME IS MISSING: %s' % self.path)
            elif not does_dir_exist(file_dir):
                self.send_error(400, 'ERROR - DIRECTORY DOES NOT EXIST: %s' % self.path)
            elif not file_name:
                self.send_error(400, 'ERROR - FILE NAME IS MISSING: %s' % self.path)
            elif not does_file_exist(file_dir, file_name):
                self.send_error(400, 'ERROR - FILE DOES NOT EXIST: %s' % self.path)
            else:
                curr_dir = EXPORT_DIR_ABS + os.sep + file_dir

                try:
                    sendReply = False

                    if file_name.endswith(".html"):
                        mime_type='text/html'
                        sendReply = True
                    elif file_name.endswith(".csv"):
                        mime_type='text/csv'
                        sendReply = True
                    elif file_name.endswith(".gz"):
                        mime_type = 'application/gzip'
                        sendReply = True
                    elif file_name.endswith(".zip"):
                        mime_type = 'application/zip'
                        sendReply = True
                    else:
                        mime_type = 'text/plain'
                        sendReply = True

                    if sendReply:
                        f = open(curr_dir + os.sep + file_name, 'rb')

                        if compress:
                            ok = True
                            base_name = os.path.splitext(os.path.basename(file_name))[0]
                            file_content = f.read()
                            file_size = 0
                            file_comp = ''
                            mime_type = ''
                            content = ''

                            if comp_ext == 'gz':
                                gz_file = self.gz_content(file_name, file_content)
                                gz_size = self.get_size(gz_file)
                                content = gz_file.getvalue()
                                gz_file.close()

                                file_comp = base_name + '.gz'
                                file_size = gz_size
                                mime_type = 'application/gzip'
                            elif comp_ext == 'zip':
                                zip_file = self.zip_content(file_name, file_content)
                                zip_size = self.get_size(zip_file)
                                content = zip_file.getvalue()
                                zip_file.close()

                                file_comp = base_name + '.zip'
                                file_size = zip_size
                                mime_type = 'application/zip'
                            else:
                                ok = False

                            if ok:
                                self.send_response(200)
                                self.send_header('Content-Type', mime_type)
                                self.send_header('Content-Length', file_size)
                                self.send_header('Content-Disposition', 'attachment; filename=' + file_comp)
                                self.end_headers()
                                self.wfile.write(content)
                                self.wfile.close()
                            else:
                                self.send_error(400, 'ERROR - UNKNOWN COMPRESSION FORMAT: %s' % self.path)

                        else:
                            self.send_response(200)
                            self.send_header('Content-Type', mime_type)
                            self.send_header('Content-Length', str(os.path.getsize(curr_dir + os.sep + file_name)))
                            self.send_header('Content-Disposition', 'attachment; filename=' + file_name)
                            self.end_headers()

                            while True:
                                data = f.read(4096)
                                self.wfile.write(data)
                                if not data:
                                    break

                            self.wfile.write('\n')
                            self.wfile.close()

                        f.close()

                    else:
                        self.send_error(400, 'ERROR - BAD FILE REQUEST: %s' % self.path)

                    return

                except IOError:
                    self.send_error(404, 'ERROR - FILE NOT FOUND: %s' % self.path)

        # create a tarball which may take ages and then call back to inform the client
        elif curr_path == '/tar':
            file_dir = query.get('dir')
            file_name = query.get('name')

            if not file_dir:
                self.send_error(400, 'ERROR - DIRECTORY NAME IS MISSING: %s' % self.path)
            elif not does_dir_exist(file_dir):
                self.send_error(400, 'ERROR - DIRECTORY DOES NOT EXIST: %s' % self.path)
            elif not file_name:
                self.send_error(400, 'ERROR - FILE NAME IS MISSING: %s' % self.path)
            elif not does_file_exist(file_dir, file_name):
                self.send_error(400, 'ERROR - FILE DOES NOT EXIST: %s' % self.path)
            else:
                cb_host = query.get('host')
                cb_port = query.get('port')
                cb_path = query.get('path')

                if cb_host and cb_port and cb_path:
                    body = 'working ...\n'

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    self.wfile.close()

                    base_name = os.path.splitext(os.path.basename(file_name))[0]
                    curr_dir = file_dir
                    tgz_file = base_name + '.tgz'
                    file_comp = tgz_file

                    cb_url = {'host': cb_host,
                              'port': cb_port,
                              'path': cb_path,
                              'timeout': HTTP_CB_TIMEOUT,
                              'tar': tgz_file}

                    if does_file_exist(file_dir, file_comp):
                        logger.info('file already exists: %s' % file_dir + os.sep + file_comp)
                        ret = 0
                    else:
                        args = 'cd ' + curr_dir + '; tar -czf ' + file_comp + ' ' + file_name
                        ret = self.call_shell(args)

                    if ret == 0:
                        cb_url['query'] = 'success=true'
                    else:
                        cb_url['query'] = 'success=false'

                    self.http_get(cb_url)
                else:
                    self.send_error(400, 'ERROR - CALLBACK PARAMETERS ARE MISSING: %s' % self.path)

        # delete file in a given directory
        elif curr_path == '/delete':
            file_dir = query.get('dir')
            file_name = query.get('name')
            file_prefix = query.get('prefix')
            file_suffix = query.get('suffix')

            if not file_dir:
                self.send_error(400, 'ERROR - DIRECTORY NAME IS MISSING: %s' % self.path)
            elif not does_dir_exist(file_dir):
                self.send_error(400, 'ERROR - DIRECTORY DOES NOT EXIST: %s' % self.path)
            else:
                curr_dir = EXPORT_DIR_ABS + os.sep + file_dir

                if file_name:
                    if does_file_exist('', curr_dir + os.sep + file_name):
                        os.remove(curr_dir + os.sep + file_name)

                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write('deleted: ' + curr_dir + os.sep + file_name)
                        self.wfile.close()
                    else:
                        self.send_error(400, 'ERROR - FILE DOES NOT EXIST: %s' % curr_dir + os.sep + file_name)
                else:
                    if not (file_prefix or file_suffix):
                        self.send_error(400, 'ERROR - DELETE PARAMETERS ARE MISSING: %s' % self.path)
                    else:
                        del_file = 0

                        if not file_prefix:
                            file_prefix = '*'
                        if not file_suffix:
                            file_suffix = '*'

                        for file_name in os.listdir(curr_dir):
                            if file_prefix == '*' and not file_suffix == '*':
                                if file_name.endswith(file_suffix):
                                    del_file += 1
                                    os.remove(curr_dir + os.sep + file_name)
                            elif file_suffix == '*' and not file_prefix == '*':
                                if file_name.startswith(file_prefix):
                                    del_file += 1
                                    os.remove(curr_dir + os.sep + file_name)
                            elif file_suffix == '*' and file_prefix == '*':
                                del_file += 1
                                os.remove(curr_dir + os.sep + file_name)
                            else:
                                if file_name.startswith(file_prefix) and file_name.endswith(file_suffix):
                                    del_file += 1
                                    os.remove(curr_dir + os.sep + file_name)

                        self.send_response(200)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()

                        if del_file > 0:
                            self.wfile.write('deleted ' + str(del_file) + ' files\n')
                        else:
                            self.wfile.write('no file is deleted\n')
                        self.wfile.close()
        else:
            self.send_error(400, 'ERROR - BAD RESOURCE REQUEST: %s' % self.path)

try:
    # check the directories first
    for exp_dir in EXPORT_DIRS:
        if not does_dir_exist(exp_dir):
            print 'FATAL: directory "' + exp_dir + '" does not exist'
            sys.exit(1)

    server = ThreadedHTTPServer(('', _port_num), ThreadedRequestHandler)
    server.serve_forever()

except KeyboardInterrupt:
    print
    logger.debug('%s - stopped', threading.currentThread().getName())
    server.socket.close()
    sys.exit(0)

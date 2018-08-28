from waitress import serve
from config import wsgi

open('/tmp/app-initialized', 'w').close()
serve(wsgi.application, unix_socket='/tmp/nginx.socket')

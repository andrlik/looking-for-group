from waitress import serve
from config import wsgi

open("/opt/python/log/app-initialized", "w").close()


serve(wsgi.application, unix_socket="/opt/python/log/nginx.socket")

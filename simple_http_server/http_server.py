# -*- coding: utf-8 -*-


import http
import socket
import socketserver
"""
Copyright (c) 2018 Keijack Wu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


import os
import re
import ssl as _ssl
import threading

from collections import OrderedDict
from socketserver import ThreadingMixIn
from urllib.parse import unquote
from urllib.parse import quote

from typing import Callable, Dict, List, Tuple

from simple_http_server import ControllerFunction, StaticFile

from .base_http_request_handler import BaseHTTPRequestHandler
from .__utils import remove_url_first_slash
from .logger import get_logger

_logger = get_logger("simple_http_server.http_server")


class HTTPServer(socketserver.TCPServer, ThreadingMixIn):

    allow_reuse_address = 1    # Seems to make sense in testing environment

    HTTP_METHODS = ["OPTIONS", "GET", "HEAD", "POST", "PUT", "DELETE", "TRACE", "CONNECT"]

    def server_bind(self):
        """Override server_bind to store the server name."""
        socketserver.TCPServer.server_bind(self)
        host, port = self.server_address[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port

    def __init__(self, addr, res_conf={}):
        super().__init__(addr, BaseHTTPRequestHandler)
        self.method_url_mapping: Dict[str, Dict[str, ControllerFunction]] = {"_": {}}
        self.path_val_url_mapping: Dict[str, Dict[str, ControllerFunction]] = {"_": OrderedDict()}
        self.method_regexp_mapping: Dict[str, Dict[str, ControllerFunction]] = {"_": OrderedDict()}
        for mth in HTTPServer.HTTP_METHODS:
            self.method_url_mapping[mth] = {}
            self.path_val_url_mapping[mth] = OrderedDict()
            self.method_regexp_mapping[mth] = OrderedDict()

        self.filter_mapping = OrderedDict()
        self._res_conf = []
        self.websocket_handler_mapping = OrderedDict()
        self.add_res_conf(res_conf)

    @property
    def res_conf(self):
        return self._res_conf

    @res_conf.setter
    def res_conf(self, val: Dict[str, str]):
        self._res_conf.clear()
        self.add_res_conf(val)

    def add_res_conf(self, val: Dict[str, str]):
        if not val or not isinstance(val, dict):
            return
        for res_k, v in val.items():
            if res_k.startswith("/"):
                k = res_k[1:]
            else:
                k = res_k
            if k.endswith("/*"):
                key = k[0:-1]
            elif k.endswith("/**"):
                key = k[0:-2]
            elif k.endswith("/"):
                key = k
            else:
                key = k + "/"

            if v.endswith(os.path.sep):
                val = v
            else:
                val = v + os.path.sep
            self._res_conf.append((key, val))
        self._res_conf.sort(key=lambda it: -len(it[0]))

    def __get_path_reg_pattern(self, url):
        _url: str = url
        path_names = re.findall("(?u)\\{\\w+\\}", _url)
        if len(path_names) == 0:
            # normal url
            return None, path_names
        for name in path_names:
            _url = _url.replace(name, "([\\w%.-@!\\(\\)\\[\\]\\|\\$]+)")
        _url = f"^{_url}$"

        quoted_names = []
        for name in path_names:
            name = name[1: -1]
            quoted_names.append(quote(name))
        return _url, quoted_names

    def map_controller(self, ctrl: ControllerFunction):
        url = ctrl.url
        regexp = ctrl.regexp
        method = ctrl.method
        _logger.debug(f"map url {url}|{regexp} with method[{method}] to function {ctrl.func}. ")
        assert method is None or method == "" or method.upper() in HTTPServer.HTTP_METHODS
        _method = method.upper() if method is not None and method != "" else "_"
        if regexp:
            self.method_regexp_mapping[_method][regexp] = ctrl
        else:
            _url = remove_url_first_slash(url)

            path_pattern, path_names = self.__get_path_reg_pattern(_url)
            if path_pattern is None:
                self.method_url_mapping[_method][_url] = ctrl
            else:
                self.path_val_url_mapping[_method][path_pattern] = (ctrl, path_names)

    def _res_(self, path, res_pre, res_dir):
        fpath = os.path.join(res_dir, path.replace(res_pre, ""))
        _logger.debug(f"static file. {path} :: {fpath}")
        fext = os.path.splitext(fpath)[1]
        ext = fext.lower()
        if ext in (".html", ".htm", ".xhtml"):
            content_type = "text/html"
        elif ext == ".xml":
            content_type = "text/xml"
        elif ext == ".css":
            content_type = "text/css"
        elif ext in (".jpg", ".jpeg"):
            content_type = "image/jpeg"
        elif ext == ".png":
            content_type = "image/png"
        elif ext == ".webp":
            content_type = "image/webp"
        elif ext == ".js":
            content_type = "text/javascript"
        elif ext == ".pdf":
            content_type = "application/pdf"
        elif ext == ".mp4":
            content_type = "video/mp4"
        elif ext == ".mp3":
            content_type = "audio/mp3"
        else:
            content_type = "application/octet-stream"

        return StaticFile(fpath, content_type)

    def get_url_controller(self, path="", method="") -> Tuple[Callable, Dict, List]:
        # explicitly url matching
        if path in self.method_url_mapping[method]:
            return self.method_url_mapping[method][path], {}, ()
        elif path in self.method_url_mapping["_"]:
            return self.method_url_mapping["_"][path], {}, ()

        # url with path value matching
        fun_and_val = self.__try_get_from_path_val(path, method)
        if fun_and_val is None:
            fun_and_val = self.__try_get_from_path_val(path, "_")
        if fun_and_val is not None:
            return fun_and_val[0], fun_and_val[1], ()

        # regexp
        func_and_groups = self.__try_get_from_regexp(path, method)
        if func_and_groups is None:
            func_and_groups = self.__try_get_from_regexp(path, "_")
        if func_and_groups is not None:
            return func_and_groups[0], {}, func_and_groups[1]
        # static files
        for k, v in self.res_conf:
            if path.startswith(k):
                def static_fun():
                    return self._res_(path, k, v)
                return static_fun, {}, ()
        return None, {}, ()

    def __try_get_from_regexp(self, path, method):
        for regex, ctrl in self.method_regexp_mapping[method].items():
            m = re.match(regex, path)
            _logger.debug(f"regexp::pattern::[{regex}] => path::[{path}] match? {m is not None}")
            if m:
                return ctrl, tuple([unquote(v) for v in m.groups()])
        return None

    def __try_get_from_path_val(self, path, method):
        for patterns, val in self.path_val_url_mapping[method].items():
            m = re.match(patterns, path)
            _logger.debug(f"url with path value::pattern::[{patterns}] => path::[{path}] match? {m is not None}")
            if m:
                fun, path_names = val
                path_values = {}
                for idx in range(len(path_names)):
                    key = unquote(path_names[idx])
                    path_values[key] = unquote(m.groups()[idx])
                return fun, path_values
        return None

    def map_filter(self, path_pattern, filter_fun):
        self.filter_mapping[path_pattern] = filter_fun

    def get_matched_filters(self, path):
        available_filters = []
        for key, val in self.filter_mapping.items():
            if re.match(key, path):
                available_filters.append(val)
        return available_filters

    def map_websocket_hanlder(self, endpoint, handler_class):
        self.websocket_handler_mapping[remove_url_first_slash(endpoint)] = handler_class

    def get_matched_websocket_handler(self, path):
        if path not in self.websocket_handler_mapping:
            return None
        return self.websocket_handler_mapping[path]


class SimpleDispatcherHttpServer:
    """Dispatcher Http server"""

    def map_filter(self, path_pattern, filter_fun):
        self.server.map_filter(path_pattern, filter_fun)

    def map_request(self, ctrl: ControllerFunction):
        self.server.map_controller(ctrl)

    def map_websocket_handler(self, endpoint, handler_class):
        self.server.map_websocket_hanlder(endpoint, handler_class)

    def __init__(self,
                 host: Tuple[str, int] = ('', 9090),
                 ssl: bool = False,
                 ssl_protocol: int = _ssl.PROTOCOL_TLS_SERVER,
                 ssl_check_hostname: bool = False,
                 keyfile: str = "",
                 certfile: str = "",
                 keypass: str = "",
                 ssl_context: _ssl.SSLContext = None,
                 resources: Dict[str, str] = {}):
        self.host = host

        self.ssl = ssl
        self.server = HTTPServer(self.host, res_conf=resources)

        if ssl:
            if ssl_context:
                ssl_ctx = ssl_context
            else:
                assert keyfile and certfile, "keyfile and certfile should be provided. "
                ssl_ctx = _ssl.SSLContext(protocol=ssl_protocol)
                ssl_ctx.check_hostname = ssl_check_hostname
                ssl_ctx.load_cert_chain(certfile=certfile, keyfile=keyfile, password=keypass)
            self.server.socket = ssl_ctx.wrap_socket(
                self.server.socket,
                server_side=True
            )

    def resources(self, res={}):
        self.server.res_conf = res

    def start(self):
        if self.ssl:
            ssl_hint = " with SSL on"
        else:
            ssl_hint = ""
        _logger.info(f"Dispatcher Http Server starts. Listen to port [{self.host[1]}]{ssl_hint}.")
        self.server.serve_forever()

    def shutdown(self):
        # server must shutdown in a separate thread, or it will be deadlocking...WTF!
        t = threading.Thread(target=self.server.shutdown)
        t.daemon = True
        t.start()

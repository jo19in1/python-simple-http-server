# python-simple-http-server

[![PyPI version](https://badge.fury.io/py/simple-http-server.png)](https://badge.fury.io/py/simple-http-server)

## Discription

This is a simple http server, use MVC like design.

## Support Python Version

Python 3.7+

## Why choose

* Lightway.
* Functional programing.
* Filter chain support.
* Session support, and can support distributed session by [this extention](https://gitee.com/keijack/python-simple-http-server-redis-session).
* Spring MVC like request mapping.
* SSL support.
* Websocket support
* Easy to use.
* Free style controller writing.
* Easily integraded with WSGI servers. 
* Coroutine mode support.

## Dependencies

There are no other dependencies needed to run this project. However, if you want to run the unitests in the `tests` folder, you need to install `websocket` via pip:

```shell
python3 -m pip install websocket-client
```

## How to use

### Install

```shell
python3 -m pip install simple_http_server
```

### Write Controllers

```python

from simple_http_server import request_map
from simple_http_server import Response
from simple_http_server import MultipartFile
from simple_http_server import Parameter
from simple_http_server import Parameters
from simple_http_server import Header
from simple_http_server import JSONBody
from simple_http_server import HttpError
from simple_http_server import StaticFile
from simple_http_server import Headers
from simple_http_server import Cookies
from simple_http_server import Cookie
from simple_http_server import Redirect
from simple_http_server import ModelDict

# request_map has an alias name `route`, you can select the one you familiar with.
@request_map("/index")
def my_ctrl():
    return {"code": 0, "message": "success"}  # You can return a dictionary, a string or a `simple_http_server.simple_http_server.Response` object.


@route("/say_hello", method=["GET", "POST"])
def my_ctrl2(name, name2=Parameter("name", default="KEIJACK"), model=ModelDict()):
    """name and name2 is the same"""
    name == name2 # True
    name == model["name"] # True
    return "<!DOCTYPE html><html><body>hello, %s, %s</body></html>" % (name, name2)


@request_map("/error")
def my_ctrl3():
    return Response(status_code=500)


@request_map("/exception")
def exception_ctrl():
    raise HttpError(400, "Exception")

@request_map("/upload", method="GET")
def show_upload():
    root = os.path.dirname(os.path.abspath(__file__))
    return StaticFile("%s/my_dev/my_test_index.html" % root, "text/html; charset=utf-8")

@request_map("/upload", method="POST")
def my_upload(img=MultipartFile("img")):
    root = os.path.dirname(os.path.abspath(__file__))
    img.save_to_file(root + "/my_dev/imgs/" + img.filename)
    return "<!DOCTYPE html><html><body>upload ok!</body></html>"


@request_map("/post_txt", method="POST")
def normal_form_post(txt):
    return "<!DOCTYPE html><html><body>hi, %s</body></html>" % txt

@request_map("/tuple")
def tuple_results():
    # The order here is not important, we consider the first `int` value as status code,
    # All `Headers` object will be sent to the response
    # And the first valid object whose type in (str, unicode, dict, StaticFile, bytes) will
    # be considered as the body
    return 200, Headers({"my-header": "headers"}), {"success": True}

"""
" Cookie_sc will not be written to response. It's just some kind of default
" value
"""
@request_map("tuple_cookie")
def tuple_with_cookies(all_cookies=Cookies(), cookie_sc=Cookie("sc")):
    print("=====> cookies ")
    print(all_cookies)
    print("=====> cookie sc ")
    print(cookie_sc)
    print("======<")
    import datetime
    expires = datetime.datetime(2018, 12, 31)

    cks = Cookies()
    # cks = cookies.SimpleCookie() # you could also use the build-in cookie objects
    cks["ck1"] = "keijack"request
    cks["ck1"]["path"] = "/"
    cks["ck1"]["expires"] = expires.strftime(Cookies.EXPIRE_DATE_FORMAT)
    # You can ignore status code, headers, cookies even body in this tuple.
    return Header({"xx": "yyy"}), cks, "<html><body>OK</body></html>"

"""
" If you visit /a/b/xyz/x，this controller function will be called, and `path_val` will be `xyz`
"""
@request_map("/a/b/{path_val}/x")
def my_path_val_ctr(path_val=PathValue()):
    return f"<html><body>{path_val}</body></html>"

@request_map("/star/*") # /star/c will find this controller, but /star/c/d not.
@request_map("*/star") # /c/star will find this controller, but /c/d/star not.
def star_path(path_val=PathValue()):
    return f"<html><body>{path_val}</body></html>"

@request_map("/star/**") # Both /star/c and /star/c/d will find this controller.
@request_map("**/star") # Both /c/star and /c/d/stars will find this controller.
def star_path(path_val=PathValue()):
    return f"<html><body>{path_val}</body></html>"

@request_map("/redirect")
def redirect():
    return Redirect("/index")

@request_map("session")
def test_session(session=Session(), invalid=False):
    ins = session.get_attribute("in-session")
    if not ins:
        session.set_attribute("in-session", "Hello, Session!")

    __logger.info("session id: %s" % session.id)
    if invalid:
        __logger.info("session[%s] is being invalidated. " % session.id)
        session.invalidate()
    return "<!DOCTYPE html><html><body>%s</body></html>" % str(ins)

# use coroutine, these controller functions will work both in a coroutine mode or threading mode.

async def say(sth: str = ""):
    _logger.info(f"Say: {sth}")
    return f"Success! {sth}"

@request_map("/中文/coroutine")
async def coroutine_ctrl(hey: str = "Hey!"):
    return await say(hey)
```

Beside using the default values, you can also use variable annotations to specify your controller function's variables.

```python
@request_map("/say_hello/to/{name}", method=["GET", "POST", "PUT"])
def your_ctroller_function(
        user_name: str, # req.parameter["user_name"]，400 error will raise when there's no such parameter in the query string.
        password: str, # req.parameter["password"]，400 error will raise when there's no such parameter in the query string.
        skills: list, # req.parameters["skills"]，400 error will raise when there's no such parameter in the query string.
        all_headers: Headers, # req.headers
        user_token: Header, # req.headers["user_token"]，400 error will raise when there's no such parameter in the quest headers.
        all_cookies: Cookies, # req.cookies, return all cookies
        user_info: Cookie, # req.cookies["user_info"]，400 error will raise when there's no such parameter in the cookies.
        name: PathValue, # req.path_values["name"]，get the {name} value from your path.
        session: Session # req.getSession(True)，get the session, if there is no sessions, create one.
    ):
    return "<html><body>Hello, World!</body></html>"
```

We recommend using functional programing to write controller functions. but if you realy want to use Object, you can use `@request_map` in a class method. For doing this, every time a new request comes, a new MyController object will be created.

```python

class MyController:

    def __init__(self) -> None:
        self._name = "ctr object"

    @request_map("/obj/say_hello", method="GET")
    def my_ctrl_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

```

If you want a singleton, you can add a `@controller` decorator to the class.

```python

@controller
class MyController:

    def __init__(self) -> None:
        self._name = "ctr object"

    @request_map("/obj/say_hello", method="GET")
    def my_ctrl_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

```

You can also add the `@request_map` to your class, this will be as the part of the url.

```python

@controller
@request_map("/obj", method="GET")
class MyController:

    def __init__(self) -> None:
        self._name = "ctr object"

    @request_map
    def my_ctrl_default_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

    @request_map("/say_hello", method=("GET", "POST"))
    def my_ctrl_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

```

You can specify the `init` variables in `@controller` decorator. 

```python

@controller(args=["ctr_name"], kwargs={"desc": "this is a key word argument"})
@request_map("/obj", method="GET")
class MyController:

    def __init__(self, name, desc="") -> None:
        self._name = f"ctr[{name}] - {desc}"

    @request_map
    def my_ctrl_default_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

    @request_map("/say_hello", method=("GET", "POST"))
    def my_ctrl_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

```

From `0.7.0`, `@request_map` support regular expression mapping. 

```python
# url `/reg/abcef/aref/xxx` can map the flowing controller:
@route(regexp="^(reg/(.+))$", method="GET")
def my_reg_ctr(reg_groups: RegGroups, reg_group: RegGroup = RegGroup(1)):
    print(reg_groups) # will output ("reg/abcef/aref/xxx", "abcef/aref/xxx")
    print(reg_group) # will output "abcef/aref/xxx"
    return f"{self._name}, {reg_group.group},{reg_group}"
```
Regular expression mapping a class:

```python
@controller(args=["ctr_name"], kwargs={"desc": "this is a key word argument"})
@request_map("/obj", method="GET") # regexp do not work here, method will still available
class MyController:

    def __init__(self, name, desc="") -> None:
        self._name = f"ctr[{name}] - {desc}"

    @request_map
    def my_ctrl_default_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

    @route(regexp="^(reg/(.+))$") # prefix `/obj`  from class decorator will be ignored, but `method`(GET in this example) from class decorator will still work.
    def my_ctrl_mth(self, name: str):
        return {"message": f"hello, {name}, {self._name} says. "}

```

### Session

Defaultly, the session is stored in local, you can extend `SessionFactory` and `Session` classes to implement your own session storage requirement (like store all data in redis or memcache)

```python
from simple_http_server import Session, SessionFactory, set_session_factory

class MySessionImpl(Session):

    def __init__(self):
        super().__init__()
        # your own implementation

    @property
    def id(self) -> str:
        # your own implementation

    @property
    def creation_time(self) -> float:
        # your own implementation

    @property
    def last_accessed_time(self) -> float:
        # your own implementation

    @property
    def is_new(self) -> bool:
        # your own implementation

    @property
    def attribute_names(self) -> Tuple:
        # your own implementation

    def get_attribute(self, name: str) -> Any:
        # your own implementation

    def set_attribute(self, name: str, value: Any) -> None:
        # your own implementation

    def invalidate(self) -> None:
        # your own implementation

class MySessionFacImpl(SessionFactory):

    def __init__(self):
        super().__init__()
        # your own implementation

    
    def get_session(self, session_id: str, create: bool = False) -> Session:
        # your own implementation
        return MySessionImpl()

set_session_factory(MySessionFacImpl())

```

There is an offical Redis implementation here: https://github.com/keijack/python-simple-http-server-redis-session.git

### Websocket

```python
from simple_http_server import WebsocketHandler, WebsocketRequest,WebsocketSession, websocket_handler

@websocket_handler(endpoint="/ws/{path_val}")
class WSHandler(WebsocketHandler):

    def on_handshake(self, request: WebsocketRequest):
        """
        "
        " You can get path/headers/path_values/cookies/query_string/query_parameters from request.
        " 
        " You should return a tuple means (http_status_code, headers)
        "
        " If status code in (0, None, 101), the websocket will be connected, or will return the status you return. 
        "
        " All headers will be send to client
        "
        """
        _logger.info(f">>{session.id}<< open! {request.path_values}")
        return 0, {}

    def on_open(self, session: WebsocketSession):
        """
        " 
        " Will be called when the connection opened.
        "
        """
        _logger.info(f">>{session.id}<< open! {session.request.path_values}")

    def on_text_message(self, session: WebsocketSession, message: str):
        """
        "
        " Will be called when receive a text message.
        "
        """
        _logger.info(f">>{session.id}<< on text message: {message}")
        session.send(message)

    def on_close(self, session: WebsocketSession, reason: str):
        """
        "
        " Will be called when the connection closed.
        "
        """
        _logger.info(f">>{session.id}<< close::{reason}")
```

### Error pages

You can use `@error_message` to specify your own error page. See:

```python
from simple_http_server import error_message
# map specified codes
@error_message("403", "404")
def my_40x_page(message: str, explain=""):
    return f"""
    <html>
        <head>
            <title>发生错误！</title>
        <head>
        <body>
            message: {message}, explain: {explain}
        </body>
    </html>
    """

# map specified code rangs
@error_message("40x", "50x")
def my_error_message(code, message, explain=""):
    return f"{code}-{message}-{explain}"

# map all error page
@error_message
def my_error_message(code, message, explain=""):
    return f"{code}-{message}-{explain}"
```

### Write filters

This server support filters, you can use `request_filter` decorator to define your filters.

```python
from simple_http_server import request_filter

@request_filter("/tuple/**") # use wildcard
@request_filter(regexp="^/tuple") # use regular expression
def filter_tuple(ctx):
    print("---------- through filter ---------------")
    # add a header to request header
    ctx.request.headers["filter-set"] = "through filter"
    if "user_name" not in ctx.request.parameter:
        ctx.response.send_redirect("/index")
    elif "pass" not in ctx.request.parameter:
        ctx.response.send_error(400, "pass should be passed")
        # you can also raise a HttpError
        # raise HttpError(400, "pass should be passed")
    else:
        # you should always use do_chain method to go to the next
        ctx.do_chain()
```

### Start your server

```python
# If you place the controllers method in the other files, you should import them here.

import simple_http_server.server as server
import my_test_ctrl


def main(*args):
    # The following method can import several controller files once.
    server.scan("my_ctr_pkg", r".*controller.*")
    server.start()

if __name__ == "__main__":
    main()
```

If you want to specify the host and port:

```python
    server.start(host="", port=8080)
```

If you want to specify the resources path: 

*Notice: `/path_prefix/`/`/path_prefix/*`/`/path_prefix/**` is the same effect.*

```python 
    server.start(resources={"/path_prefix/*", "/absolute/dir/root/path",
                            "/path_prefix/*", "/absolute/dir/root/path"})
```

If you want to use ssl:

```python
    server.start(host="", 
                 port=8443,
                 ssl=True,
                 ssl_protocol=ssl.PROTOCOL_TLS_SERVER, # Optional, default is ssl.PROTOCOL_TLS_SERVER, which will auto detect the highted protocol version that both server and client support. 
                 ssl_check_hostname=False, #Optional, if set to True, if the hostname is not match the certificat, it cannot establish the connection, default is False.
                 keyfile="/path/to/your/keyfile.key",
                 certfile="/path/to/your/certfile.cert",
                 keypass="", # Optional, your private key's password
                 )
```

### Coroutine

From `0.12.0`, you can use coroutine tasks than threads to handle requests, you can set the `prefer_coroutine` parameter in start method to enable the coroutine mode. 

```python
    server.start(prefer_coroutine=True)
```

From `0.13.0`, coroutine mode uses the coroutine server, that means all requests will use the async I/O rather than block I/O. So you can now use `async def` to define all your controllers including the Websocket event callback methods.

## Logger

The default logger is try to write logs to the screen, you can specify the logger handler to write it to a file.

```python
import simple_http_server.logger as logger
import logging

_formatter = logging.Formatter(fmt='[%(asctime)s]-[%(name)s]-%(levelname)-4s: %(message)s')
_handler = logging.TimedRotatingFileHandler("/var/log/simple_http_server.log", when="midnight", backupCount=7)
_handler.setFormatter(_formatter)
_handler.setLevel("INFO")

logger.set_handler(_handler)
```

If you want to add a handler rather than replace the inner one, you can use:

```python
logger.add_handler(_handler)
```

If you want to change the logger level:

```python
logger.set_level("DEBUG")
```

This logger will first save all the log record to a global queue, and then output them in a background thread, so it is very suitable for getting several logger with a same handler, especialy the `TimedRotatingFileHandler` which may slice the log files not quite well in a mutiple thread environment. 


## WSGI Support

You can use this module in WSGI apps. 

```python
import simple_http_server.server as server
import os
from simple_http_server import request_map


# scan all your controllers
server.scan("tests/ctrls", r'.*controllers.*')
# or define a new controller function here
@request_map("/hello_wsgi")
def my_controller(name: str):
    return 200, "Hello, WSGI!"
# resources is optional
wsgi_proxy = server.init_wsgi_proxy(resources={"/public/*": f"/you/static/files/path"})

# wsgi app entrance. 
def simple_app(environ, start_response):
    return wsgi_proxy.app_proxy(environ, start_response)

# If your entrance is async:
async def simple_app(envion, start_response):
    return await wsgi_proxy.async_app_proxy(environ, start_response)
```

## Thanks

The code that process websocket comes from the following project: https://github.com/Pithikos/python-websocket-server
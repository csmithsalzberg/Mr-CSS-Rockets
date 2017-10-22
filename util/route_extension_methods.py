from flask import Flask
from flask import Response
from flask import redirect
from flask import url_for

from oop import override
from template_context import context

_route_extensions = []


def route_extension_method(route_extension):
    # type: (callable) -> callable
    _route_extensions.append(route_extension)
    return route_extension


@route_extension_method
def url(route_func):
    # type: (callable) -> str
    return url_for(route_func.func_name)


@route_extension_method
def route_to(route_func):
    # type: (callable) -> Response
    return redirect(url_for(route_func.func_name))


@override(Flask)
def route(_super, app, rule, **options):
    # type: (callable, Flask, str, dict[str, any]) -> callable
    def decorator(route_func):
        # type: (callable) -> callable
        route_func = _super(app, rule, **options)(route_func)

        for _route_extension in _route_extensions:
            func_name = _route_extension.func_name

            def route_extension():
                return _route_extension(route_func)

            route_extension.func_name = func_name
            setattr(route_func, func_name, route_extension)

        # add to template context
        context[route_func.func_name] = route_func

        return route_func

    return decorator

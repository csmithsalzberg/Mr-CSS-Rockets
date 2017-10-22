def extend(klass):
    # type: (type) -> callable
    def extender(extension_method):
        # type: (callable) -> None
        setattr(klass, extension_method.func_name, extension_method)
        return None

    return extender


def override(klass):
    # type: (type) -> callable
    def overrider(override_method):
        # type: (callable) -> None
        func_name = override_method.func_name
        super_method = getattr(klass, func_name)

        def override_closure(self, *args, **kwargs):
            return override_method(super_method, self, *args, **kwargs)

        setattr(klass, func_name, override_closure)
        return None

    return overrider

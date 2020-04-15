class ServiceMeta(type):
    def __init__(cls, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Service(metaclass=ServiceMeta):
    pass

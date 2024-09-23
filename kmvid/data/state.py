import kmvid.data.common as common
import kmvid.data.resource as resource
import kmvid.data.variable as variable

time = 0
resource_manager = None
render = None

class State:
    def __enter__(self):
        global time
        global resource_manager

        time = 0
        resource_manager = resource.ResourceManager()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        global time
        global resource_manager

        time = 0

        if resource_manager:
            resource_manager.close()
            resource_manager = None

class Render:
    def __init__(self, *args, **kwargs):
        self.render = common.Render(*args, **kwargs)
        self.old = None

    def __enter__(self):
        global render

        self.old = render
        render = self.render
        return self.render

    def __exit__(self, exc_type, exc_value, traceback):
        global render
        render = self.old

def local_time(node, t=None):
    if t is None:
        t = time

    while node.parent:
        if isinstance(node, variable.VariableHold):
            var = node.get_variable("start_time")
            if var:
                value = var.get_value()
                if value:
                    t -= value
        elif getattr(node, 'start_time', None):
            t -= node.start_time or 0

        node = node.parent

    return t

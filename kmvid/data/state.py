import kmvid.data.common as common
import kmvid.data.resource as resource
import kmvid.data.variable as variable

global_time = 0
local_time = 0
resource_manager = None
render = None

def set_time(time):
    """Sets the time (local and global). For use at the root level of
    rendering to set what time to render.

    """
    global global_time
    global local_time
    global_time = time
    local_time = time

class State:
    def __enter__(self):
        global global_time
        global local_time
        global resource_manager

        global_time = 0
        local_time = 0
        resource_manager = resource.ResourceManager()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        global global_time
        global local_time
        global resource_manager

        global_time = 0
        local_time = 0

        if resource_manager:
            resource_manager.close()
            resource_manager = None

class AdjustLocalTime:
    def __init__(self, time_offset):
        self.time_offset = time_offset

    def __enter__(self):
        global local_time
        local_time -= self.time_offset
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        global local_time
        local_time += self.time_offset

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

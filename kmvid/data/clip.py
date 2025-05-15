import kmvid.data.common as common
import kmvid.data.effect as effect
import kmvid.data.variable as variable
import kmvid.data.resource as resource
import kmvid.data.state as state

def color(width=100, height=100, color=(0, 0, 0), mode=None):
    return Clip(resource.ColorResource(width, height, color, mode))

def image(path, mode=None):
    return Clip(resource.ImageResource(path, mode))

def video(path):
    return Clip(resource.VideoResource(path))

@variable.holder
class Clip(common.Node, variable.VariableHold):
    """Clips contains effects and other clips.

    Each effect and clip are rendered in the same order that they are
    added. Sub-clips are truncated by the boundries of this clip.

    """

    start_time = variable.VariableConfig(
        float, 0, doc="""How far into the parent clip this clip starts.""")
    duration = variable.VariableConfig(
        float, doc="""Duration of the clip.

        If the clip is using a finite resource (such as a video) the
        duration will not be longer than the resource allows.""")

    def __init__(self, resource, **kwargs):
        common.Node.__init__(self)
        variable.VariableHold.__init__(self, kwargs=kwargs)

        self.resource = resource
        self.items = []
        self._time_map = None

    def get_time_map(self):
        """Returns the TimeMap object for this clip is applicable. Only
        underlaying resources with finite durations have TimeMap
        objects.

        """
        if self._time_map is None:
            info = self.resource.get_info()
            if info.duration is not None:
                self._time_map = resource.TimeMap(info.duration)

        return self._time_map

    time = property(get_time_map)

    def _get_duration(self):
        value = None
        if self.get_time_map():
            value = self.get_time_map().get_duration()
        else:
            value = self.resource.get_info().duration

        for item in self.items:
            if isinstance(item, Clip):
                duration = item.duration
                if duration is not None:
                    start = item.start_time
                    value = max(value or 0, start + duration)

        return value

    def add_item(self, item):
        if isinstance(item, (Clip, effect.Effect)):
            self.items.append(item)
            item.parent = self
        else:
            raise Exception("Unknown argument type %s" % str(type(item)))

    def get_frame(self):
        return self._get_frame_internal(None)

    def _get_frame_internal(self, parent_image):
        frame_time = state.local_time
        if self._time_map:
            frame_time = self._time_map.get(state.local_time)
        image = self.resource.get_frame(frame_time)

        with state.Render(parent_image, image) as render:
            for item in self.items:

                if isinstance(item, effect.Effect):
                    item.apply(render)

                elif isinstance(item, Clip):
                    start_time = item.start_time
                    duration = item.duration

                    if (start_time <= state.local_time and
                        (duration is None or
                         state.local_time < start_time + duration)):

                        sub_data = None

                        with state.AdjustLocalTime(start_time):
                            sub_data = item._get_frame_internal(image)

                        if sub_data is not None:
                            image.paste(
                                sub_data.image,
                                (int(sub_data.x), int(sub_data.y)),
                                (sub_data.image
                                 if sub_data.image.has_transparency_data
                                 else None))

                else:
                    raise Exception("Unknown item to render: %s" % str(item))

        return render

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(common.Node, self)
        s.merge_super(variable.VariableHold, self)
        s.set('resource', self.resource.to_simple())
        s.set('items', [item.to_simple() for item in self.items])
        s.set('time_map', self._time_map.to_simple() if self._time_map else None)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Clip(None)
        common.Node.from_simple(s, obj)
        variable.VariableHold.from_simple(s, obj)

        obj.resource = resource.Resource.from_simple(s.get_simple('resource'))
        obj.items = []
        for item in s.get('items', []):
            item_simple = common.Simple.from_data(s, item)
            if item.get('_type') == 'Clip':
                obj.items.append(Clip.from_simple(item_simple))
            elif  item.get('_type') == 'Effect':
                obj.items.append(effect.Effect.from_simple(item_simple))
            else:
                raise Exception(f"Unknown clip item type: {s.get('_type')}")
        obj._time_map = (resource.TimeMap.from_simple(s.get_simple('time_map'))
                         if s.get('time_map', None)
                         else None)

        return obj

import kmvid.data.common as common
import kmvid.data.ffmpeg as ffmpeg
import kmvid.data.state as state

import os.path
import sys

import PIL.Image

IMAGE_FORMATS = set([
    "blp", "bmp", "cur", "dcx", "dds", "dib", "emf", "eps",
    "fits", "flc", "fli", "fpx", "ftex", "gbr", "gd", "gif",
    "icns", "ico", "im", "imt", "jpeg", "jpg", "mcidas", "mic",
    "mpo", "msp", "pcd", "pcx", "pfm", "pixar", "png", "ppm",
    "psd", "qoi", "sgi", "spider", "sun", "tga", "tiff", "wal",
    "webp", "wmf", "xbm", "xpm",
])

VIDEO_FORMATS = set(ffmpeg.get_video_formats().keys())

def is_recognized_format(path):
    """Returns True if the extension name of the path is recognized as
    known file format.

    """
    _, ext = os.path.splitext(path)
    ext = ext.lower()[1:]
    return ext in IMAGE_FORMATS or ext in VIDEO_FORMATS

def from_file(path, **kwargs):
    """Creates a resource from the given file path."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()[1:]
    if ext in IMAGE_FORMATS:
        return ImageResource(path=path, **kwargs)
    elif ext in VIDEO_FORMATS:
        return VideoResource(path=path, **kwargs)
    else:
        raise ValueError(f"Unknown resource format for file '{path}'")

class Info:
    def __init__(self):
        self.width = None
        self.height = None
        self.duration = None
        self.fps = None

class Resource(common.Simpleable):
    def get_info(self):
        raise NotImplementedError()

    def get_frame(self, time):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def _heartbeat(self):
        if state.resource_manager is not None:
            state.resource_manager.report_heartbeat(self)

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            cls = getattr(sys.modules[__name__], s.get('_sub_type'))
            obj = cls.from_simple(s)

        return obj

class ColorResource(Resource):
    def __init__(self, width=100, height=100, color=(255, 255, 255), mode=None):
        Resource.__init__(self)
        self.width = width
        self.height = height
        self.color = color
        self.mode = mode
        self.image = None

    def get_info(self):
        info = Info()
        info.width = self.width
        info.height = self.height
        return info

    def _get_mode_from_color(self):
        color = self.color
        if isinstance(self.color, str):
            color = PIL.ImageColor.getrgb(self.color)
        if len(color) == 3:
            return "RGB"
        elif len(color) == 4:
            return "RGBA"
        else:
            raise ValueError("Unknown color format: %s", str(self.color))

    def get_frame(self, time):
        if self.image is None:
            self.image = PIL.Image.new(
                mode = self.mode or self._get_mode_from_color(),
                size = (int(self.width), int(self.height)),
                color = self.color)

        self._heartbeat()
        return self.image.copy()

    def close(self):
        self.image = None

    def to_simple(self):
        s = common.Simple(self)
        s.set('width', self.width)
        s.set('height', self.height)
        s.set('color', self.color)
        s.set('mode', self.mode)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = ColorResource()
        obj.width = s.get('width')
        obj.height = s.get('height')
        obj.color = s.get('color')
        obj.mode = s.get('mode')
        return obj

class ImageResource(Resource):
    def __init__(self, path, mode=None):
        Resource.__init__(self)
        self.path = path
        self.mode = mode
        self.image = None

        self._info = None

    def get_info(self):
        if self._info is None:
            self._info = Info()
            if self.image:
                self._info.width = self.image.width
                self._info.height = self.image.height
            else:
                with PIL.Image.open(self.path) as img:
                    self._info.width = img.width
                    self._info.height = img.height

        return self._info

    def get_frame(self, time):
        if self.image is None:
            with PIL.Image.open(self.path) as img:
                self.image = img if self.mode is None else img.convert(self.mode)

        self._heartbeat()
        return self.image.copy()

    def close(self):
        self.image = None

    def to_simple(self):
        s = common.Simple(self)
        s.set('path', self.path)
        s.set('mode', self.mode)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = ImageResource(None)
        obj.path = s.get('path')
        obj.mode = s.get('mode')
        return obj

class VideoResource(Resource):
    def __init__(self, path):
        Resource.__init__(self)
        self.path = path
        self.reader = None

        self._info = None

    def get_info(self):
        if self._info is None:
            probe = ffmpeg.Ffprobe(self.path)
            self._info = Info()
            self._info.width = probe.width
            self._info.height = probe.height
            self._info.fps = probe.fps
            self._info.duration = probe.duration

        return self._info

    def get_frame(self, time):
        if self.reader is None:
            self.reader = ffmpeg.FfmpegReader(self.path)

        self._heartbeat()
        return self.reader.get_frame(time)

    def close(self):
        if self.reader is not None:
            self.reader.close()
            self.reader = None

    def to_simple(self):
        s = common.Simple(self)
        s.set('path', self.path)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = VideoResource(None)
        obj.path = s.get('path')
        return obj

class ResourceManager:
    def __init__(self):
        self.resources = set()

    def report_heartbeat(self, resource_instance):
        self.resources.add(resource_instance)

    def close(self):
        for r in self.resources:
            r.close()

        self.resources = set()

class MappingEntry(common.Simpleable):
    def __init__(self, in_time, out_time, out_time_end=None):
        self.in_time = in_time
        self.out_time = out_time
        self.out_time_end = out_time_end

    def get_end_time(self):
        """Returns out_time_end if set, otherwise out_time."""
        if self.out_time_end is not None:
            return self.out_time_end
        return self.out_time

    def to_simple(self):
        s = common.Simple(self)
        s.set('in_time', self.in_time)
        s.set('out_time', self.out_time)
        s.set('out_time_end', self.out_time_end)
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = MappingEntry(0, 0)

        obj.in_time = s.get('in_time')
        obj.out_time = s.get('out_time')
        obj.out_time_end = s.get('out_time_end')

        return obj

class TimeMap(common.Simpleable):
    def __init__(self, duration):
        self._duration = duration
        self._mapping = [MappingEntry(0, 0),
                         MappingEntry(duration, duration)]

    def _validate(self):
        errors = []

        if self._mapping[0].in_time != 0:
            errors.append("First in_time must be 0")

        in_times = [e.in_time for e in self._mapping]
        if in_times != sorted(in_times):
            errors.append("In times are out of order")
        if len(in_times) != len(set(in_times)):
            errors.append("Multiple identical in time values")

        out_times = []
        for e in self._mapping:
            out_times.append(e.out_time)
            if e.out_time_end is not None:
                out_times.append(e.out_time_end)
        if out_times != sorted(out_times):
            errors.append("Out times are out of order")
        if len(out_times) != len(set(out_times)):
            errors.append("Multiple identical out time values")

        if len(errors) > 0:
            raise ValueError(self.__repr__() + " " + ", ".join(errors))

    def _get_index(self, in_time):
        for i, e in enumerate(self._mapping):
            if e.in_time > in_time:
                return i - 1
        return None

    def get(self, in_time):
        """Returns the out_time corresponding to the given in_time."""
        index = self._get_index(in_time)
        if index is None:
            return None

        this = self._mapping[index]
        next = self._mapping[index + 1]

        if this.in_time == in_time:
            return this.get_end_time()

        in_time_duration = next.in_time - this.in_time
        out_time_duration = next.out_time - this.get_end_time()
        factor = (in_time - this.in_time) / in_time_duration

        return this.get_end_time() + out_time_duration * factor

    def get_duration(self):
        return self._mapping[-1].in_time

    def set_crop_start(self, duration):
        """Crop the start, removing the given duration.

        This method overrides any previous set_crop_start calls. It
        maintains the speed of segments.

        """
        this = self._mapping[0]
        next = self._mapping[1]

        old_out_duration = next.out_time - this.get_end_time()

        this.out_time = 0
        this.out_time_end = duration

        new_out_duration = next.out_time - this.get_end_time()

        out_diff = new_out_duration - old_out_duration
        out_factor = out_diff / old_out_duration
        in_diff = next.in_time * out_factor

        for e in self._mapping[1:]:
            next.in_time += in_diff

        self._validate()

    def set_crop_end(self, duration):
        """Crop the end, removing the given duration.

        This method overrides any previous set_crop_end calls. It
        maintains the speed of segments.

        """
        prev = self._mapping[-2]
        this = self._mapping[-1]

        old_in_duration = this.in_time - prev.in_time
        old_out_duration = this.out_time - prev.get_end_time()

        this.out_time = self._duration - duration
        this.out_time_end = self._duration

        new_out_duration = this.out_time - prev.get_end_time()
        factor = new_out_duration / old_out_duration

        this.in_time = prev.in_time + old_in_duration * factor

        self._validate()

    def set_speed(self, speed_factor):
        """Sets the speed. This overrides any previous speed configuration.

        A speed_factor of 2 means that it's running twice as fast, 0.5
        means that it's running at half speed.

        """
        factor = 1 / speed_factor

        for index in range(0, len(self._mapping) - 1):
            this = self._mapping[index]
            next = self._mapping[index + 1]

            out_duration = next.out_time - this.get_end_time()
            next.in_time = this.in_time + out_duration * factor

        self._validate()

    def __repr__(self):
        s = "TimeMap(" + str(self._duration) + ", ["

        first = True
        for e in self._mapping:
            if first:
                first = False
            else:
                s += ", "

            if e.out_time_end is None:
                s += "%s > %s" % (str(e.in_time),
                                  str(e.out_time))
            else:
                s += "%s > (%s, %s)" % (str(e.in_time),
                                        str(e.out_time),
                                        str(e.out_time_end))

        s += "])"
        return s

    def to_simple(self):
        s = common.Simple(self)
        s.set('duration', self._duration)
        s.set('mapping', [e.to_simple() for e in self._mapping])
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = TimeMap(None)

        obj._duration = s.get('duration')
        obj._mapping = [MappingEntry.from_simple(common.Simple.from_data(s, entry_data))
                        for entry_data in s.get('mapping')]

        return obj

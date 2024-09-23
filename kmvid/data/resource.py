import kmvid.data.common as common
import kmvid.data.ffmpeg as ffmpeg
import kmvid.data.state as state

import os.path
import sys

import PIL.Image

IMAGE_FORMATS = set([
    ".blp", ".bmp", ".cur", ".dcx", ".dds", ".dib", ".emf", ".eps",
    ".fits", ".flc", ".fli", ".fpx", ".ftex", ".gbr", ".gd", ".gif",
    ".icns", ".ico", ".im", ".imt", ".jpeg", ".jpg", ".mcidas", ".mic",
    ".mpo", ".msp", ".pcd", ".pcx", ".pfm", ".pixar", ".png", ".ppm",
    ".psd", ".qoi", ".sgi", ".spider", ".sun", ".tga", ".tiff", ".wal",
    ".webp", ".wmf", ".xbm", ".xpm",
])

VIDEO_FORMATS = set(ffmpeg.get_video_formats().keys())

def is_recognized_format(path):
    """Returns True if the extension name of the path is recognized as
    known file format.

    """
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    return ext in IMAGE_FORMATS or ext in VIDEO_FORMATS

def from_file(path, **kwargs):
    """Creates a resource from the given file path."""
    _, ext = os.path.splitext(path)
    ext = ext.lower()
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
        state.resource_manager.report_heartbeat(self)

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            cls = getattr(sys.modules[__name__], s.get('_sub_type'))
            obj = cls.from_simple(s)

        return obj

class ColorResource(Resource):
    def __init__(self, width=100, height=100, color=(255, 255, 255), mode="RGB"):
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

    def get_frame(self, time):
        if self.image is None:
            self.image = PIL.Image.new(mode = self.mode,
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
    def __init__(self, path, mode="RGB"):
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
                self.image = img.convert(self.mode)

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

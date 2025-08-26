import kmvid.data.clip as clip
import kmvid.data.common as common
import kmvid.data.ffmpeg as ffmpeg
import kmvid.data.state as state
import kmvid.data.variable as variable

import math
import sys
import threading
import time

import PIL.Image

@variable.holder
class Project(common.Node, variable.VariableHold):
    """Project is the base for rendering. It contains convenience
    functions for generating video and images.

    """

    width = variable.VariableConfig(
        int, 800, doc="""Width of rendered video.""")
    height = variable.VariableConfig(
        int, 600, doc="""Height of rendered video.""")
    fps = variable.VariableConfig(
        float, 30, doc="""Frames per second to use when rendering video.""")
    filename = variable.VariableConfig(
        str, "output.mp4", doc="""Path to use when rendering video.""")
    duration = variable.VariableConfig(
        "time", None,
        doc="""Target duration of the rendered video.

        If not set duration is derived from clips added to the
        project. If duration is not set and not able to be derived
        some rendering functions will fail."""
    )

    def __init__(self, *args, **kwargs):
        common.Node.__init__(self)
        variable.VariableHold.__init__(self, args=args, kwargs=kwargs)

        self.root_clip = clip.color(width = self.width,
                                    height = self.height,
                                    color = (0, 0, 0))
        self.root_clip.parent = self

    def _get_duration(self):
        clip = self.root_clip.duration
        user = self.get_variable('duration').get_value(external_lookup=False)
        if clip and user:
            return min(clip, user)
        return clip or user

    def add(self, *clips):
        for clp in clips:
            self.root_clip.add(clp)
        return self

    def get_frame(self, time=0):
        """Returns the frame at the given time as an image.

        Call 'show' on the image to display it directly.

        """
        with state.State():
            state.set_time(time)
            render = self.root_clip.get_frame()
            return render.image

    def get_frame_wall(self, width=1920, cols=3, rows=None, frame_selection=None):
        """Returns an image with a grid of frames from the project.

        Call 'show' on the image to display it directly.

        width -- Sets the width of the returned image. The height of
        the image is dynamically determined from frame selection
        arguments.

        cols -- The number of frames to display horizontally.

        rows -- The number of frames to display vertically. Defaults
        to 3 if no other discriminatory arguments are given. The frame
        selection is spread evenly over the duration of the project.

        frame_selection -- An iterable containing the times at which
        to extract frames. If given the rows argument will be ignored,
        it will be set automatically to accommodate all the given
        times.

        """
        if frame_selection is None:
            rows = rows or 3
            total_frames = cols * rows
            step = self.duration / total_frames
            frame_selection = [t * step for t in range(total_frames)]
        else:
            frame_selection = [t for t in frame_selection]
            rows = math.ceil(len(frame_selection) / cols)

        tile_width = int(width / cols)
        tile_height = int(tile_width / self.width * self.height)
        image = PIL.Image.new("RGB", size=(width, tile_height * rows))

        with state.State():
            count = 0
            for time in frame_selection:
                frame = self.get_frame(time)
                if frame is not None:
                    tile = frame.resize((tile_width, tile_height))
                    x = (count % cols) * tile_width
                    y = int(count / cols) * tile_height
                    image.paste(tile, (x, y))
                count += 1

        return image

    def write(self):
        """Renders the project to the filename given."""
        with state.State():
            time = 0
            frame_time = 1 / self.fps
            duration = self.duration

            with ffmpeg.FfmpegWriter(self.filename,
                                     (self.width, self.height),
                                     self.fps) as writer:
                with ProgressTracker(self) as tracker:
                    while time < duration:
                        state.set_time(time)
                        render = self.root_clip.get_frame()
                        writer.write_frame(render.image)
                        tracker.report_frame(state.global_time)
                        time += frame_time

    def to_simple(self):
        s = common.Simple(self)
        s.merge_super(common.Node, self)
        s.merge_super(variable.VariableHold, self)
        s.set('root_clip', self.root_clip.to_simple())
        return s

    @staticmethod
    def from_simple(s, obj=None):
        if obj is None:
            obj = Project()
        common.Node.from_simple(s, obj)
        variable.VariableHold.from_simple(s, obj)
        obj.root_clip = clip.Clip.from_simple(s.get_simple('root_clip'))
        return obj

class ProgressTracker(threading.Thread):
    def __init__(self, project):
        threading.Thread.__init__(self)
        self.current_time = 0
        self.current_frame = 0

        frame_padding = len(str(project.duration * project.fps))
        time_padding = len("%.2f" % project.duration)

        self.fmt = "\r%s  ::  %%%dd frames  ::  %%%d.2f / %.2f sec" % (
            project.filename,
            frame_padding,
            time_padding,
            project.duration)

        self.running = True
        self.sleep_duration = 1

    def report_frame(self, current_time):
        self.current_time = current_time
        self.current_frame += 1

    def write_progress(self):
        sys.stdout.write(self.fmt % (
            self.current_frame,
            self.current_time))

    def run(self):
        while self.running:
            time.sleep(self.sleep_duration)
            self.write_progress()

    def __enter__(self):
        self.write_progress()
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.running = False
        self.join()
        self.write_progress()
        sys.stdout.write("\n")

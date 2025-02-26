import PIL.Image
import json
import logging
import os
import subprocess

logger = logging.getLogger(__name__)

_FFMPEG_PATH = "bin/ffmpeg.exe"
_FFPROBE_PATH = "bin/ffprobe.exe"

class FfmpegWriter:
    def __init__(self, filename, size, fps):
        """filename -- File to write to. If the file exists it will be
        overwritten.

        size -- (w, h) tuple designating the width and height for the
        video. This must match the images fed to write_frame.

        fps -- The FPS to use for the generated video.

        """
        self.filename = filename
        self.size = size
        self.fps = fps if isinstance(fps, str) else "%.02f" % fps

        # ffmpeg documentation
        #
        # As a general rule, options are applied to the next specified
        # file. Therefore, order is important, and you can have the
        # same option on the command line multiple times. Each
        # occurrence is then applied to the next input or output file.
        # Exceptions from this rule are the global options (e.g.
        # verbosity level), which should be specified first.
        #
        # Do not mix input and output files - first specify all input
        # files, then all output files. Also do not mix options which
        # belong to different files. All options apply ONLY to the
        # next input or output file and are reset between files.

        cmd = [
            # command
            _FFMPEG_PATH,
            '-y', # overwrite existing files
            '-loglevel', 'quiet',

            # input video
            '-s'       , '%dx%d' % size, # frame size
            '-r'       , self.fps,       # frame rate
            '-f'       , 'rawvideo',     # input file format
            '-codec:v' , 'rawvideo',     # video codec
            '-pix_fmt' , 'rgb24',        # pixel format
            # '-an'      ,                 # disable audio stream (needed?)
            '-i'       , '-',            # use stdin

            # output video
            '-codec:v'    , 'libx264', # video codec
            '-preset'     , 'medium',  # preset for x264 (ultrafast, superfast, veryfast, faster, fast, medium, slow, veryslow)
            self.filename ,            # output file
        ]

        self.process = subprocess.Popen(cmd, stdin = subprocess.PIPE)

    def write_frame(self, image):
        """Write the given image as the next video frame.

        image -- A pillow image object. It will automatically be
        converted to fit the video format.

        """
        image = image.convert("RGB")
        self.process.stdin.write(image.tobytes())

    def close(self):
        if self.process:
            self.process.stdin.close()
            try:
                return_code = self.process.wait(5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

            if return_code != 0:
                raise Exception("ffmpeg existing with code %d" % return_code)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class FfmpegReader:
    def __init__(self, filename):
        """Create a frame reader for the given filename.

        filename -- File to read from.

        """
        self.filename = filename
        self.fps = None
        self.size = (1, 1)

        self._frame_size = None
        self._frame_time = None

        self._process = None
        self._last_frame = None
        self._reset_threshold = 5

    def get_frame_info(self, time):
        """Returns a FrameInfo object corresponding to the given time.

        If the time is past the duration of the video a FrameInfo with
        the eof attribute set to True will be returned.

        This method is optimized for sequential fetching of frames. If
        the requested time is in the past or too far into the future a
        complete reset of the internal state will occur to fetch that
        frame.

        The FrameInfo object returned is cached so fetching the same
        frame multiple times has low cost.

        time -- The time in the video to fetch the frame from.

        """
        # reset process if needed
        if (not self._last_frame or
            self._last_frame.start_time > time or
            self._last_frame.end_time + self._reset_threshold < time):
            self._setup_process(time)

        # fast-forward if needed
        while not self._last_frame.eof and self._last_frame.end_time < time:
            self._next_frame()

        return self._last_frame

    def get_frame(self, time):
        """Convenience method for fetching the pillow image for the given
        frame. If there is no frame at the given time None is
        returned.

        time -- The time in the video to fetch the frame from.

        """
        frame_info = self.get_frame_info(time)
        if frame_info.eof:
            return None
        return frame_info.image

    def _setup_video_info(self):
        """Reads video information through ffprobe."""
        cmd = [
            _FFPROBE_PATH,
            '-loglevel'       , '0',
            '-of'             , 'csv=print_section=0:item_sep=,', # output format
            '-select_streams' , 'v:0',
            '-show_entries'   , 'stream=r_frame_rate,width,height',
            self.filename
        ]

        result = subprocess.run(cmd, capture_output = True, text = True)

        # TODO how do you know what order the values are printed in?
        # Maybe use json format for this instead and parse properly.
        w, h, f = result.stdout.split(',')
        n, d = f.split('/')

        self.size = (int(w), int(h))
        self.fps = int(n) / int(d)
        self._frame_size = self.size[0] * self.size[1] * 3
        self._frame_time = 1 / self.fps

    def _setup_process(self, start_time):
        """Starts the underlaying ffmpeg process to fetch data from the video
        file. If there's currently a process it will be terminated
        first.

        start_time -- The point in the video to start reading data.

        """
        if self._process:
            self.close()

        if not os.path.exists(self.filename):
            raise Exception(f"Video file does not exist: {self.filename}")

        if self._frame_size is None:
            self._setup_video_info()

        cmd = [
            _FFMPEG_PATH,
            '-loglevel', 'quiet',

            # input video
            '-ss' , "%.5f" % start_time, # start time
            '-i'  , self.filename,

            # output video
            '-f'       , 'rawvideo', # video format
            '-pix_fmt' , 'rgb24',    # pixel format
            '-codec:v' , 'rawvideo', # video codec
            '-'        ,             # stdout

            # TODO '-ss' here to trim output?
        ]

        self._process = subprocess.Popen(cmd,
                                         bufsize = self._frame_size,
                                         stdout = subprocess.PIPE,
                                         #stderr = subprocess.PIPE,
                                         stdin = subprocess.DEVNULL)
        self._next_frame(start_time)

    def _next_frame(self, time=None):
        """Advances to the next frame by reading it from the ffmpeg process
        output. This sets up the self._last_frame to contain the next
        frame.

        If there is no more data to read _last_frame will be populated
        and the eof attribute will be True.

        time -- Indicates the time to use for the frame. Not the time
        for the frame you want but the time that will be used for the
        next frame. If time is not given the last frame will be used
        to figure out this frames time.

        """
        frame = FrameInfo()

        if time is not None:
            n = int(time / self._frame_time)
            frame.start_time = n * self._frame_time
            frame.end_time = frame.start_time + self._frame_time
        elif self._last_frame:
            frame.start_time = self._last_frame.end_time
            frame.end_time = frame.start_time + self._frame_time
        else:
            raise Exception("Unable to set frame time")

        frame_bytes = self._process.stdout.read(self._frame_size)

        if len(frame_bytes) == 0:
            frame.eof = True
            self._last_frame = frame
            return

        if len(frame_bytes) != self._frame_size:
            raise Exception(f"Expected {self._frame_size} bytes for frame but got {len(frame_bytes)} from '{self.filename}'")

        frame.image = PIL.Image.frombytes("RGB", self.size, frame_bytes)
        frame.image = frame.image.convert("RGBA")
        self._last_frame = frame

    def close(self):
        if self._process:
            self._process.stdout.close()
            # TODO close things right self._process.terminate()
            self._process.wait()
            self._process = None
        self._last_frame = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class Ffprobe:
    def __init__(self, filename):
        self.filename = filename
        self.width = None
        self.height = None
        self.size = None
        self.fps = None
        self.fps_exact = None
        self.duration = None

        self._run()

    def _run(self):
        cmd = [
            _FFPROBE_PATH,
            '-i', self.filename,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            '-hide_banner',
        ]

        result = subprocess.run(cmd, capture_output = True, text = True)
        if result is None or result.stdout is None:
            logger.debug("ffprobe failed for: %s" % self.filename)
        else:
            data = json.loads(result.stdout)

            for stream in data['streams']:
                if stream['codec_type'] == 'video':
                    self.width = int(stream['width'])
                    self.height = int(stream['height'])
                    self.size = (self.width, self.height)

                    n, d = stream['r_frame_rate'].split('/')
                    self.fps_exact = (int(n), int(d))
                    self.fps = self.fps_exact[0] / self.fps_exact[1]

                    break

            self.duration = float(data['format']['duration'])

class FrameInfo:
    def __init__(self):
        self.image = None
        self.start_time = 0
        self.end_time = 0
        self.eof = False

def get_video_formats():
    """Returns a dict of {<file ending>: <format name>} for formats
    supported by ffmpeg. File endings are lowercase. Supported formats
    may vary between ffmpeg versions.

    """
    cmd = [_FFMPEG_PATH, '-formats', '-v', 'quiet']
    result = subprocess.run(cmd, capture_output = True, text = True)
    lines = result.stdout.split("\n")
    lines = lines[5:]

    result = {}

    for row in lines:
        # demuxers that are not devices
        if row and row[1] == "D" and row[3] != "d":
            fmt, name = row[5:].split(" ", 1)

            for fmt_entry in fmt.split(","):
                result[fmt_entry.strip().lower()] = name.strip()

    return result

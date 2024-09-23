import kmvid.data.clip as clip
import kmvid.data.state as state

import os
import os.path
import unittest

import PIL.Image
import PIL.ImageChops

_initialized = False
_generate_test_data = False

_root_path = "test-resources"
_error_path = "test-errors"
_test_images = set()

def _verify_image(test_obj, tc_id, image):
    global _generate_test_data
    global _initialized
    global _test_images

    # first time initialization

    if not _initialized:
        os.makedirs(_root_path, exist_ok=True)
        os.makedirs(_error_path, exist_ok=True)

        _test_images = set()
        for fn in os.listdir(_root_path):
            _test_images.add(os.path.join(_root_path, fn))

        for fn in os.listdir(_error_path):
            if fn.endswith('.png'):
                os.remove(os.path.join(_error_path, fn))

        _initialized = True

    # setup

    filename = _get_tc_filename(test_obj, tc_id)

    report_name = f"[{test_obj.__module__}, {test_obj.__class__.__name__}"
    for x in [tc_id] if isinstance(tc_id, str) else [str(x) for x in tc_id]:
        report_name += ", " + str(x)
    report_name += "]"

    _test_images.discard(os.path.join(_root_path, filename))

    # test

    if _generate_test_data:
        path = os.path.join(_root_path, filename)
        if not os.path.exists(path):
            image.save(path)
        return True

    else:
        with PIL.Image.open(os.path.join(_root_path, filename)) as expected:
            if expected.size != image.size:
                raise AssertionError(
                    f"{report_name} image size mismatch {expected.size} vs {image.size}")

            diff = PIL.ImageChops.difference(image, expected)
            bbox = diff.getbbox()
            if bbox is not None:
                error_image = _make_error_image(expected, diff, image)
                error_image.save(os.path.join(_error_path, filename))

                raise AssertionError(f"{report_name} image mismatch with {os.path.join(_error_path, filename)}")

            return True

def _make_error_image(expected, diff, actual):
    w, h = expected.size
    img = PIL.Image.new("RGB", (w * 3, h))
    img.paste(expected)
    img.paste(diff, box=(w, 0))
    img.paste(actual, box=(w*2, 0))

    return img

def _get_tc_filename(test_obj, tc_id):
    id = None
    if isinstance(tc_id, (str, int, bool)):
        id = str(tc_id)
    elif isinstance(tc_id, (list, tuple)):
        for x in tc_id:
            if len(id) == 0:
                id = str(x)
            else:
                id += "_" + str(x)
    else:
        raise Exception(f"Unknown tc id type for: {tc_id}")

    return f"{test_obj.__module__}__{test_obj.__class__.__name__}__{id}.png"

class Testbase(unittest.TestCase):
    def assertImage(self, tc_id, image_or_clip):
        image = image_or_clip
        if isinstance(image_or_clip, clip.Clip):
            with state.State():
                render = image_or_clip.get_frame()
                image = render.image

        self.assertTrue(_verify_image(self, tc_id, image))

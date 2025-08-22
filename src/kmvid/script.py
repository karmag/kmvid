import kmvid.data.effect
import kmvid.data.variable
import kmvid.data.project
import kmvid.data.resource
import kmvid.data.text

import PIL.ImageColor

Val = kmvid.data.variable.make_val
Project = kmvid.data.project.Project

def Clip(file_or_color, **kwargs):
    clip_kws, res_kws = kmvid.data.clip.Clip.split_kwargs(kwargs)

    res = None

    try:
        if isinstance(file_or_color, str):
            color = PIL.ImageColor.getrgb(file_or_color)
            res = kmvid.data.resource.ColorResource(color = color, **res_kws)
        else:
            res = kmvid.data.resource.ColorResource(color = file_or_color, **res_kws)
    except ValueError:
        res = kmvid.data.resource.from_file(file_or_color, **res_kws)

    clip = kmvid.data.clip.Clip(res, **clip_kws)

    return clip

Pos = kmvid.data.effect.Pos
Resize = kmvid.data.effect.Resize
Rotate = kmvid.data.effect.Rotate
Fade = kmvid.data.effect.Fade
Crop = kmvid.data.effect.Crop
Draw = kmvid.data.effect.Draw
Border = kmvid.data.effect.Border
BorderCorner = kmvid.data.effect.BorderCorner
AlphaShape = kmvid.data.effect.AlphaShape
Blur = kmvid.data.effect.Blur

"""Photodiode patch helpers for RPG visual stimuli.

The visual tasks display pre-built RPG grating files. These helpers keep the
task interface unchanged while adding a fixed photodiode square to the pixels:
white during visual stimulation and black during the gray no-stimulus period.
"""

import hashlib
import os
import struct
import tempfile


PHOTODIODE_SIZE_PX = 120
PHOTODIODE_MARGIN_PX = 0
PHOTODIODE_ON_COLOR = (255, 255, 255)
PHOTODIODE_OFF_COLOR = (0, 0, 0)
PHOTODIODE_OFF_RAW_FRAMES = 2

_GRATING_HEADER_FORMAT = "<8H"
_GRATING_HEADER_SIZE = struct.calcsize(_GRATING_HEADER_FORMAT)
_CACHE_DIR = os.path.join(tempfile.gettempdir(), "rpi_behavior_boxes_photodiode")


def _ensure_cache_dir():
    """Return the cache directory path, creating it if needed.

    Inputs
    ------
    None.

    Returns
    -------
    str
        Absolute directory path in the system temporary directory. No physical
        units or array shape conventions apply.
    """
    if not os.path.isdir(_CACHE_DIR):
        os.makedirs(_CACHE_DIR)
    return _CACHE_DIR


def _rgb565(color):
    """Convert an RGB color triplet to RPG's 16-bit RGB565 integer format.

    Inputs
    ------
    color : tuple[int, int, int], shape (3,)
        Red, green, and blue values in 8-bit screen intensity units, 0-255.

    Returns
    -------
    int
        Packed 16-bit RGB565 pixel value.
    """
    red, green, blue = color
    return (((31 * (red + 4)) // 255) << 11) | (((63 * (green + 2)) // 255) << 5) | ((31 * (blue + 4)) // 255)


def _pixel_bytes(color, pixel_size):
    """Return one pixel encoded for an RPG grating file.

    Inputs
    ------
    color : tuple[int, int, int], shape (3,)
        Red, green, and blue values in 8-bit screen intensity units, 0-255.
    pixel_size : int, bytes/pixel
        RPG pixel width. Supported values are 2 for RGB565 and 3 for RGB888.

    Returns
    -------
    bytes
        Encoded bytes for exactly one pixel.
    """
    if pixel_size == 2:
        return struct.pack("<H", _rgb565(color))
    if pixel_size == 3:
        return bytes(bytearray(color))
    raise ValueError("Unsupported pixel size: " + str(pixel_size))


def read_grating_info(grating_file):
    """Return width, height, frame counts, and pixel size for an RPG grating.

    Inputs
    ------
    grating_file : str
        Path to an RPG grating file. ``~`` is expanded. The file is expected to
        use the RPG grating header followed by row-major frame pixels.

    Returns
    -------
    dict
        Keys are ``frames_per_cycle`` (int, frames), ``n_frames`` (int, frames),
        ``width`` (int, pixels), ``height`` (int, pixels), and ``pixel_size``
        (int, bytes/pixel). Frame arrays are stored row-major as
        ``(height, width)`` pixels per frame.
    """
    grating_file = os.path.expanduser(grating_file)
    with open(grating_file, "rb") as handle:
        header_bytes = handle.read(_GRATING_HEADER_SIZE)
    if len(header_bytes) != _GRATING_HEADER_SIZE:
        raise ValueError("Grating file is too small: " + grating_file)

    header = struct.unpack(_GRATING_HEADER_FORMAT, header_bytes)
    frames_per_cycle = header[0]
    n_frames = header[4]
    width = header[5]
    height = header[6]
    if frames_per_cycle <= 0 or width <= 0 or height <= 0:
        raise ValueError("Invalid RPG grating header: " + grating_file)

    data_bytes = os.path.getsize(grating_file) - _GRATING_HEADER_SIZE
    pixels_per_cycle = frames_per_cycle * width * height
    if pixels_per_cycle <= 0 or data_bytes % pixels_per_cycle != 0:
        raise ValueError("Unexpected RPG grating size: " + grating_file)
    pixel_size = data_bytes // pixels_per_cycle
    if pixel_size not in (2, 3):
        raise ValueError("Unsupported RPG grating pixel size: " + str(pixel_size))

    return {
        "frames_per_cycle": frames_per_cycle,
        "n_frames": n_frames,
        "width": width,
        "height": height,
        "pixel_size": pixel_size,
    }


def _cache_key(path, stat_result, extra):
    """Return a cache key tied to a source file and photodiode settings.

    Inputs
    ------
    path : str
        Source file path.
    stat_result : os.stat_result
        Metadata for ``path`` containing size and modification time.
    extra : str
        Additional cache identity string describing patch settings.

    Returns
    -------
    str
        SHA1 hexadecimal digest string.
    """
    digest = hashlib.sha1()
    digest.update(os.path.abspath(path).encode("utf-8"))
    digest.update(str(stat_result.st_size).encode("ascii"))
    digest.update(str(stat_result.st_mtime).encode("ascii"))
    digest.update(extra.encode("ascii"))
    return digest.hexdigest()


def _patch_bounds(width, height):
    """Return top-right photodiode square bounds for a frame.

    Inputs
    ------
    width : int, pixels
        Frame width.
    height : int, pixels
        Frame height.

    Returns
    -------
    tuple[int, int, int, int]
        ``(left, top, right, bottom)`` pixel bounds in row-major image
        coordinates. The right and bottom bounds are exclusive.
    """
    size = min(PHOTODIODE_SIZE_PX, width, height)
    left = max(0, width - size - PHOTODIODE_MARGIN_PX)
    top = max(0, PHOTODIODE_MARGIN_PX)
    right = min(width, left + size)
    bottom = min(height, top + size)
    return left, top, right, bottom


def patched_grating_path(grating_file):
    """Create or reuse a patched RPG grating with a white top-right square.

    Inputs
    ------
    grating_file : str
        Path to an RPG grating file. Frames are interpreted as row-major arrays
        with shape ``(height, width)`` and units of screen pixels.

    Returns
    -------
    str
        Path to a cached RPG grating file with the photodiode square set to
        white in every stored frame. The source grating is not modified.
    """
    grating_file = os.path.expanduser(grating_file)
    info = read_grating_info(grating_file)
    stat_result = os.stat(grating_file)
    extra = "on:{0}:{1}:{2}:{3}".format(
        PHOTODIODE_SIZE_PX,
        PHOTODIODE_MARGIN_PX,
        PHOTODIODE_ON_COLOR,
        info["pixel_size"],
    )
    filename = os.path.basename(grating_file) + "." + _cache_key(grating_file, stat_result, extra) + ".photodiode"
    output_path = os.path.join(_ensure_cache_dir(), filename)
    if os.path.exists(output_path):
        return output_path

    with open(grating_file, "rb") as handle:
        patched = bytearray(handle.read())

    left, top, right, bottom = _patch_bounds(info["width"], info["height"])
    pixel_size = info["pixel_size"]
    pixel = _pixel_bytes(PHOTODIODE_ON_COLOR, pixel_size)
    patch_row = pixel * (right - left)
    frame_stride = info["width"] * info["height"] * pixel_size

    for frame_index in range(info["frames_per_cycle"]):
        frame_start = _GRATING_HEADER_SIZE + frame_index * frame_stride
        for y_pos in range(top, bottom):
            row_start = frame_start + ((y_pos * info["width"] + left) * pixel_size)
            row_end = row_start + len(patch_row)
            patched[row_start:row_end] = patch_row

    with open(output_path, "wb") as handle:
        handle.write(patched)
    return output_path


def screen_args_for_grating(grating_file, gray_level):
    """Return RPG Screen keyword arguments matching an existing grating file.

    Inputs
    ------
    grating_file : str
        Path to an RPG grating file.
    gray_level : int
        Screen background intensity, 0-255.

    Returns
    -------
    dict
        Keyword arguments for ``rpg.Screen``: ``resolution`` as ``(width,
        height)`` in pixels, ``background`` as intensity 0-255, and
        ``colormode`` as 16 or 24 bits/pixel.
    """
    info = read_grating_info(grating_file)
    colormode = 24 if info["pixel_size"] == 3 else 16
    return {
        "resolution": (info["width"], info["height"]),
        "background": gray_level,
        "colormode": colormode,
    }


def _raw_colormode_for_screen(screen):
    """Return RPG raw colormode for an existing screen object.

    Inputs
    ------
    screen : object
        RPG Screen-like object exposing ``colormode``. RPG uses ``2`` for
        RGB888 and ``0`` for RGB565.

    Returns
    -------
    int
        Raw conversion color mode, either 16 or 24 bits/pixel.
    """
    return 24 if getattr(screen, "colormode", 0) == 2 else 16


def write_photodiode_off_rgb_frame(path, width, height, gray_level):
    """Write one RGB888 gray frame with a black top-right photodiode square.

    Inputs
    ------
    path : str
        Output path for raw RGB bytes. The file contains no header.
    width : int, pixels
        Frame width.
    height : int, pixels
        Frame height.
    gray_level : int
        Background intensity, 0-255.

    Returns
    -------
    None
        Writes row-major RGB bytes with shape ``(height, width, 3)`` and
        intensity units 0-255.
    """
    left, top, right, bottom = _patch_bounds(width, height)
    background = bytes(bytearray((gray_level, gray_level, gray_level)))
    off_pixel = bytes(bytearray(PHOTODIODE_OFF_COLOR))
    with open(path, "wb") as handle:
        for y_pos in range(height):
            if top <= y_pos < bottom:
                handle.write(background * left)
                handle.write(off_pixel * (right - left))
                handle.write(background * (width - right))
            else:
                handle.write(background * width)


def load_photodiode_off_raw(screen, rpg_module, width, height, gray_level):
    """Load a gray RPG raw stimulus with a black photodiode square.

    Inputs
    ------
    screen : object
        RPG Screen-like object exposing ``colormode`` and ``load_raw(path)``.
    rpg_module : module-like object
        RPG module exposing ``convert_raw(input, output, n_frames, width,
        height, refreshes_per_frame, colormode)``.
    width : int, pixels
        Frame width.
    height : int, pixels
        Frame height.
    gray_level : int
        Background intensity, 0-255.

    Returns
    -------
    object
        RPG Raw-like object returned by ``screen.load_raw``. The cached raw
        contains two identical frames, each with shape ``(height, width)`` in
        screen pixels, so RPG can compute an inter-frame timing interval.
    """
    colormode = _raw_colormode_for_screen(screen)
    extra = "off:{0}:{1}:{2}:{3}:{4}:{5}:{6}".format(
        width,
        height,
        gray_level,
        colormode,
        PHOTODIODE_SIZE_PX,
        PHOTODIODE_MARGIN_PX,
        PHOTODIODE_OFF_COLOR,
        PHOTODIODE_OFF_RAW_FRAMES,
    )
    cache_name = hashlib.sha1(extra.encode("ascii")).hexdigest()
    cache_dir = _ensure_cache_dir()
    rgb_path = os.path.join(cache_dir, cache_name + ".rgb")
    raw_path = os.path.join(cache_dir, cache_name + ".raw")

    if not os.path.exists(raw_path):
        write_photodiode_off_rgb_frame(rgb_path, width, height, gray_level)
        with open(rgb_path, "rb") as handle:
            one_frame = handle.read()
        with open(rgb_path, "ab") as handle:
            handle.write(one_frame)
        rpg_module.convert_raw(rgb_path, raw_path, PHOTODIODE_OFF_RAW_FRAMES, width, height, 1, colormode)

    return screen.load_raw(raw_path)

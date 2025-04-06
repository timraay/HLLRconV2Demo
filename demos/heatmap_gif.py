import multiprocessing
import os
from pathlib import Path
import sys
from typing import NamedTuple
from PIL import Image
import imagequant
import numpy as np
import matplotlib.pyplot as plt

DATA_DIR = Path("data/positions/")
TACMAP_DIR = Path("assets/tacmaps/")

SECONDS_PASSED_PER_FRAME = 4
TIME_WINDOW_SECONDS = 60
TIME_SCALE = 60
PLOT_SCALE = 8
MAX_NUM_FRAMES = 9999
NUM_PROCESSES = 10
BACKGROUND_COLORS = 40

class FrameArgs(NamedTuple):
    t: int
    data: np.ndarray
    img: Image.Image

def get_pretty_filesize(path: str):
    size_bytes = os.path.getsize(path)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

def get_frame(args: FrameArgs):
    (t, data, img) = args
    
    # Set up the plot
    fig, ax = plt.subplots(figsize=(PLOT_SCALE, PLOT_SCALE))
    plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)    
    
    # Select range from data
    filtered = data[(data["timestamp"] >= t - TIME_WINDOW_SECONDS) & (data["timestamp"] <= t)]

    # Split data on teams
    teams = (
        filtered[filtered["team_id"] == 1],
        filtered[filtered["team_id"] == 2],
    )

    # Display the image (ensure it's properly aligned)
    ax.set_facecolor("black")
    ax.imshow(img, extent=(-100000, 100000, -100000, 100000), aspect='auto')

    for team, color in zip(teams, ("#63ff00", "#ff3d00")):
        if (team.size == 0): continue
        alpha = (team["timestamp"] - (t - TIME_WINDOW_SECONDS)) * 0.1 / TIME_WINDOW_SECONDS
        ax.scatter(
            team["x"],
            team["y"],
            color=color,
            alpha=alpha, # type: ignore
            marker="o",
            s=np.full_like(team["x"], PLOT_SCALE * 0.06),
        )

    # Remove axes for a cleaner look
    ax.set_xticks([])
    ax.set_yticks([])

    # Convert to image
    fig.canvas.draw()
    im = Image.frombytes(
        'RGBA',
        fig.canvas.get_width_height(),
        fig.canvas.buffer_rgba() # type: ignore
    )
    plt.close(fig)
    return im

def quantize_background(im: Image.Image, max_colors: int, alpha: float = 0.15):
    # Modify alpha channel
    r, g, b, a = im.convert("RGBA").split()
    a = a.point(lambda p: int(p * alpha))
    im = Image.merge("RGBA", (r, g, b, a))

    # Composit onto black background
    composited = Image.new("RGBA", im.size, color=(0, 0, 0, 255))
    composited.alpha_composite(im)

    # Quantize image
    quantized_im = imagequant.quantize_pil_image(
        image=composited,
        dithering_level=1.0,
        max_colors=max_colors,
        min_quality=0,
        max_quality=100,
    )

    # Extract colors from palette
    palette = quantized_im.palette
    assert palette is not None
    quantized_palette = list(palette.getdata()[1])

    # Convert from RGBA to RGB
    quantized_palette = [
        x
        for i, x in enumerate(quantized_palette[:max_colors*4])
        if (i + 1) % 4 != 0
    ]

    return quantized_im, quantized_palette

def quantize_images(ims: list[Image.Image], max_colors: int):
    # Stack images into same canvas
    stacked_im = Image.new("RGB", (ims[0].width, ims[0].height * len(ims)))
    for i, im in enumerate(ims):
        stacked_im.paste(im, (0, ims[0].height * i))
    
    # Quantize image
    stacked_im = stacked_im.quantize(
        colors=max_colors,
        method=Image.Quantize.MAXCOVERAGE,
        dither=Image.Dither.NONE,
    )

    # Get palette
    palette = stacked_im.palette
    assert palette is not None
    stacked_im.close()

    # Extract colors from palette
    return list(palette.getdata()[1])[:max_colors*3]

def main():
    if len(sys.argv) < 3:
        print("Missing parameter. Please provide the name of a map (as seen in `/assets/tacmaps/`).")
        return

    if len(sys.argv) < 4:
        print("Missing parameter. Please provide the name of a CSV file inside of `/data/positions/`.")
        return
    
    tacmap_fn = sys.argv[2]
    if not tacmap_fn.lower().endswith('.png'):
        tacmap_fn += ".png"
    tacmap_fp = TACMAP_DIR / Path(tacmap_fn)
    if not tacmap_fp.exists():
        print("File \"%s\" does not exist" % tacmap_fp)
        return
    
    data_fn = sys.argv[3]
    if not data_fn.lower().endswith('.csv'):
        data_fn += ".csv"
    data_fp = DATA_DIR / Path(data_fn)
    if not data_fp.exists():
        print("File \"%s\" does not exist" % data_fp)
        return
    
    # Load the background image (should be 1:1 in aspect ratio)
    background_im, background_palette = quantize_background(
        Image.open(tacmap_fp),
        max_colors=BACKGROUND_COLORS
    )

    # Read data
    data = np.genfromtxt(data_fp, delimiter=",", encoding="utf-8", names=True)
    data["y"] *= -1

    t_min = np.min(data["timestamp"])
    t_max = np.max(data["timestamp"])
    num_frames = min(int((t_max - t_min) // SECONDS_PASSED_PER_FRAME), MAX_NUM_FRAMES)
    print("Num frames:", num_frames)

    with multiprocessing.Pool(NUM_PROCESSES) as p:
        ts = [
            FrameArgs(t_min + 80 + i * SECONDS_PASSED_PER_FRAME, data, background_im)
            for i in range(num_frames)
        ]
        ims = p.map(get_frame, ts)

    print("Optimizing palette...")
    output_palette = quantize_images(ims, max_colors=256 - BACKGROUND_COLORS)
    palette_im = Image.new("P", ims[0].size)
    palette_im.putpalette(background_palette + output_palette, rawmode="RGB")
    
    print("Quantizing frames...")
    for i, im in enumerate(ims):
        quantized = im.convert("RGB").quantize(
            palette=palette_im,
            dither=Image.Dither.NONE,
        )
        im.close()
        ims[i] = quantized

    print("Saving GIF...")
    ims[0].save(
        fp="out.gif",
        palette=palette_im,
        save_all=True,
        append_images=ims[1:],
        duration=(SECONDS_PASSED_PER_FRAME / TIME_SCALE) * 1000,
        optimize=True,
        loop=0,
    )

    print(get_pretty_filesize("out.gif"))

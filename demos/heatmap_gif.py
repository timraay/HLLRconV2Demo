import multiprocessing
from pathlib import Path
import sys
from typing import NamedTuple
from PIL import Image, GifImagePlugin
import numpy as np
import matplotlib.pyplot as plt

GifImagePlugin.LOADING_STRATEGY = GifImagePlugin.LoadingStrategy.RGB_ALWAYS

DATA_DIR = Path("data/positions/")
TACMAP_DIR = Path("assets/tacmaps/")

SECONDS_PASSED_PER_FRAME = 4
TIME_WINDOW_SECONDS = 60
TIME_SCALE = 60
PLOT_SCALE = 8
MAX_NUM_FRAMES = 9999
NUM_PROCESSES = 10

class FrameArgs(NamedTuple):
    t: int
    data: np.ndarray
    img: Image.Image

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
    ax.imshow(img, extent=(-100000, 100000, -100000, 100000), aspect='auto', alpha=0.15)

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

    fig.canvas.draw()
    im = Image.frombytes(
        'RGBA',
        fig.canvas.get_width_height(),
        fig.canvas.buffer_rgba() # type: ignore
    )
    plt.close(fig)
    return im

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
    img = Image.open(tacmap_fp).convert("RGBA")

    # Read data
    data = np.genfromtxt(data_fp, delimiter=",", encoding="utf-8", names=True)
    data["y"] *= -1

    t_min = np.min(data["timestamp"])
    t_max = np.max(data["timestamp"])
    num_frames = min(int((t_max - t_min) // SECONDS_PASSED_PER_FRAME), MAX_NUM_FRAMES)
    print("Num frames:", num_frames)

    with multiprocessing.Pool(NUM_PROCESSES) as p:
        ts = [
            FrameArgs(t_min + 80 + i * SECONDS_PASSED_PER_FRAME, data, img)
            for i in range(num_frames)
        ]
        ims = p.map(get_frame, ts)

    # ims: list[Image.Image] = []
    # for i in range(num_frames):
    #     print(i)
    #     t = t_min + 80 + i * SECONDS_PASSED_PER_FRAME
    #     im = get_frame(FrameArgs(t, data, img))
    #     im.save(f"frame{i}.png")
    #     ims.append(im.convert("RGBA"))
    
    print("saving...")
    ims[0].save(
        fp="out.gif",
        save_all=True,
        append_images=ims[1:],
        duration=(SECONDS_PASSED_PER_FRAME / TIME_SCALE) * 1000,
        optimize=True,
        loop=0,
    )

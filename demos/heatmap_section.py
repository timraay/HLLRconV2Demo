from pathlib import Path
from PIL import Image
import sys
import numpy as np
import matplotlib.pyplot as plt

DATA_DIR = Path("data/positions/")
TACMAP_DIR = Path("assets/tacmaps/")

MAP_CENTER = (60000, 35000)
MAP_RADIUS = 35000
SECONDS_RANGE = (0, 300 * 60)

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
    img = Image.open(tacmap_fp)
    img_radius = (
        img.size[0] * MAP_RADIUS // 200000,
        img.size[1] * MAP_RADIUS // 200000,
    )
    img_center = (
        (img.size[0] * (MAP_CENTER[0] + 100000) // 200000),
        (img.size[1] * (MAP_CENTER[1] + 100000) // 200000),
    )
    img = img.crop((
        img_center[0] - img_radius[0],
        img_center[1] - img_radius[1],
        img_center[0] + img_radius[0],
        img_center[1] + img_radius[1],
    ))

    # Read data
    data = np.genfromtxt(data_fp, delimiter=",", encoding="utf-8", names=True)
    t_min = np.min(data["timestamp"])
    data["x"] -= MAP_CENTER[0]
    data["y"] -= MAP_CENTER[1]
    filtered = data[
        (data["x"] >= -MAP_RADIUS) &
        (data["x"] <= MAP_RADIUS) &
        (data["y"] >= -MAP_RADIUS) &
        (data["y"] <= MAP_RADIUS) &
        (data["timestamp"] >= SECONDS_RANGE[0] + t_min) &
        (data["timestamp"] <= SECONDS_RANGE[1] + t_min)
    ]
    filtered["y"] *= -1
    teams = (
        filtered[filtered["team_id"] == 1],
        filtered[filtered["team_id"] == 2],
    )

    # Set up the plot
    fig, ax = plt.subplots(figsize=(12, 12))
    plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)

    # Display the image (ensure it's properly aligned)
    
    ax.set_facecolor("black")
    ax.imshow(
        img,
        extent=(
            -MAP_RADIUS,
            MAP_RADIUS,
            -MAP_RADIUS,
            MAP_RADIUS,
        ),
        # extent=(-100000, 100000, -100000, 100000),
        aspect='auto',
        alpha=0.15,
    )

    for team, color in zip(teams, ("#63ff00", "#ff3d00")):
        ax.scatter(team["x"], team["y"], color=color, alpha=0.03, marker="o", s=2)

    # Remove axes for a cleaner look
    ax.set_xticks([])
    ax.set_yticks([])

    plt.axis("equal") # Lock aspect ratio
    plt.show()

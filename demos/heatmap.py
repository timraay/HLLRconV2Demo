from pathlib import Path
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

DATA_DIR = Path("data/positions/")
TACMAP_DIR = Path("assets/tacmaps/")

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
    img = mpimg.imread(tacmap_fp)

    # Read data
    data = np.genfromtxt(data_fp, delimiter=",", encoding="utf-8", names=True)
    data["y"] *= -1
    teams = (
        data[data["team_id"] == 1],
        data[data["team_id"] == 2],
    )

    # Set up the plot
    fig, ax = plt.subplots(figsize=(12, 12))
    plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)

    # Display the image (ensure it's properly aligned)
    ax.set_facecolor("black")
    ax.imshow(img, extent=(-100000, 100000, -100000, 100000), aspect='auto', alpha=0.15)

    # Overlay KDE heatmap
    # cmap="rocket", cmap="mako"
    # sns.kdeplot(
    #     x=x,
    #     y=y,
    #     cmap="mako",
    #     fill=True,
    #     thresh=0.1,
    #     alpha=0.5,
    #     common_norm=True,
    #     gridsize=200,
    #     ax=ax,
    #     bw_adjust=0.1,
    #     levels=10,
    # )

    for team, color in zip(teams, ("#63ff00", "#ff3d00")):
        ax.scatter(team["x"], team["y"], color=color, alpha=0.01, marker="o", s=np.full_like(team["x"], 1))
        ax.scatter(team["x"], team["y"], color=color, alpha=0.01, marker="o", s=np.full_like(team["x"], 1))

    # Remove axes for a cleaner look
    ax.set_xticks([])
    ax.set_yticks([])

    plt.axis("equal") # Lock aspect ratio
    plt.show()

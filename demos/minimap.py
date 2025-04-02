import asyncio
from pathlib import Path
from PIL import Image, ImageTk
import threading
import tkinter as tk

from lib.rcon import Rcon
from lib.constants import RCON_HOST, RCON_PASSWORD, RCON_PORT
from lib.exceptions import HLLError

TACMAP_PATH = Path("assets/tacmap.png")

def get_oval_coords(x: float, y: float) -> tuple[float, float, float, float]:
    radius = 7
    return (x - radius, y - radius, x + radius, y + radius)

class Minimap(tk.Frame):
    def __init__(self, master, *pargs):
        super().__init__(master, *pargs)

        self.image = Image.open(TACMAP_PATH)

        self.background_image = ImageTk.PhotoImage(self.image.copy())

        self.canvas = tk.Canvas(master, border=2, background="black")
        self.canvas.grid()

        self.image_id = self.canvas.create_image((self.canvas.size()[0] // 2, self.canvas.size()[0] // 2), image=self.background_image)
        self.pos_id = self.canvas.create_oval(*get_oval_coords(15, 15), fill="orange")
        self.pos_offset = (0, 0)
        
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        self.canvas.bind('<Configure>', self._resize_image)

    def _resize_image(self, event):
        window_width: int = event.width - 8
        window_height: int = event.height - 8

        self.canvas.configure(width=window_width, height=window_height)
        self._redraw_image()
        self._redraw_pos()
    
    def _redraw_image(self):
        wg_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        im_size = min(wg_size)
        
        image = self.image.resize((im_size, im_size))
        self.background_image = ImageTk.PhotoImage(image)

        self.canvas.itemconfig(self.image_id, image=self.background_image)
        self.canvas.coords(self.image_id, wg_size[0] / 2, wg_size[1] / 2)

    def _redraw_pos(self):
        wg_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        im_size = min(wg_size)
        im_origin = (
            (wg_size[0] - im_size) / 2,
            (wg_size[1] - im_size) / 2,
        )
        
        self.canvas.coords(self.pos_id, *get_oval_coords(
            im_origin[0] + self.pos_offset[0] * im_size,
            im_origin[1] + self.pos_offset[1] * im_size,
        ))

    def set_position(self, x: float, y: float):
        self.pos_offset = (x, y)
        self._redraw_pos()

class RconThread(threading.Thread):
    def __init__(self, minimap: Minimap, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.minimap = minimap

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        rcon = Rcon(
            host=RCON_HOST,
            port=RCON_PORT,
            password=RCON_PASSWORD,
        )
        rcon.start()
        await rcon.wait_until_connected(timeout=10)

        while True:
            try:
                resp = await rcon.commands.get_players()
            except (HLLError, asyncio.TimeoutError):
                pass
            else:
                players = resp["players"]
                if players:
                    world_origin = (-100000, -100000)
                    world_size = (200000, 200000)
                    pos = players[0]["worldPosition"]
                    self.minimap.set_position(
                        (pos["x"] - world_origin[0]) / world_size[0],
                        (pos["y"] - world_origin[1]) / world_size[1],
                    )

def main():
    root = tk.Tk()
    tacmap = Minimap(root)
    tacmap.pack(fill="both", expand=True)

    thread = RconThread(tacmap)
    thread.daemon = True
    thread.start()

    try:
        root.mainloop()
    except KeyboardInterrupt:
        return

# HLL RCON v2 demos

An implementation of the version 2 RCON protocol for Hell Let Loose, with examples.

## How to run

1. Clone the repository.
2. Create a `.env` file defining `RCON_HOST`, `RCON_PORT` and `RCON_PASSWORD`.
3. Run `python main.py <demo>`, with `<demo>` being one of the filenames in the `/demos/` folder.

## Available demos

| Name | Description |
|-|-|
| `basic` | Basic example of how to use this implementation.
| `protocol` | A lower-level version of the `basic` demo.
| `stress` | A test that attempts to execute 1000 commands concurrently.
| `stress_pooled` | The same test as `stress` but using a pool of 10 connections.
| `reconnect` | Demonstration of the demo client's ability to automatically reconnect.
| `minimap` | Opens a separate window showing the live position of a player on the map. Currently assumes the map is SME and only supports one player at a time.
| `capture_position_data` | Start polling player positions on the server and save it to a CSV file.
| `heatmap` | Generate a heatmap from a player positions CSV. Requires 2 extra parameters: The name of the map as seen in `/assets/tacmaps/`, and the name of the CSV file as seen in `/data/positions/`.
| `heatmap_gif` | The same as `heatmap` but generates a GIF that shows player movements over time.
| `heatmap_section` | The same as `heatmap` but has some extra (currently hardcoded) to zoom in on a specific section of the map.

## Polling player positions on multiple servers at once

To connect to multiple servers at once and start polling them for player positions, you can do the following:

1. Open `capture_data.py` in a text editor.
2. Update `args` with as many servers as desired, then save.
3. Run `python capture_data.py`.

# HLL RCON v2 demos

An implementation of the version 2 RCON protocol for Hell Let Loose, with examples.

## How to run

1. Clone the repository.
2. Create a `.env` file defining `RCON_HOST`, `RCON_PORT` and `RCON_PASSWORD`.
3. Run `python main.py <demo>`, with `<demo>` being one of the filenames in the `/demos/` folder.

## Available demos

| Name | Description |
|-|-|
| `basic` | Basic example of how to use this protocol implementation.
| `minimap` | Opens a separate window showing the live position of a player on the map. Currently assumes the map is SME and only supports one player at a time.
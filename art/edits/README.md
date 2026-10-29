# Hand-cleaned map art

Blizzard's map art has sea names ("The Great Sea"), continent names and the odd compass
baked into it. Where OpenMap shows that art somewhere Blizzard's map never did (zoomed
into the sea, between continents), the lettering gets in the way. This folder is for
cleaning it out by hand.

1. `python -P tools/map-art/export.py <db2 dir> <texture cache>` writes `source/`: the
   world map, both continents, and every zone map with sea, as full-size PNGs
   (1002 × 668, the client's own pixels). Not committed: re-export any time.
2. Copy the ones you're editing into `edited/`, **same file name, same size**, and paint
   out the lettering (keep everything else as it is: the coasts and islands must still
   line up).
3. `python -P tools/map-art/import.py <db2 dir> <texture cache>` compares each edited
   PNG with its source and writes only the 256-px tiles you changed to
   `OpenMap/Media/Textures/MapArt/`, listed in `OpenMap/Data/ArtEdits.lua`. The addon
   draws those tiles in place of the client's.
   The names come back as live lettering (`OpenMap/Data/Labels.lua`, measured from this
   art): one of each, fixed on the world, so they stay put as you zoom.
4. Restart the game (new textures need a full restart, not `/reload`).

Edits are of Blizzard's own art, and stay true to its style: they take out what's in the way
and add nothing the game's maps don't have.

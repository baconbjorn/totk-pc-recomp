# DevSpawnMenu

This is a safe dev-only mod scaffold for TotK Recomp.

The requested "press F2 to open a spawn menu and spawn swords/items" flow requires a verified in-game spawn hook. This repository does not currently include a safe, tested item-grant or actor-spawn implementation, so this mod intentionally stays inert and install-safe.

Intended layout:

- Place this folder in `mods/` next to `totk.exe`
- `mods/DevSpawnMenu/cheats/277178B7DBA1B6D4.txt` holds the cheat entry
- The folder is ready to grow into a real spawn-menu mod once a validated spawn path is added

This scaffold is intentionally non-invasive and keeps the game unchanged until a real implementation is available.

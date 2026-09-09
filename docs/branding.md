# Vimmite visual identity

Vimmite keeps Fedora/KDE's supported Breeze Dark components and adds a small,
replaceable identity layer. Users can still select another global theme, color
scheme, wallpaper, launcher icon, or terminal configuration normally.

## Palette

| Role | Hex | Use |
| --- | --- | --- |
| Graphite 950 | `#111218` | Deep backgrounds and terminal canvas |
| Graphite 900 | `#18191f` | Windows and alternate surfaces |
| Graphite 800 | `#24252d` | Controls, tabs, and inactive chrome |
| Electric indigo | `#6366f1` | Selection, focus, and primary accent |
| Indigo highlight | `#818cf8` | Hover, links, and bright terminal blue |
| Vimmite gold | `#f6c453` | Identity, attention, cursor, and warm accent |
| Gold highlight | `#ffe08a` | High-contrast gold highlight |
| Frost | `#ebecef` | Primary text on graphite |

The installed `VimmiteGraphite.colors` scheme is derived from Breeze Dark's
semantic roles. Electric indigo is the interaction color; gold is intentionally
reserved for identity and attention so it remains distinctive.

## Installed assets

| Surface | Installed asset or setting |
| --- | --- |
| Desktop and installer/live session | `/usr/share/wallpapers/Vimmite/` |
| Lock screen and SDDM login | `/usr/share/wallpapers/VimmiteLock/` |
| Plasma global theme | `org.vimmite.desktop` (Vimmite Graphite) |
| Scalable brand mark | `/usr/share/icons/hicolor/scalable/apps/vimmite.svg` |
| Application launcher mark | `start-here-vimmite` |
| Fastfetch mark | `/usr/share/fastfetch/presets/vimmite.txt` |
| Kitty profile | `/etc/xdg/kitty/kitty.conf` |

The original supplied PNG artwork remains lossless in the image. The compass/V
logo is SVG so documentation and desktop surfaces can render it sharply at any
size. The wallpaper creator made the supplied artwork available for free use;
Vimmite uses it in this personal, noncommercial project under
`LicenseRef-Vimmite-Brand-Assets`. Reconfirm the creator's terms before any
commercial reuse.

## Behavior on upgrades

System files define defaults, not locked policy. New users and the installer
environment receive the complete identity. Existing users keep appearance keys
already stored in their home directory, while settings they have never
overridden continue to inherit the Vimmite defaults.

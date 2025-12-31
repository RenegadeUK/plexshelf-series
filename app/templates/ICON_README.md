# PlexShelf Favicon and Icon

- favicon.svg: SVG favicon for browser tabs
- favicon.ico: (to be generated) for legacy browser support
- icon-256.svg: 256x256 SVG icon for app use
- icon-256.png: (to be generated) 256x256 PNG icon for app use

To generate PNG/ICO from SVG, use ImageMagick:

    convert icon-256.svg icon-256.png
    convert favicon.svg favicon.ico

Or use an online converter if ImageMagick is not available.
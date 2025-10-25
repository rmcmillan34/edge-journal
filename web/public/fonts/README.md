Bundled Fonts (Nerd Fonts)

Place the patched Nerd Font TTFs you want to self-host in this folder.

Recommended files (used by the app):
- IosevkaNerdFont-Regular.ttf
- IosevkaNerdFont-Bold.ttf

Where to get them:
- Nerd Fonts releases: https://github.com/ryanoasis/nerd-fonts/releases (download the Iosevka package and extract the TTFs)

Licensing:
- Nerd Fonts redistributes patched fonts under their original licenses.
- Iosevka is licensed under the SIL Open Font License (OFL). Include the upstream license file (OFL.txt) alongside the fonts if available.

Notes:
- Large binaries increase repo size. If you prefer, use Git LFS for .ttf files.
- After adding files, the Next.js app will preload and serve them from /fonts.

# AXION Themes + Theme Creator Spec v1

## Products
- **Axion Themes** (theme manager)
- **Axion Theme Creator** (build/share themes)

## Theme elements
- Color palette (primary/accent/surface/state colors)
- Taskbar/start menu style profile
- Icon pack reference
- Wallpaper pack + rotation rules
- Sounds profile
- Cursor/font profile
- Motion profile (normal/reduced)

## Theme package format
- `.axtheme` signed package
- Includes `theme.json` + assets + preview images

## Theme Creator features
- live preview canvas (taskbar/start/settings/control panel)
- import wallpaper pack
- accent extraction from wallpaper
- save draft / export signed package
- accessibility validation (contrast checks)

## Marketplace
- free themes + low-cost premium themes
- clear install/uninstall + rollback

## Security
- theme packages sandbox-validated before install
- no executable payloads in theme packages

## v1 done
- user can apply theme in one click
- user can create/export/import theme package
- rollback to previous theme works instantly

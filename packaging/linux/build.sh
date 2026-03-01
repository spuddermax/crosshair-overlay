#!/bin/bash
set -e

VERSION="0.6.0"
PKG_NAME="crosshair-overlay"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build/${PKG_NAME}_${VERSION}_all"
OUTPUT="$SCRIPT_DIR/${PKG_NAME}_${VERSION}_all.deb"

echo "=== Building ${PKG_NAME} v${VERSION} .deb ==="

# Clean previous build
rm -rf "$SCRIPT_DIR/build"
rm -f "$OUTPUT"

# Create directory structure
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"

# Control file
cat > "$BUILD_DIR/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Depends: python3, python3-gi, gir1.2-gtk-3.0, gir1.2-appindicator3-0.1
Maintainer: spuddermax
Description: Crosshair overlay with pixel ruler and measure mode
 A lightweight full-screen crosshair overlay for Linux.
 Features include customizable crosshair lines, center dot,
 pixel ruler with tick marks, measure mode, and named presets.
EOF

# Conffiles
cat > "$BUILD_DIR/DEBIAN/conffiles" <<EOF
/usr/share/applications/${PKG_NAME}.desktop
EOF

# postinst
cat > "$BUILD_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e

chmod +x /usr/bin/crosshair-overlay
gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# postrm
cat > "$BUILD_DIR/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e

case "$1" in
    purge)
        # Remove autostart files for all users
        for home_dir in /home/*; do
            rm -f "$home_dir/.config/autostart/crosshair-overlay.desktop"
        done
        # Note: user config in ~/.config/crosshair-overlay/ is left to the user
        ;;
    remove|upgrade|failed-upgrade|abort-install|abort-upgrade|disappear)
        gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true
        ;;
esac
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postrm"

# Install the Python script as the binary
cp "$REPO_ROOT/linux/crosshair_overlay.py" "$BUILD_DIR/usr/bin/crosshair-overlay"
chmod 755 "$BUILD_DIR/usr/bin/crosshair-overlay"

# Desktop file and icon
cp "$SCRIPT_DIR/crosshair-overlay.desktop" "$BUILD_DIR/usr/share/applications/"
cp "$SCRIPT_DIR/crosshair-overlay.svg" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/"

# Build the .deb
dpkg-deb --build "$BUILD_DIR" "$OUTPUT"

# Clean up build dir
rm -rf "$SCRIPT_DIR/build"

echo ""
echo "=== Build complete ==="
echo "Package: $OUTPUT"
echo ""
dpkg-deb -I "$OUTPUT"

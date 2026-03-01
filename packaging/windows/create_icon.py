#!/usr/bin/env python3
"""Generate crosshair-overlay.ico from the same design used in the tray icon."""

from PIL import Image, ImageDraw


def create_crosshair_image(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Scale factor relative to 64px base
    s = size / 64.0

    # Circle
    margin = int(8 * s)
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        outline=(221, 221, 221, 153), width=max(1, int(2 * s)))

    cx = size // 2
    cy = size // 2
    gap = int(8 * s)
    end = int(28 * s)
    lw = max(1, int(2 * s))

    # Cross lines
    draw.line([(cx, margin // 2), (cx, cy - gap)],
        fill=(221, 221, 221, 255), width=lw)
    draw.line([(cx, cy + gap), (cx, size - margin // 2)],
        fill=(221, 221, 221, 255), width=lw)
    draw.line([(margin // 2, cy), (cx - gap, cy)],
        fill=(221, 221, 221, 255), width=lw)
    draw.line([(cx + gap, cy), (size - margin // 2, cy)],
        fill=(221, 221, 221, 255), width=lw)

    # Center dot
    dot_r = max(2, int(3 * s))
    draw.ellipse(
        [cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
        fill=(238, 85, 85, 255))

    return img


def main():
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [create_crosshair_image(s) for s in sizes]

    # Save as .ico with all sizes
    images[0].save(
        "crosshair-overlay.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:])
    print(f"Created crosshair-overlay.ico with sizes: {sizes}")


if __name__ == "__main__":
    main()

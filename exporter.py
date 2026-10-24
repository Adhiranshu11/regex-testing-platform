"""
exporter.py  --  Step 6 (export half): save automaton diagrams as images
=========================================================================
SVG needs nothing extra. PNG uses the optional `cairosvg` package
(pip install cairosvg); without it, use the web app's Save PNG button instead.
"""
import os


def save_svg(svg, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return path


def save_png(svg, path, scale=2):
    """Write a PNG of the diagram. Returns True on success, False if cairosvg is missing."""
    try:
        import cairosvg
    except ImportError:
        return False
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=path, scale=scale,
                     background_color="white")
    return True

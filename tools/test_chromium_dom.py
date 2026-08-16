import subprocess
import json

# Test with Chromium headless dump
cmd = [
    "chromium", "--headless", "--no-sandbox", "--disable-gpu",
    "--dump-dom",
    "file:///home/cgl/dev/monad/web/monadone/index.html"
]

res = subprocess.run(cmd, capture_output=True, text=True)
dom = res.stdout

assert "Productive Self-Application" in dom, "Title missing in DOM"
assert "assets/slide1.png" in dom, "Slide 1 missing in DOM"
assert "assets/slide2.png" in dom, "Slide 2 missing in DOM"
assert "lightbox-modal" in dom, "Lightbox missing in DOM"
assert "comp-btn" in dom, "Component selector missing in DOM"
print("Chromium Headless DOM Rendering: 100% VALID.")

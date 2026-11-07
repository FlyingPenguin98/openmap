# Generated textures for the stitched world map (no game art):
#   MapGrain.tga        tileable parchment mottling (dark, alpha = how much), drawn
#                       over land that has no zone map
#   MapFeatherThin.tga  the overlays' edge fade, its edge wavy like torn paper
#   MapFeather*.tga     straight edge fades (zone base art 10%, continents 18%),
#   MapFeatherRound.tga a round fade for city maps
#   MapTooth.tga        fine paper tooth for the closest zoom
# (Masks and grain only: map icons are Blizzard's own, never drawn here.)
# usage: python -P tools/map-textures/make.py
import os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import clients   # the client the tools build for (OPENMAP_CLIENT)
OUT = clients.TEX
N = 256

def periodic_noise(beta, seed):
    # 1/f^beta noise that tiles seamlessly (filtered on the FFT torus)
    r = np.random.default_rng(seed)
    f = np.fft.fft2(r.standard_normal((N, N)))
    ky, kx = np.fft.fftfreq(N)[:, None], np.fft.fftfreq(N)[None, :]
    k = np.sqrt(kx * kx + ky * ky); k[0, 0] = 1
    n = np.real(np.fft.ifft2(f / k ** beta))
    return (n - n.mean()) / n.std()

def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def save(alpha, path, rgb=(255, 255, 255)):
    img = np.dstack([np.full((N, N), c) for c in rgb] + [np.clip(alpha, 0, 1) * 255]).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(OUT, path))

# parchment mottling: broad blotches, a little paper grain
v = 0.85 * periodic_noise(1.8, 1) + 0.3 * periodic_noise(0.6, 2)
save(np.clip((v - 0.3) / 2.4, 0, 1) ** 1.2 * 0.4, "MapGrain.tga", (92, 64, 34))

ys, xs = np.mgrid[0:N, 0:N] + 0.5
edge = np.minimum(np.minimum(xs, N - xs), np.minimum(ys, N - ys))
def feather(F, wobble=0.0, seed=3, inset=0.0):
    # fully clear for the outer `inset` (the zone art's own dark torn-paper frame), then fading in over F
    d = (edge - inset * N) / (F * N)
    if wobble: d = d + wobble * periodic_noise(2.4, seed) * np.clip(1.6 - d, 0, 1)
    return smooth(d) * smooth((edge - inset * N) / (0.02 * N))   # the inset stays clear, wobble or not

save(feather(0.10, 0.45, inset=0.06), "MapFeatherThin.tga")
save(feather(0.10, inset=0.08), "MapFeather.tga")
save(feather(0.18), "MapFeatherWide.tga")
dist = np.hypot(xs / N * 2 - 1, ys / N * 2 - 1)
save(smooth((0.98 - dist) / 0.43), "MapFeatherRound.tga")
print("ok")

# MapTooth.tga: fine paper tooth (tileable noise, dark, alpha = how much), over the art at
# the closest zoom with MapGrain, so stretched art reads as close-up paper
t = periodic_noise(0.35, 5)
save(np.clip((t - 0.2) / 2.0, 0, 1) * 0.5, "MapTooth.tga", (60, 42, 22))
print("tooth ok")

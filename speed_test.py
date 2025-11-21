import time
import io
import tkinter as tk
from PIL import Image

root = tk.Tk()

# Create a decent sized image (e.g. 720p)
img = Image.new("RGB", (1280, 720), "red")

# Test PNG
start = time.time()
bio_png = io.BytesIO()
img.save(bio_png, format="PNG")
data_png = bio_png.getvalue()
photo_png = tk.PhotoImage(data=data_png)
print(f"PNG Time: {time.time() - start:.4f}s")

# Test PPM
start = time.time()
bio_ppm = io.BytesIO()
img.save(bio_ppm, format="PPM")
data_ppm = bio_ppm.getvalue()
photo_ppm = tk.PhotoImage(data=data_ppm)
print(f"PPM Time: {time.time() - start:.4f}s")

root.destroy()

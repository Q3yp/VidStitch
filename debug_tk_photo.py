import tkinter as tk
import os
from PIL import Image

# Create a dummy image
img = Image.new("RGB", (100, 100), "blue")
img.save("test.png")

root = tk.Tk()
try:
    # Try standard Tkinter PhotoImage (no PIL needed for PNG in Tk 8.6+)
    photo = tk.PhotoImage(file="test.png")
    label = tk.Label(root, image=photo)
    label.pack()
    print("tk.PhotoImage(file=...) worked!")
except Exception as e:
    print(f"tk.PhotoImage failed: {e}")

root.update()
root.destroy()

import tkinter as tk
from PIL import Image, ImageTk
import sys

print(f"Python version: {sys.version}")
root = tk.Tk()
img = Image.new("RGB", (100, 100), "red")
try:
    photo = ImageTk.PhotoImage(img)
    label = tk.Label(root, image=photo)
    label.pack()
    print("ImageTk.PhotoImage created successfully.")
except Exception as e:
    print(f"Error creating PhotoImage: {e}")
    import traceback
    traceback.print_exc()

root.update()
root.destroy()

import tkinter as tk
from PIL import Image
import io
import base64

root = tk.Tk()

# Create dummy image
img = Image.new("RGB", (50, 50), "green")
bio = io.BytesIO()
img.save(bio, format="PNG")
img_data = bio.getvalue()

try:
    # Use data= argument
    photo = tk.PhotoImage(data=img_data)
    label = tk.Label(root, image=photo)
    label.pack()
    print("tk.PhotoImage(data=...) worked!")
except Exception as e:
    print(f"tk.PhotoImage(data=...) failed: {e}")

root.update()
root.destroy()

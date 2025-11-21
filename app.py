import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading
import time
import cv2
import io
import tempfile
import shutil
from PIL import Image
from video_processor import VideoStitcher

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def pil_to_photoimage(pil_image):
    if pil_image is None:
        return None
    bio = io.BytesIO()
    # PPM is uncompressed and much faster to generate than PNG
    if pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    pil_image.save(bio, format="PPM")
    return tk.PhotoImage(data=bio.getvalue())

class VideoPlayerFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.video_path = None
        self.cap = None
        self.is_playing = False
        # Removed threading event, using simpler flag for after loop
        
        self.display_label = ctk.CTkLabel(self, text="No Video Loaded", fg_color="black", text_color="white")
        self.display_label.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.controls = ctk.CTkFrame(self, height=40)
        self.controls.pack(fill="x", padx=5, pady=5)
        
        self.btn_play = ctk.CTkButton(self.controls, text="Play", width=60, command=self.toggle_play)
        self.btn_play.pack(side="left", padx=5)
        
        self.slider = ctk.CTkSlider(self.controls, from_=0, to=100, command=self.seek)
        self.slider.pack(side="left", fill="x", expand=True, padx=5)
        self.slider.set(0)

    def load_video(self, path):
        self.stop_playback()
        self.video_path = path
        if not path or not os.path.exists(path):
            self.display_label.configure(text="File not found" if path else "No Video")
            return

        # Open strictly for one frame
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self.display_label.configure(text="Error loading video")
            return

        ret, frame = cap.read()
        if ret:
            self.show_frame(frame)
        cap.release()
        
        self.display_label.configure(text="")
        self.btn_play.configure(text="Play")

    def stop_playback(self):
        self.is_playing = False
        if self.cap:
            self.cap.release()
            self.cap = None

    def toggle_play(self):
        if not self.video_path:
            return

        if self.is_playing:
            # Pause
            self.is_playing = False
            self.btn_play.configure(text="Play")
        else:
            # Play
            self.is_playing = True
            self.btn_play.configure(text="Pause")
            
            # Initialize capture if needed
            if self.cap is None or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.video_path)
                
                # Restore position from slider
                total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_frames > 0:
                    current_pos = self.slider.get()
                    start_frame = int((current_pos / 100) * total_frames)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # Start the loop on main thread
            self.play_next_frame()

    def play_next_frame(self):
        start_time = time.time()
        
        if not self.is_playing or not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            # End of video
            self.is_playing = False
            self.btn_play.configure(text="Play")
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Reset
            return

        # Update UI
        self.show_frame(frame)
        
        # Update slider (skip every few frames to save UI updates)
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        if int(current_frame) % 5 == 0:
            total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            if total_frames > 0:
                progress = (current_frame / total_frames) * 100
                self.slider.set(progress)

        # Schedule next frame accounting for processing time
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30
        
        process_time = (time.time() - start_time) * 1000
        delay_ms = int(max(1, (1000 / fps) - process_time))
        
        self.after(delay_ms, self.play_next_frame)

    def show_frame(self, frame):
        h_label = self.display_label.winfo_height()
        w_label = self.display_label.winfo_width()
        
        if h_label < 10 or w_label < 10: return

        h, w, _ = frame.shape
        aspect = w / h
        
        if w_label / h_label > aspect:
            new_h = h_label
            new_w = int(aspect * new_h)
        else:
            new_w = w_label
            new_h = int(new_w / aspect)

        frame = cv2.resize(frame, (new_w, new_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        
        photo = pil_to_photoimage(img)
        self.current_photo = photo 
        self.display_label.configure(image=photo, text="")
    
    def seek(self, value):
        if self.cap and self.cap.isOpened():
            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            target_frame = int((value / 100) * total_frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            # If paused, show that frame immediately
            if not self.is_playing:
                ret, frame = self.cap.read()
                if ret:
                    self.show_frame(frame)

class DraggableItem(ctk.CTkFrame):
    def __init__(self, master, index, video_path, thumbnail_photo, on_drag_start, on_drag_release, **kwargs):
        super().__init__(master, **kwargs)
        self.index = index
        self.video_path = video_path
        self.on_drag_start = on_drag_start
        self.on_drag_release = on_drag_release
        
        self.configure(fg_color=("gray85", "gray20"), corner_radius=6)

        self.thumb_label = ctk.CTkLabel(self, text="", width=80, height=45)
        if thumbnail_photo:
            self.thumb_label.configure(image=thumbnail_photo)
        else:
            self.thumb_label.configure(text="No Img")
        self.thumb_label.pack(side="left", padx=5, pady=5)

        filename = os.path.basename(video_path)
        self.name_label = ctk.CTkLabel(self, text=filename, anchor="w", font=ctk.CTkFont(size=13))
        self.name_label.pack(side="left", fill="x", expand=True, padx=5)

        self.handle = ctk.CTkLabel(self, text="☰", width=30, cursor="hand2")
        self.handle.pack(side="right", padx=5)

        self.handle.bind("<Button-1>", self.start_drag)
        self.handle.bind("<ButtonRelease-1>", self.stop_drag)
        self.bind("<Button-1>", self.start_drag)
        self.bind("<ButtonRelease-1>", self.stop_drag)

    def start_drag(self, event):
        self.on_drag_start(event, self.index)

    def stop_drag(self, event):
        self.on_drag_release(event)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VidStitch - AI Video Stitcher")
        self.geometry("1000x700")

        self.stitcher = VideoStitcher()
        self.video_paths = []
        self.thumbnails = {} 
        self.drag_data = {"item": None, "index": None}
        self.temp_output_path = None

        self.grid_columnconfigure(0, weight=1) 
        self.grid_columnconfigure(1, weight=2) 
        self.grid_rowconfigure(0, weight=1)

        # --- Left Column: Video List ---
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_panel.grid_rowconfigure(1, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.left_panel, text="Video Sequence", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self.left_panel, label_text="Drag '☰' to reorder")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        self.add_btn = ctk.CTkButton(self.left_panel, text="Add Videos", command=self.add_videos)
        self.add_btn.grid(row=2, column=0, pady=10, padx=10, sticky="ew")

        # --- Right Column: Preview & Stitch ---
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.right_panel.grid_rowconfigure(0, weight=1) 
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.player = VideoPlayerFrame(self.right_panel)
        self.player.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Action Area
        self.action_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.action_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        # Buttons Container
        self.btn_container = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.btn_container.pack(fill="x", pady=5)
        
        self.stitch_btn = ctk.CTkButton(self.btn_container, text="Stitch & Preview", command=self.stitch_preview, height=40, fg_color="green")
        self.stitch_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.export_btn = ctk.CTkButton(self.btn_container, text="Export", command=self.export_video, height=40, state="disabled")
        self.export_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        self.status_label = ctk.CTkLabel(self.action_frame, text="Ready", anchor="w")
        self.status_label.pack(fill="x", pady=(5, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.action_frame)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        self.progress_bar.set(0)

        self.list_widgets = []

    def add_videos(self):
        files = filedialog.askopenfilenames(filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv")])
        if files:
            for f in files:
                if f not in self.video_paths:
                    self.video_paths.append(f)
                    pil_thumb = self.stitcher.get_thumbnail(f)
                    if pil_thumb:
                        pil_thumb = pil_thumb.resize((80, 45))
                        photo = pil_to_photoimage(pil_thumb)
                        self.thumbnails[f] = photo
                    else:
                        self.thumbnails[f] = None
            self.refresh_list()

    def refresh_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self.list_widgets.clear()

        for i, path in enumerate(self.video_paths):
            item = DraggableItem(
                self.scroll_frame, 
                index=i, 
                video_path=path, 
                thumbnail_photo=self.thumbnails.get(path),
                on_drag_start=self.on_drag_start, 
                on_drag_release=self.on_drag_release
            )
            item.pack(fill="x", pady=2, padx=2)
            self.list_widgets.append(item)

    def on_drag_start(self, event, index):
        self.drag_data["index"] = index
        self.drag_data["item"] = self.list_widgets[index]
        self.drag_data["item"].configure(fg_color=("green", "green")) 

    def on_drag_release(self, event):
        src_index = self.drag_data["index"]
        if src_index is None: return

        root_y = self.winfo_pointery() 
        
        target_index = src_index 
        
        for i, widget in enumerate(self.list_widgets):
            w_y = widget.winfo_rooty()
            w_h = widget.winfo_height()
            if w_y < root_y < (w_y + w_h):
                target_index = i
                break
        
        if src_index != target_index:
            item = self.video_paths.pop(src_index)
            self.video_paths.insert(target_index, item)
            self.refresh_list()
        else:
            self.refresh_list()
            
        self.drag_data["index"] = None

    def stitch_preview(self):
        if len(self.video_paths) < 1:
            messagebox.showwarning("No Videos", "Please add at least one video.")
            return

        # Ensure previous playback is stopped to release file lock
        self.player.stop_playback()
        
        # Define temp path
        self.temp_output_path = os.path.join(tempfile.gettempdir(), "vidstitch_preview.mp4")

        self.stitch_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.progress_bar.start()
        
        threading.Thread(target=self.run_stitch_process, args=(self.temp_output_path,), daemon=True).start()

    def run_stitch_process(self, output_path):
        try:
            def update_status(msg):
                self.status_label.configure(text=msg)
            
            self.stitcher.stitch_videos(self.video_paths, output_path, progress_callback=update_status)
            
            # On Success
            self.after(0, lambda: self.on_stitch_complete(output_path))
            
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{e}"))
            self.after(0, self.reset_ui)

    def on_stitch_complete(self, path):
        self.reset_ui()
        self.status_label.configure(text="Preview Ready")
        self.player.load_video(path)
        self.export_btn.configure(state="normal")

    def export_video(self):
        if not self.temp_output_path or not os.path.exists(self.temp_output_path):
            return

        target_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if target_path:
            try:
                shutil.copy2(self.temp_output_path, target_path)
                messagebox.showinfo("Exported", "Video exported successfully!")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def reset_ui(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.stitch_btn.configure(state="normal")
        self.status_label.configure(text="Ready")

if __name__ == "__main__":
    app = App()
    app.mainloop()

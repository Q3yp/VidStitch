import os
import numpy as np
import cv2
from moviepy import VideoFileClip, concatenate_videoclips
from skimage.metrics import structural_similarity as ssim
from PIL import Image

class VideoStitcher:
    def __init__(self):
        self.clips = []
        self.search_window = 2  # seconds to search at head/tail

    def get_thumbnail(self, video_path):
        """
        Extracts a thumbnail from the start of the video.
        Returns a PIL Image.
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            ret, frame = cap.read()
            cap.release()
            if ret:
                # Convert BGR to RGB
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                return Image.fromarray(frame)
            return None
        except Exception:
            return None

    def calculate_similarity(self, frame1, frame2):
        """
        Calculates similarity between two frames using MSE on resized grayscale images.
        Lower score means more similar.
        """
        # Get original aspect ratio from one of the frames
        original_h, original_w, _ = frame1.shape
        original_aspect = original_w / original_h

        # Define target height for comparison (e.g., 128 pixels)
        target_height = 512
        target_width = int(target_height * original_aspect)
        
        # Ensure target_width is at least 1 pixel to avoid errors with very thin videos
        target_width = max(1, target_width)

        # Resize frames preserving aspect ratio
        img1 = cv2.resize(cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY), (target_width, target_height))
        img2 = cv2.resize(cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY), (target_width, target_height))
        
        mse = np.mean((img1 - img2) ** 2)
        return mse

    def find_best_transition(self, clip1, clip2):
        """
        Finds the timestamp in clip1 (end) and clip2 (start) that minimizes the difference.
        Returns (t1, t2) where t1 is cut point for clip1, t2 is start point for clip2.
        """
        # Determine search duration based on clip lengths
        duration1 = clip1.duration
        duration2 = clip2.duration
        
        search_dur1 = min(self.search_window, duration1)
        search_dur2 = min(self.search_window, duration2)
        
        # Extract frames at roughly 10 fps for the search window to save time
        # We don't need to check every single frame for a rough match, but let's try 
        # to be somewhat precise.
        fps_check = 10
        
        # Times to check
        t1_start = duration1 - search_dur1
        t2_end = search_dur2
        
        # Generate frames
        # iter_frames yields (t, frame) ideally, but moviepy yields just frame
        # We'll generate times manually
        # Avoid exact end of clip to prevent "bytes wanted but 0 bytes read" warning
        safe_duration1 = max(0, duration1 - 0.01)
        t1_start = max(0, safe_duration1 - search_dur1)
        
        times1 = np.linspace(t1_start, safe_duration1, int(search_dur1 * fps_check))
        times2 = np.linspace(0, t2_end, int(search_dur2 * fps_check))
        
        best_score = float('inf')
        best_t1 = safe_duration1
        best_t2 = 0
        
        # Cache frames for clip2 to avoid re-reading
        frames2 = [(t, clip2.get_frame(t)) for t in times2]
        
        for t1 in times1:
            try:
                frame1 = clip1.get_frame(t1)
                for t2, frame2 in frames2:
                    score = self.calculate_similarity(frame1, frame2)
                    if score < best_score:
                        best_score = score
                        best_t1 = t1
                        best_t2 = t2
            except Exception as e:
                # Handle potential errors reading end of stream
                continue
                
        print(f"Best transition found: Cut Clip A at {best_t1:.2f}s, Start Clip B at {best_t2:.2f}s (Score: {best_score:.2f})")
        return best_t1, best_t2

    def stitch_videos(self, video_paths, output_path, progress_callback=None):
        if not video_paths:
            return

        loaded_clips = []
        try:
            # 1. Load all clips
            for i, path in enumerate(video_paths):
                if progress_callback:
                    progress_callback(f"Loading video {i+1}/{len(video_paths)}...")
                loaded_clips.append(VideoFileClip(path))

            if len(loaded_clips) < 2:
                # Just export the single clip
                 if progress_callback:
                    progress_callback("Exporting single video...")
                 loaded_clips[0].write_videofile(output_path, codec="libx264", audio_codec="aac")
                 return

            final_subclips = []
            
            # 2. Process pairs
            # First clip is always kept from start
            prev_clip = loaded_clips[0]
            
            for i in range(1, len(loaded_clips)):
                next_clip = loaded_clips[i]
                
                if progress_callback:
                    progress_callback(f"Analyzing transition {i}/{len(loaded_clips)-1}...")
                
                # Find best cut points
                cut_prev, start_next = self.find_best_transition(prev_clip, next_clip)
                
                # Trim previous clip
                # Note: If this is the first iteration, we take from 0. 
                # If it's not, we've effectively already "consumed" the previous clip, 
                # but wait -- we need to handle the chain.
                # Chain strategy:
                # Clip 1: 0 -> cut_1
                # Clip 2: start_2 -> cut_2
                # ...
                # Clip N: start_N -> end
                
                # For the current pair (prev_clip, next_clip):
                # We determine where prev_clip ENDS and where next_clip STARTS.
                
                # For the very first clip, we start at 0.
                # For subsequent clips, the 'start' was determined in the previous iteration.
                # BUT, determining the "end" of Clip 2 might depend on Clip 3.
                # This implies a greedy approach: optimize 1-2, then 2-3, etc.
                # So we need to store "start_point" for the current clip (determined by previous transition)
                
                pass 

            # Refined Logic for Chaining
            # We need to track "start_time" for the current clip.
            current_clip_start_time = 0
            
            trimmed_clips = []
            
            for i in range(len(loaded_clips) - 1):
                clip_a = loaded_clips[i]
                clip_b = loaded_clips[i+1]
                
                if progress_callback:
                    progress_callback(f"Stitching {i+1} & {i+2}...")

                cut_a, start_b = self.find_best_transition(clip_a, clip_b)
                
                # Add the segment of Clip A
                segment = clip_a.subclipped(current_clip_start_time, cut_a)
                trimmed_clips.append(segment)
                
                # Update start time for Clip B for the next iteration
                current_clip_start_time = start_b
                
            # Add the final clip remainder
            last_clip = loaded_clips[-1]
            segment = last_clip.subclipped(current_clip_start_time, last_clip.duration)
            trimmed_clips.append(segment)

            # 3. Concatenate
            if progress_callback:
                progress_callback("Rendering final video...")
                
            final_clip = concatenate_videoclips(trimmed_clips, method="compose")
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
            final_clip.close()
            
            if progress_callback:
                progress_callback("Done!")

        except Exception as e:
            print(f"Error during stitching: {e}")
            raise e
        finally:
            # Cleanup
            for clip in loaded_clips:
                clip.close()

if __name__ == "__main__":
    print("VideoStitcher module loaded.")
    # You can add test code here if needed
    stitcher = VideoStitcher()
    print("VideoStitcher initialized successfully.")
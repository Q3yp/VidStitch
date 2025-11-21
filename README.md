# VidStitch - AI Smart Video Stitcher Vibed with Gemini3

VidStitch is a Python-based desktop application that intelligently stitches video clips together. Instead of simple concatenation, it analyzes the tail of the preceding video and the head of the following video to find the most visually similar frame, creating a smoother, "smart" cut.

## Features

- **GUI Interface:** Drag-and-drop style video ordering (via buttons).
- **Smart Stitching:** Automatically finds the best cut point between videos to minimize visual jump cuts.
- **Support:** MP4, MOV, AVI, MKV.

## Installation

This project uses `uv` for dependency management.

1.  **Prerequisites:** Ensure you have Python installed.
2.  **Install dependencies:**
    ```bash
    uv sync
    ```

## Usage

1.  **Run the application:**
    ```bash
    uv run app.py
    ```
2.  **Add Videos:** Click "Add Videos" to select your clips.
3.  **Arrange:** Use "Move Up" and "Move Down" to order them.
4.  **Stitch:** Click "Stitch Videos", choose a save location, and wait for the process to complete.

## Technical Details

- **Framework:** CustomTkinter (GUI).
- **Processing:** MoviePy & OpenCV.
- **Algorithm:** Compares frame similarity (MSE on resized frames) within a search window (default 2s) to find optimal transition points.

import asyncio
import overshoot
import cv2
import os
from dotenv import load_dotenv
from collections import deque
import time

load_dotenv()
API_KEY = os.getenv("OVERSHOOT_API_KEY")
BUFFER_LENGTH_SECONDS = 4.0
FPS = 3
frame_buffer = deque(maxlen=int(BUFFER_LENGTH_SECONDS * FPS)) # Assuming 5 FPS max

def save_anomaly_clip(frames_to_save):
    """Dumps the buffer to an MP4 file when a boat is spotted."""
    if not frames_to_save:
        return
        
    # Generate a unique filename based on the timestamp
    filename = f"anomaly_boat_most_recent.mp4"
    print(f"\n[!] ANOMALY DETECTED! Saving past {BUFFER_LENGTH_SECONDS} seconds to {filename}")
    
    # Setup the OpenCV Video Writer
    height, width, _ = frames_to_save[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, FPS, (width, height))
    
    for frame in frames_to_save:
        out.write(frame)
    out.release()
    print("[+] Clip saved successfully.\n")

def handle_overshoot_result(response):
    text = response.result.lower()
    if "yes" in text:
        captured_clip = list(frame_buffer)
        save_anomaly_clip(captured_clip)
        print("Person detected!")
    else:
        print(text)

async def main():
    # Make sure you are using the AsyncClient for await calls
    client = overshoot.Overshoot(api_key=API_KEY) 
    source = overshoot.FrameSource(width=640, height=480)
    
    print("Connecting to Overshoot...")
    stream = await client.streams.create(
        source=source,
        prompt="Respond 'Yes' if there is a water bottle in frame, otherwise respond with what you see.",
        model="Qwen/Qwen3.5-4B",
        on_result=lambda r: handle_overshoot_result(r),
        max_output_tokens=10,
        
        # FIXED MATH: 3 FPS for a 1-second clip = 3 frames sent to the model per analysis
        target_fps=FPS,
        clip_length_seconds=1.0, 
        delay_seconds=0.5,
        interval_seconds=2.0 # Ask for analysis every 2 seconds
    )

    cap = cv2.VideoCapture(0)
    print("Streaming frames... Press Ctrl+C in the terminal to stop.")
    
    try:
        while True:
            ret, bgr = cap.read()
            if not ret:
                print("Camera feed lost.")
                break
            # Save the raw frame to our local Ring Buffer
            frame_buffer.append(bgr)

            # Overshoot FrameSource expects RGBA format
            rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
            rgba = cv2.resize(rgba, (640, 480))
            
            # Push the frame into the stream
            source.push_frame(rgba) 
            
            # Yield control back to asyncio briefly
            await asyncio.sleep(0.01) 
            
    except KeyboardInterrupt:
        print("\nStopping stream...")
        
    finally:
        cap.release()
        await stream.close()
        await client.close()
        print("Cleanup complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # Catch the interrupt at the top level to hide the ugly traceback


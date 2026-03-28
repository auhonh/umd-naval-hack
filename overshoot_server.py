import asyncio
import aiofiles
import zmq
import zmq.asyncio
import json
import time
import os
import aiofiles

''' my laptop basically just listens for alerts from the Pi and prints them to the terminal.'''
async def watch_target_file(pub_socket):
    """Watches for UI updates and broadcasts the new target."""
    filename = "current_target.txt"
    last_modified = 0
    
    # Create the file if it doesn't exist
    if not os.path.exists(filename):
        with open(filename, "w") as f: f.write("")
        
    while True:
        current_modified = os.path.getmtime(filename)
        if current_modified > last_modified:
            async with aiofiles.open(filename, mode='r') as f:
                new_target = await f.read()
                new_target = new_target.strip()
                
            if new_target:
                # Broadcast the update to the Pi
                await pub_socket.send_string(f"TARGET:{new_target}")
                print(f"\n[+] Broadcasted new AI target: {new_target}")
                print("Command (start/stop): ", end="", flush=True)
                
            last_modified = current_modified
            
        await asyncio.sleep(1) # Check every second
        
async def listen_for_alerts(pull_socket):
    """Constantly listens for messages from the Pi."""
    print("[*] Listening for incoming alerts on port 5556...")
    while True:
        parts = await pull_socket.recv_multipart()
        
        # Unpack the data
        metadata = json.loads(parts[0].decode('utf-8'))
        video_bytes = parts[1]
        
        # Generate a unified timestamp prefix
        timestamp = int(time.time())
        
        # Add the exact timestamp to the metadata before saving
        metadata["timestamp"] = timestamp
        
        vid_filename = os.path.join("data", f"{timestamp}_video.mp4")
        meta_filename = os.path.join("data", f"{timestamp}_meta.json")
        
        # Save the video
        with open(vid_filename, "wb") as f:
            f.write(video_bytes)
            
        # Save the metadata
        with open(meta_filename, "w") as f:
            json.dump(metadata, f, indent=4)
            
        print(f"\n[🚨 ALERT]: {metadata['message']}")
        print(f"[📁 SAVED]: {vid_filename} and {meta_filename}")
        print("Command (start/stop): ", end="", flush=True)

async def get_user_commands(pub_socket):
    """Waits for you to type 'start' or 'stop' and broadcasts it."""
    loop = asyncio.get_running_loop()
    print("[*] Command broadcaster ready on port 5555.")
    
    while True:
        # run_in_executor prevents input() from freezing the incoming alerts
        cmd = await loop.run_in_executor(None, input, "Command (start/stop): ")
        cmd = cmd.strip().lower()
        
        if cmd in ['start', 'stop']:
            await pub_socket.send_string(cmd)
            print(f"[+] Broadcasted: {cmd}")
        else:
            print("[-] Invalid command. Use 'start' or 'stop'.")

async def main():
    ctx = zmq.asyncio.Context()

    # Setup the Publisher socket (Commands out)
    pub_socket = ctx.socket(zmq.PUB)
    pub_socket.bind("tcp://*:5555")

    # Setup the Pull socket (Alerts in)
    pull_socket = ctx.socket(zmq.PULL)
    pull_socket.bind("tcp://*:5556")

    # Run both tasks concurrently
    await asyncio.gather(
        listen_for_alerts(pull_socket),
        get_user_commands(pub_socket)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down Command Center.")
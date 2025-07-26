# RescueLaneClipper
## Introduction
In countries like Germany, Austria and Swiss, it is mandatory for vehicles to form a rescue lane during traffic jams or slow-moving conditions on highways, allowing emergency vehicles to reach accident scenes without delay.

However, violations are difficult to enforce due to
- Lack of real-time documentation and evidence,
- Emergency responders needing to focus on saving lives, not monitoring traffic behaviour.

This project aims at automatically detecting and documenting obstructions of emergency vehicles using a camera installed inside the vehicle - similar to a dashcam.
Unlike a typical dashcam, this project is not build to detect crashes, but detect license plates that remain in the frame for long.

The project analyzes frames, detects number plates, reads the number plates with OCR and evaluates if the number plate got scanned before. The project can be customized through a config.ini file and uses basic logic like a Levenshtein ratio to tackle wrong OCR.

The finished project is planned to feature an open-source list of parts, 3D print files and more to rebuild and refine the project at home.

> [!NOTE]  
> This project is actively being developed and is not yet feature-complete. Expect changes, improvements, and new functionality over time. Feedback and contributions are welcome!

## Prerequisites
You will need Python3, pip and wget for this project.

## Installation
- Download the code from GitHub
### In a Terminal
- Change the directory to the folder where you want to put your future project: `cd /path/to/new/project/folder`
- Create a new Python virtual environment in the folder:
  `python -m venv .venv`


- Copy the following files into your new folder:
  - main.py
  - FrameManager.py
  - FrameProcessor.py
  - license_plate_detector.pt
  - config.ini
  

- Activate the virtual environment: `.venv\Scripts\activate.ps1` (Windows) or `source .venv/bin/activate` (Unix/macOS)
  - On Windows, you might have to enable Execution of RemoteSigned scripts before executing the .ps1 script: `Set-ExecutionPolicy RemoteSigned` (In a Powershell Admin Terminal)
  - You should see your prompt change to *(.venv) ...*
- Install all external libraries: `pip install opencv-python Levenshtein fast_plate_ocr[onnx] ultralytics pyserial tuspy py7zr`

- Install pycamera2: `sudo apt update` and `sudo apt install python3-picamera2 -y`

## Execution
- run the program: `python main.py`
  - You should see some output: "Warming up YOLO Model... Warm-up finished!"

## Whitelisting
It might be useful to have certain number plates ignored by the system, for example other rescue vehicles.
Therefore, a whitelist.txt file can be created in the main project folder. Each line inside this file is one number plate.
The system checks against each value in this list and ignores it, shown by a "[whitelisted]" tag in the consoles output.

You can also set a custom Levenshtein ratio for this check (LevenshteinThresholdWhitelist) to make sure that the whitelist works properly.

If the whitelist is not used, the .txt file may be deleted.

> [!NOTE]  
> As this project is actively being developed, currently it does not yet accept a webcams livestream! It uses example videos like [this one](https://www.youtube.com/watch?v=M6Rtz2CiY2c).
> The video can be downloaded via 3D YouTube Downloader and is expected to be under the path "./tests/insideView.mp4".

## Upload
To upload the saved video files and images, we use [tus/tusd](https://tus.io/), as it has a few feature that we can make use of:
- Simple installation and setup
- Resumable uploads (if power got cut before fully uploading)
- Simple user authentification to make sure that not everybody can upload to the server
- Encryption of files isn't as simple with tus/tusd, so we rely on encrypting the files itself before sending them

A second machine will be needed. In this project, a second Raspberry Pi with Raspbian
will be used. The following instructions use the terms "Client" (The Raspberry Pi inside the vehicle) and "Server" (The Raspberry Pi that gets uploaded to) as names for the respective machines.

### Terminal on the server machine:
#### Install tusd:
- Download the zipped tusd folder: `wget https://github.com/tus/tusd/releases/download/v2.8.0/tusd_linux_arm.tar.gz`
- Extract the archive: `tar -xzf tusd_linux_arm.tar.gz`
- Change directory into the extracted archive: `cd tusd_linux_arm`
- Set correct permissions for file: `chmod +x tusd`
- Move tusd binary to correct directoy: `sudo mv tusd /usr/local/bin/`
- Create folder for uploads: `mkdir tus-uploads`

You can verify that everything worked with:
- `which tusd` should return `/usr/local/bin/tusd`
- `tusd -version` should return:
```
Version: v2.8.0
Commit: 0e52ad650abed02ec961353bb0c3c8bc36650d2c
Date: Wed Apr  2 07:47:10 UTC 2025
```

If everything is working as intended, you can remove your downloaded files with:
- `cd ..` and 
- `rm -rf tusd_linux_arm*`

#### Install a firewall:
A firewall should always be used, especially if we want our server to be accessible from external sources!
- Update our packages list: `sudo apt update`
- Install firewall: `sudo apt install ufw`
> [!NOTE]
> Ports give access to different services on the same system, kind of like a corridor with lots of doors that are either locked or unlocked.
> There are so called 'well-known ports' (port 0-1023) that are reserved for default services.
> To make it a bit harder for possible intruders, we can choose a random port (1024-65535), as many port scans just check the well-known ports.
>
> You can use a [random port generator](https://proxyscrape.com/tools/port) for this.
> 
> Please write your chosen port down somewhere, as you will need it later!

- Add chosen port to firewall: `sudo ufw allow [your port]`, e.g. `sudo ufw allow 37859`

> [!NOTE]
> If you use SSH or SFTP to access your server, make sure to add the port to the firewall as well (default is 22):
> `sudo ufw allow 22`
> 
> If you have other services running on your server that need open ports, repeat the process for each port.

- Finally, enable the firewall: `sudo ufw allow`

> [!NOTE]
> Remember to enable Port-Forwarding in your router. If you don't have a static public IP, you will need a dynamic DNS service like [noip](https://www.noip.com).
> If you use noip, you can either set up your router to automatically sync your public IP with noip or use the Dynamic Update Client (only updates when the device is running!).


#### Start tusd for the first time:
- Start your tusd service temporarily (change the port to your own!): `tusd -upload-dir "./tus-uploads" -host "0.0.0.0" -port "37859" -disable-download`
- You should see a line that states `You can now upload files to: http://[::]:37859/files/`
- Open a **second terminal** on the server and issue the command `curl localhost:37859/files` (change the port to your own!) 
- You should get an error, but a new line on your first terminal as well. This proves that a connection can be made.

#### Implementing tusd as a service:
To autostart tus/tusd whenever the Raspberry Pi boots, we use systemd.
- Get into the correct directory: `cd /etc/systemd/system/`
- Create a new file: `sudo nano tusd.service`
- Add the following lines to the file (change the port to your own!):
```
# /etc/systemd/system/tusd.service
[Unit]
Description=tusd resumable upload server
Requires=network.target

[Service]
User=pi
ExecStart=/usr/local/bin/tusd -upload-dir /home/pi/tus-uploads -disable-download -port 37859
Restart=always

[Install]
WantedBy=multi-user.target
```
- Save the file with CTRL+O and press Enter
- Close the file with CTRL+X
- Set permissions for the file: `sudo chmod 644 /etc/systemd/system/tusd.service`
- Reload systemctl daemon: `sudo systemctl daemon-reload`
- Enable service: `sudo systemctl enable tusd.service`
- Reboot server: `sudo reboot`

After rebooting, you should be able to test the service the same way you did in the [section above](#start-tusd-for-the-first-time).

### Configuring the config.ini
To make the upload work properly, you have to update your config.ini "Upload" section.
- EnableUpload: If you want to upload to an external source, this has to be set to True
- Server: The static IP or Dyn-DNS Address that your server uses
- UploadPort: The port that you used in your port-forwarding
- EncryptionKey: All files that get uploaded will be encrypted with this key. Don't share this key if it runs in a production environment!

> [!IMPORTANT]
> Currently, all files that get uploaded get saved as two files: [filename] and [filename].info.
> 
> To view your uploaded content, download the file *without* .info at the end and open it with [7zip](https://www.7-zip.org/).
> You will be prompted to insert your password. The password is your EncryptionKey.

 ## Milestones
- [x] Split Video Stream and Processing in different Threads
- [x] Add Timestamps to the video output
- [x] Implement config.ini file
- [x] Add Pre- and PostRecording times to the video output
- [x] Implement GPS positioning
- [x] Add Whitelist to disable detection for other rescue vehicles
- [x] Optimize RAM usage (temporary saved frames take up lots of space right now)
- [x] Find a good solution to distribute the evidence (E-Mail, SFTP Server, etc.)
- [ ] Give an Option for manual capture
- [ ] Build Hardware Prototype
- [ ] Provide Build Instructions
- [ ] Add solutions to detect if the siren and emergency lights are active; display it in the frame
- [ ] 3D Print Case and provide files

## How it works
The *FrameManager* class temporarily stores all streamed frames, depending on the set FPS. 

The *FrameProcessor* class analyzes a Frame in 2 steps:
1. Run the YOLO Detection Model and search for number plates in the Frame
2. Run the fast_plate_ocr Model on the detected areas and capture the number plates text

The *FrameStorage* is used as a container. Whenever a number plate got selected to be saved, a new FrameStorage object gets created. It stores all relevant Frames and is responsible to create the final Video in a different Thread.

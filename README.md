# RescueLaneClipper
## Introduction
In countries like Germany, Austria and Swiss, it is mandatory for vehicles to form a rescue lane during traffic jams or slow-moving conditions on highways, allowing emergency vehicles to reach accident scenes without delay.

However, violations are difficult to enforce due to
- Lack of real-time documentation and evidence,
- Emergency responders needing to focus on saving lives, not monitoring traffic behaviour.

This project aims at automatically detecting and documenting obstructions of emergency vehicles using a camera installed inside the vehicle - similar to a dashcam.
Unlike a typical dashcam, this project is not build to detect crashes, but detect license plates that remain in the frame for long.

The project analyzes frames, detects number plates, reads the number plates with OCR and evaluates if the number plate got scanned before. The project can be customized through a config.ini file and uses basic logic like a Levenshtein ratio to tackle wrong OCR.

The finished project is planned to feature a open-source list of parts, 3D print files and more to rebuild and refine the project at home.

> [!NOTE]  
> This project is actively being developed and is not yet feature-complete. Expect changes, improvements, and new functionality over time. Feedback and contributions are welcome!

## Prerequisites
You will need Python3 and pip for this project.

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
- Install all external libraries: `pip install opencv-python Levenshtein fast_plate_ocr[onnx] ultralytics`

## Execution
- run the program: `python main.py`
  - You should see some output: "Warming up YOLO Model... Warm-up finished!"

> [!NOTE]  
> As this project is actively being developed, currently it does not yet accept a webcams livestream! It uses example videos like [this one](https://www.youtube.com/watch?v=M6Rtz2CiY2c).
> The video can be downloaded via 3D Youtube Downloader and is expected to be under the path "./tests/insideView.mp4".

 ## Milestones
- [x] Split Video Stream and Processing in different Threads
- [x] Add Timestamps to the video output
- [x] Implement config.ini file
- [x] Add Pre- and PostRecording times to the video output
- [ ] Implement GPS positioning
- [ ] Build Hardware Prototype
- [ ] Provide Build Instructions
- [ ] 3D Print Case and provide files

## How it works
The *FrameManager* class temporarily stores all streamed frames, depending on the set FPS. 

The *FrameProcessor* class analyzes a Frame in 2 steps:
1. Run the YOLO Detection Model and search for number plates in the Frame
2. Run the fast_plate_ocr Model on the detected areas and capture the number plates text

The *FrameStorage* is used as a container. Whenever a number plate got selected to be saved, a new FrameStorage object gets created. It stores all relevant Frames and is responsible to create the final Video in a different Thread.

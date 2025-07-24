import time
from ultralytics import YOLO
from fast_plate_ocr import LicensePlateRecognizer
from collections import defaultdict, deque
from FrameProcessor import FrameProcessor
from FrameManager import FrameManager, FrameStorage, Frame
from configparser import ConfigParser
import numpy as np

if __name__ == "__main__":
    config = ConfigParser()
    config.read("config.ini")

    # Create Models for use in FrameProcessor
    ocrModel = LicensePlateRecognizer(config["FrameProcessor"]["OCRModel"]) # type: ignore
    yoloModel = YOLO(config["FrameProcessor"]["YOLOModel"], verbose=False)


    # Warm-up yoloModel with dummy frame
    # more on this issue: https://github.com/ultralytics/ultralytics/issues/14332#issuecomment-2221024314
    print("Warming up YOLO Model...")
    yoloModel.predict(source=np.zeros((640, 640, 3), dtype=np.uint8), save=False, verbose=False)
    print("Warm-up finished!")


    startTime = time.time()
    processed_frames = 0

    detection_threshold = int(config["Algorithm"]["DetectionThreshold"])  # How many times does the number plate have to be detected in the last queuedFrames time period to be collected?
    last_plates = deque(maxlen=int(config["Algorithm"]["LastPlatesFrameStorageLength"]))  # store plates of the last x frames (x = maxlen)

    all_detected_plates = []

    resultDir = config["Setup"]["ResultDir"]
    levenshtein_threshold = config["Algorithm"]["LevenshteinThreshold"]

    temporaryFrameStorage: dict[str, FrameStorage] = {}

    fm = FrameManager(config)
    fm.start()

    while True:
        frame: Frame = fm.getCurrentFrame()

        if frame is None:
            continue  # End of video

        print(" -- Processing frame {0} -- ".format(processed_frames))
        processed_frames += 1

        if not fm.running:
            break

        # Process Frame
        frameProc = FrameProcessor(frame.frame, all_detected_plates, ocrModel, yoloModel, config)
        plates, previewImage = frameProc.processFrame()
        last_plates.append(plates)


        for plate in plates:
            if plate not in all_detected_plates:
                all_detected_plates.append(plate)

        # Group the plates that got detected to get its frequency in the last x analyzed frames
        plate_indexes = defaultdict(list)
        for idx, frame_detections in enumerate(last_plates):
            for plate in frame_detections:
                plate_indexes[plate].append(idx)

        # Filter to only those with multiple detections
        duplicates = {plate: indexes for plate, indexes in plate_indexes.items() if len(indexes) > detection_threshold}
        if len(duplicates) > 0:
            for plate, indexes in duplicates.items():
                if plate not in temporaryFrameStorage:  # If not yet known, create a new FrameStorage for a new clip
                    temporaryFrameStorage[plate] = FrameStorage(config, previewImage)
                    temporaryFrameStorage[plate].addFrames(fm.getLastFrames(config.getint("OutputVideo", "PreRecordingTime")))  # add the right amount of frames before
                else:
                    storage = temporaryFrameStorage[plate]
                    if plate in plates:  # If the plate got spotted in the current frame, update the "lastSeen" parameter and add all unsavedFrames
                        storage.lastSeen = time.time()
                        storage.addFrames(fm.getUnsavedFrames(storage.frames[len(storage.frames) - 1].frameID))
                    else:  # If the plate didn't get spotted in the current frame, still add parts as long as the time since lastSeen is lower than the set time in PostRecordingTime
                        if time.time() - storage.lastSeen < config.getint("OutputVideo", "PostRecordingTime"):
                            storage.addFrames(fm.getUnsavedFrames(storage.frames[len(storage.frames) - 1].frameID))

        # Check if temporary Storage holds values that are older
        tmpDict = temporaryFrameStorage.copy()  # Because you can't pop values while iterating through the dict, we copy the original, pop from the copy and replace the original after iterating
        for key, value in temporaryFrameStorage.items():
            if not key in duplicates:
                path = resultDir + key + "/"
                temporaryFrameStorage[key].createVideo(path, fm.getFPS())
                tmpDict.pop(key)
        temporaryFrameStorage = tmpDict

    # When while loop got broken, finalize all not saved FrameStorage objects
    for key, frameStorage in temporaryFrameStorage.items():
        frameStorage.createVideo(resultDir + key + "/", fm.getFPS())

    endTime = time.time()

    processDuration = endTime - startTime

    fm.stop()

    print(f"\nProcessed {processed_frames} frames in {processDuration:.2f} seconds")
from collections import deque
from configparser import ConfigParser
import threading, os, cv2, time, datetime, serial, numpy as np


class FrameManager(threading.Thread):
    def __init__(self, config: ConfigParser):
        super().__init__()
        self.config: ConfigParser = config

        self.running = True
        self.lock = threading.Lock()

        self.fps = float(self.config["FrameManager"]["FPS"])
        self.streamWidth = config["FrameManager"]["Width"]
        self.streamHeight = config["FrameManager"]["Height"]

        self.gpsAllowed = config.getboolean("Setup", "EnableGPS")
        if self.gpsAllowed:
            try:
                self.gps = serial.Serial("/dev/ttyACM0", baudrate=9600)  # Note: this method only works on raspberry pi!
            except:
                self.gps = None
        else:
            self.gps = None

        self.frames = deque(maxlen=int(self.fps * float(self.config["FrameManager"]["TemporaryStorageTime"])))
        self.currentFrame: Frame = None
        self.currentFrameID = 0

        self.startTime = 0
        self.lastFrameTime = 0

        self.video_path = "./tests/insideView.mp4"

    #TODO function not tested yet!
    def getCoordinates(self):  # https://machinelearningsite.com/gps-data-in-raspberry-pi/
        if self.gpsAllowed and self.gps is not None:
            line = self.gps.readline()
            decoded_line = line.decode('utf-8')
            data = decoded_line.split(",")
            try:
                if data[0] == "$GPRMC":
                    lat_nmea = str(data[3])
                    dd = float(lat_nmea[:2])
                    mmm = float(lat_nmea[2:])/60
                    latitude = dd + mmm

                    long_nmea = str(data[5])
                    dd = float(long_nmea[:3])
                    mmm = float(long_nmea[3:])/60
                    longitude = dd + mmm
                    return longitude, latitude
                else:
                    return 0, 0
            except:
                return 0, 0
        else:
            return 0, 0

    def run(self):
        cap = cv2.VideoCapture(self.video_path)

        self.startTime = time.time()
        while self.running:
            if not cap.isOpened():
                print("Error opening video file")
                self.stop()
                break

            ret, frame = cap.read()
            if not ret:
                print("finished video.")
                self.stop()  # No more frames, or error reading frame
                break

            # Optional: Display Stream Live in a separate window; for debugging purposes
            #cv2.imshow('Monitor Stream', frame)
            #cv2.waitKey(1)

            frame = Frame(frame, self.currentFrameID)
            if self.gpsAllowed:
                longitude, latitude = self.getCoordinates()
                frame.longitude = longitude
                frame.latitude = latitude

            with self.lock:
                self.currentFrame = frame
                self.frames.append(frame)
                self.currentFrameID += 1
                self.lastFrameTime = time.time()
            while time.time() - self.lastFrameTime < (1 / self.fps):  # Wait for next frame as long as needed (more accurate than time.sleep() as it accounts for any processing time)
                pass

    def getFPS(self):
        """
        :return: Returns the currently achieved Live FPS. Does NOT return the self.fps property because that is just the aimed for value but not the real one.
        """
        currTime = time.time()
        timeTaken = currTime - self.startTime

        return self.currentFrameID / timeTaken

    def getCurrentFrame(self):
        """
        :return: Returns the most recent frame or None if there is no frame yet
        """
        with self.lock:
            return self.currentFrame if self.currentFrame is not None else None

    def getCurrentFrameID(self):
        """
        :return: Returns the currentFrameID
        """
        with self.lock:
            return self.currentFrameID

    def getLastFrames(self, timeInSeconds = None):
        """
        :param timeInSeconds: optional, time in seconds to get returned
        :return: list of frames
        """
        with self.lock:
            if timeInSeconds is None:
                return list(self.frames)
            else:
                returningFrames = int(timeInSeconds * self.fps)
                if returningFrames > self.frames.maxlen:
                    return list(self.frames)
                frameList = []
                counter = 0

                fullFrameList = list(self.frames)
                fullFrameList.reverse()
                frame: Frame
                for frame in fullFrameList:
                    if counter > returningFrames:
                        break
                    if frame is None:
                        print("frame is none!")
                    else:
                        frameList.append(frame)
                        counter += 1
                frameList.reverse()
                return frameList

    def getUnsavedFrames(self, frameID):
        """Get all available frames that are newer than the given ID
        """
        frames = self.getLastFrames()

        with self.lock:
            resFrames = []
            frame: Frame
            for frame in frames:
                if frame.frameID > frameID:
                    resFrames.append(frame)

            return resFrames

    def stop(self):
        cv2.destroyAllWindows()
        self.running = False


class Frame:
    def __init__(self, frame, frameID):
        self.compressedFrame = self._compressFrame(frame, 95)
        self.frameID = frameID

        self.longitude = None
        self.latitude = None

        self.creationTime = datetime.datetime.now()

    def _compressFrame(self, frame, quality=80):
        _, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return encoded.tobytes()

    def getFrame(self):
        jpeg_array = np.frombuffer(self.compressedFrame, dtype=np.uint8)
        return cv2.imdecode(jpeg_array, cv2.IMREAD_COLOR)

class FrameStorage:
    def __init__(self, config, plate, previewImage=None):
        self.frames: list[Frame] = []
        self.config: ConfigParser = config
        self.plateNumber = plate
        self.previewImage = previewImage
        self.creationTime = time.time()  # Used to track the MaximumClipTime
        self.lastSeen = time.time()  # Used to track the PostRecordingTime; reset when the number plate gets detected again

    def addFrame(self, frame):
        self.frames.append(frame)

    def addFrames(self, frames: list):
        self.frames.extend(frames)

    def createVideo(self, path, fps):
        process = threading.Thread(target=self._workerCreateVideo, args=(self.frames, self.previewImage, path, fps,))
        process.start()

    def _draw_timestamp(self, frame, datetimeStr, frameNumber, latitude=None, longitude=None):
        overlay_text = f"{datetimeStr} | Frame: {frameNumber:04d}"

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 1
        padding = 10  # Padding inside the black box

        text_size, _ = cv2.getTextSize(overlay_text, font, font_scale, font_thickness)
        text_width, text_height = text_size

        # Define rectangle coordinates to reach the frame's right and bottom edges
        x_start = frame.shape[1] - text_width - padding * 2
        y_start = frame.shape[0] - text_height - padding * 2
        x_end = frame.shape[1]
        y_end = frame.shape[0]

        # Draw black rectangle flush to bottom-right
        cv2.rectangle(frame,
                      (x_start, y_start),
                      (x_end, y_end),
                      (0, 0, 0),
                      thickness=-1)

        # Draw white text with padding inside the box
        text_x = x_start + padding
        text_y = y_end - padding
        cv2.putText(frame,
                    overlay_text,
                    (text_x, text_y),
                    font,
                    font_scale,
                    (255, 255, 255),
                    font_thickness,
                    cv2.LINE_AA)

        if latitude is not None and longitude is not None:
            coord_text = f"Lat.: {latitude:.6f} | Long.: {longitude:.6f}"
            coord_size, _ = cv2.getTextSize(coord_text, font, font_scale, font_thickness)
            coord_width, coord_height = coord_size

            coord_x_start = 0
            coord_y_start = frame.shape[0] - coord_height - padding * 2
            coord_x_end = coord_width + padding * 2
            coord_y_end = frame.shape[0]

            cv2.rectangle(frame, (coord_x_start, coord_y_start), (coord_x_end, coord_y_end), (0, 0, 0), thickness=-1)
            cv2.putText(frame, coord_text, (coord_x_start + padding, coord_y_end - padding),
                        font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

    def _workerCreateVideo(self, frames: list, previewImage, path, fps):
        if len(frames) > 0:
            # Add timestamp and optional location data to the frames
            updatedFrames = []
            counter = 1
            frame: Frame
            for frame in frames:
                datetime_str = frame.creationTime.strftime("%d.%m.%Y, %H:%M:%S,%f")
                datetime_str = datetime_str[:-3]  # chop of last digits of milliseconds
                copiedFrame = frame.getFrame().copy()  # Important to copy the original frame, as the original gets shared over multiple video sequences that have overlapping timelines
                self._draw_timestamp(copiedFrame, datetime_str, counter, frame.longitude, frame.latitude)
                updatedFrames.append(copiedFrame)
                counter += 1

            frames = updatedFrames

            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            videoName = self.config["OutputVideo"]["VideoName"]
            videoPath = os.path.join(path, videoName + ".mp4")
            if not os.path.exists(videoPath):
                height, width, channels = frames[0].shape
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(videoPath, fourcc, fps,
                                      (width, height))
                for frame in frames:
                    out.write(frame)
                out.release()
        if previewImage is not None:
            imageName = self.config["PreviewImage"]["PreviewImageName"]
            imagePath = os.path.join(path, imageName + ".png")
            if not os.path.exists(imagePath):
                cv2.imwrite(path + self.config["PreviewImage"]["PreviewImageName"] + ".png", previewImage)

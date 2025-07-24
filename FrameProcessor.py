import cv2, Levenshtein, ast
from configparser import ConfigParser

class FrameProcessor:
    def __init__(self, frame: cv2.Mat, allDetectedPlates: list[str], ocrModel, yoloModel, config):
        self.frame: cv2.Mat = frame
        self.allDetectedPlates: list[str] = allDetectedPlates

        self.ocrModel = ocrModel
        self.yoloModel = yoloModel

        self.config: ConfigParser = config

    def _findNumberPlates(self):
        """Tries to find all number plates in the image via YOLO and returns a List of all parts of the image
        """
        detections = self.yoloModel.predict(self.frame, verbose=False)
        return detections

    def _getNumberPlateText(self, detectedAreas: list):
        """Tries to detect the number plate text inside the detectedAreas
        """
        plates = []

        if self.config.getboolean("PreviewImage", "SavePreviewImage"):
            plottedImage = self.frame.copy()
        else:
            plottedImage = None
        for area in detectedAreas:  # detections is a list of Results objects
            for detection in area.boxes:
                x1, y1, x2, y2 = map(int, detection.xyxy[0])
                plate_region = self.frame[y1:y2, x1:x2]

                # Run OCR
                plate = self.ocrModel.run(plate_region)
                if len(plate) > 0:
                    filteredPlate = plate[0].replace("_", "")
                    if self.config.getboolean("PreviewImage", "SavePreviewImage"):
                        boxColor = ast.literal_eval(self.config.get("PreviewImage", "BoxColor", fallback="(0, 0, 255)"))# Color for the preview images boxes
                        textColor = ast.literal_eval(self.config.get("PreviewImage", "TextColor", fallback="(0, 0, 255)")) # Color for the preview images boxes
                        if self.config.getboolean("PreviewImage", "EnableBox"):
                            cv2.rectangle(plottedImage, (x1, y1), (x2, y2), color=boxColor, thickness=2)
                        if self.config.getboolean("PreviewImage", "EnableText"):
                            cv2.putText(plottedImage, filteredPlate, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, textColor, 1)
                    plates.append(filteredPlate)
                    print(filteredPlate)
        plateResult = []
        for plate in plates:
            res = self._findSimilarPlate(plate)
            if res is None:
                plateResult.append(plate)
            else:
                plateResult.append(res)
        return plateResult, plottedImage
    
    def _findSimilarPlate(self, currentPlate, threshold=0.8):
        bestMatch = None
        bestRatio = 0.0

        for plate in self.allDetectedPlates:
            ratio = Levenshtein.ratio(currentPlate, plate)
            if ratio > bestRatio and ratio >= threshold:
                bestMatch = plate
                bestRatio = ratio
        return bestMatch

    def processFrame(self):
        detectedAreas = self._findNumberPlates()
        return self._getNumberPlateText(detectedAreas)

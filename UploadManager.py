import os, shutil, uuid
import py7zr
import traceback
from configparser import ConfigParser
from tusclient import client
from urllib import request
import threading, time


def checkConnection(uploadServer, uploadPort):
    try:
        url = "http://{0}:{1}".format(uploadServer, uploadPort)
        request.urlopen(url, timeout=1)
        return True
    except:
        return False

def checkIfFileSizeStable(filepath, stableTime = 2.0):
    """
    Checks if a file or folder has stopped growing in size. Used because the final .mp4 files will be created by cv2
    but are still growing in size, until they are fully finished processing
    :param filepath: The path to the file or folder to check on
    :param stableTime: The time that the file or folder needs to stay at the same size
    :return:
    """
    try:
        startSize = os.path.getsize(filepath)
    except FileNotFoundError:
        return False
    startTime = time.time()

    while time.time() - startTime < stableTime:
        try:
            currSize = os.path.getsize(filepath)
        except FileNotFoundError:
            return False

        if currSize != startSize:
            return False
    return True

def getFolderName(baseName):
    random = str(uuid.uuid1()).replace("-", "")[:16]  # get random string that is 16 chars long
    return baseName + "_" + random


class UploadManager(threading.Thread):
    def __init__(self, config: ConfigParser):
        super().__init__()
        self.config: ConfigParser = config

        self.running = True
        self.lock = threading.Lock()

    def run(self):
        uploadServer = self.config.get("Upload", "Server")
        uploadPort = self.config.getint("Upload", "UploadPort")
        encryptionKey = self.config.get("Upload", "EncryptionKey")
        resultsDir = self.config.get("Setup", "ResultDir")

        fullURL = "http://{0}:{1}/files/".format(uploadServer, uploadPort)

        while self.running:
            if checkConnection(uploadServer, uploadPort):
                for file in os.listdir(resultsDir):
                    if file.endswith(".7z"):
                        filePath = os.path.join(resultsDir, file)
                        tusClient = client.TusClient(fullURL)

                        uploadFinished = False

                        with open(filePath, "rb") as f:
                            currentURLFile = filePath + ".url"
                            if os.path.exists(currentURLFile):  # If there is a upload that did not complete yet, continue
                                with open(currentURLFile, "r") as urlFile:
                                    uploadURL = urlFile.read().strip()
                                uploader = tusClient.uploader(file_stream=f, chunk_size=5242880, url=uploadURL, metadata={"filename": file})
                                print("used existing url")
                            else:  # If there is no uncompleted upload, go on
                                uploader = tusClient.uploader(file_stream=f, chunk_size=5242880, metadata={"filename": file})
                                uploadURL = uploader.create_url()
                                print("created url")

                            with open(currentURLFile, "w") as urlFile:
                                urlFile.write(uploadURL)

                            print(f"Uploading {file}...")

                            try:
                                # Perform the upload
                                uploader.upload()
                                uploadFinished = True
                            except:
                                traceback.print_exc()
                                uploadFinished = False

                        try:
                            os.remove(currentURLFile)

                            uploadFinishedFolder = resultsDir + "/uploadFinished/"
                            if not os.path.exists(uploadFinishedFolder):
                                os.mkdir(uploadFinishedFolder)

                            fullFolderPath = filePath.replace(".7z", "")

                            # Create unique new name for folder
                            newFolderName = getFolderName(os.path.basename(fullFolderPath))
                            while os.path.exists(uploadFinishedFolder + newFolderName):
                                newFolderName = getFolderName(os.path.basename(newFolderName))

                            shutil.move(fullFolderPath, uploadFinishedFolder + newFolderName)  # move source folder

                            os.remove(filePath)  # remove temporarily created .7z file

                            print(f"Done: {file}")
                        except:
                            traceback.print_exc()

            if os.path.exists(resultsDir):
                for file in os.listdir(resultsDir):  # Encrypt all folders that aren't zipped already
                    filePath = os.path.join(resultsDir, file)
                    if os.path.exists(filePath) and os.path.isdir(filePath) and file != "uploadFinished":
                        if "{0}.7z".format(filePath) not in os.listdir(resultsDir):
                            if checkIfFileSizeStable(filePath):
                                with py7zr.SevenZipFile(filePath + ".7z", "w", password=encryptionKey) as archive:
                                    archive.writeall(filePath, arcname=file)


    def stop(self):
        self.running = False
# Tibetan OCR local app

This app is a free and open source offline App that can be installed on a local compter to run Tibetan OCR on batches of images (including in PDFs). It was developed by Eric Werner for the [Buddhist Digital Resource Center](https://www.bdrc.io).

### Main features

The app can open one or multiple files and run OCR on them. It can export plain text or [PageXML](https://github.com/PRImA-Research-Lab/PAGE-XML) (a format it shares with [Transkribus](https://www.transkribus.org/)). 

It can also optionally dewarp images as well as convert the output to Wylie.

Instead of providing one model that can handle all styles of Tibetan writing, we provide a few different models that we encourage users to experiment with to see what fits their data best.

The models it uses are based on transcriptions available online, from BDRC, [ALL](https://asianlegacylibrary.org/), [Adarsha](https://adarshah.org/), and [NorbuKetaka](http://purl.bdrc.io/resource/PR1ER1), as well as some transcriptions by [MonlamAI](https://monlam.ai/) and the author. The data was organized and processed in collaboration with MonlamAI, and parts of it can be made available on request.

### Installation and running

##### Windows

1. Download and unzip https://github.com/buda-base/tibetan-ocr-app/releases/download/v0.1/bdrc_ocr_win64_0.1.zip
2. Run `bdrc.exe`

##### OSX

This app does not have a package for OSX at the moment. If you're an experienced OSX developer and want to help us build one, please contact us by opening an issue.

##### From source (advanced users)

1. Make sure you have [Git LFS](https://git-lfs.com) installed
2. Clone the Github repository: `git clone https://github.com/buda-base/tibetan-ocr-app.git`
3. run `git lfs pull` to download all LFS files
4. run `pyside6-rcc resources.qrc -o resources.py`
5. Install dependencies with `pip install -r requirements.txt` (requires at least Python 3.10)
6. Run `python main.py`

### Configuring the models

1. Download and unzip https://github.com/buda-base/tibetan-ocr-app/releases/download/v0.1/bdrc-ocr-app-models.zip in a directory of your choice
2. Once the app opens, click on the setting icon, click on "import models" and select the `ORCModels/` folder where you extracted the model zip file. Warning! Do not select one of its subfolders (like `Woodblock/`, etc.).
3. Then quit the app and run it again so that the models can be used.

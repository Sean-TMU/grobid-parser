# grobid-parser

![Vercel](https://img.shields.io/badge/vercel-%23000000.svg?style=for-the-badge&logo=vercel&logoColor=white)

A tool that can process scholarly literature into structured dataset.

## Setting
* You need to prepare a Python environment in your computer. My execution environment `python 3.10.15`.
* Install required Python packages via `pip install -r requirements.txt`. For your convinence, I recommend you install package under conda virtual environment.
* We can use [demo site](https://kermitt2-grobid.hf.space/) to parse pdf file, so there is no need to start GROBID server in background.

## Prerequisites
* You need to prepare a academic paper in PDF format, and upload it through web interface.
* You need to setup following options in `.env` file.
```
GROBID_URL=<your-grobid-server-url>
STATIC_FOLDER=<path-to-STATIC-directory>
```

## Usage
1. Start the Flask application
```
python app.py
```
2. Open a web browser and navigate to `http://localhost:5000`

3. Upload a PDF file through the web interface

4. The application will process the PDF and provide:
   - Success/failure notification
   - A portion of the content in the parsed results
   - Option to download the parsed results as CSV
# grobid-parser
> A tool that can process scholarly literature into structured dataset.

### Setting
* You need to prepare a Python environment in your computer. My execution environment `python 3.10.15`.
* Use pip install -U requirements.txt command to install package dependency. For your convinence, I recommend you install package under conda virtual environment.
* Create `debug.log` file under logging folder. We can use [demo site](https://kermitt2-grobid.hf.space/) to parse pdf file, so there is no need to start GROBID server in background.

### Prerequisites
1. You need to upload original pdf file and setting `GROBID_URL` in `.env` file. The program will generate a xml file that generated by GROBID service and place under `out/` subfolder.
2. After execute the program, it will generate a csv file named `processed_results.csv` under the folder you declared in `--output` option.

### Usage
* The option you can use when execute the `grobid_parse.py`
```
root@ba932d27069e:/workspace/preprocessing# python grobid_parse.py --help
usage: grobid_parse.py [-h] [-f FOLDER] [-o OUTPUT]

Process scholarly literature into structured dataset

options:
  -h, --help            show this help message and exit
  -f FOLDER, --folder FOLDER
                        Folder path to store pdf files
  -o OUTPUT, --output OUTPUT
                        Folder name to stored csv format output
```

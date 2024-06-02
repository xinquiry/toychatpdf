# ToyChatPDF

This project use the open-source project marker and give a gui to it.

To use cpu, you should change the `TORCH_DEVICE: Option[str] = "cuda"` to `TORCH_DEVICE: Option[str] = "default"` in `marker/settings.py`.

# Installation

This has been tested on Mac and Linux (Ubuntu and Debian).  You'll need python 3.9+ and [poetry](https://python-poetry.org/docs/#installing-with-the-official-installer).

First, clone the repo and then

- Install system requirements
  - Optional: Install tesseract 5 by following [these instructions](https://notesalexp.org/tesseract-ocr/html/) or running `scripts/install/tesseract_5_install.sh`.
  - Install ghostscript > 9.55 by following [these instructions](https://ghostscript.readthedocs.io/en/latest/Install.html) or running `scripts/install/ghostscript_install.sh`.
  - Install other requirements with `cat scripts/install/apt-requirements.txt | xargs sudo apt-get install -y`
- Set the tesseract data folder path
  - Find the tesseract data folder `tessdata` with `find / -name tessdata`.  Make sure to use the one corresponding to the latest tesseract version if you have multiple.
  - Create a `local.env` file in the root `marker` folder with `TESSDATA_PREFIX=/path/to/tessdata` inside it
- Install python requirements
  - `poetry install`
  - `poetry shell` to activate your poetry venv
- Update pytorch since poetry doesn't play nicely with it
  - GPU only: run `pip install torch` to install other torch dependencies.
  - CPU only: Uninstall torch with `poetry remove torch`, then follow the [CPU install](https://pytorch.org/get-started/locally/) instructions.

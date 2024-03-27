# COMP264 (Sec.002) - Group 5

This project call `VisionUltra`, this is for blink people to hear the document from different languages.

## Installation

To set up the environment, follow these steps:

1. Clone the repository:

```bash
git clone -b master https://github.com/hung940801/comp264_group5.git
cd comp264_group5
```

2. Install pipenv packages:

```bash
pipenv install
```

3. Run the pipenv shell:

```bash
pipenv shell
```

4. Get into the Capabilities folder and run the server:

```bash
cd Capabilities
chalice local
```

5. Open the application URL [http://127.0.0.1:8000](http://127.0.0.1:8000), then upload the document that wants to be translated and click the `Upload` button. The translated audio will be played automatically after the translation.
# Simple HTTP Extractor v0.1

### Usage

```
usage: html_convert.py [-h] [-v] [-o OUTPUT_DIR] pattern

Extract files from email messages and raw HTTP-responses

positional arguments:
  pattern               Pattern to match files using `glob.iglob`. Example:
                        'forum/index.php*'

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Increase verbosity of output
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Write files to directory, and create if not exist.
```

Take look into `sample` directory for some files to play with.


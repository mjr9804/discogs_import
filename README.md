# discogs_import

Parse a record collection in CSV format and upload it to a user's Discogs collection

## Installation

```
pip3 install -r requirements.txt
```

## Usage

```
./discogs_import.py [-h] [--limit NUM] [--skip NUM] username filename

positional arguments:
  username             Discogs username
  filename             Collection file in CSV format. The file must contain the following fields: Artist, Title, Year

optional arguments:
  -h, --help           show this help message and exit
  --limit NUM, -l NUM  Limit operations to the first NUM operations (default: 0/unlimited)
  --skip NUM, -s NUM   Skip operations for the first NUM rows (default: 0/unlimited)
```

### Example

```
./discogs_import.py mjr9804 albums.csv
Adding Bruce Springsteen - Born To Run...Done!
...
```

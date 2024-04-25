# fetch-sitemap

Retrieves all URLs of a given sitemap.xml URL and fetches each page one by one. 
Useful for (load) testing the entire site for error responses.

![Sample Output](https://raw.githubusercontent.com/bartTC/fetch-sitemap/main/example.png)

## Installation

```bash 
$ pip install fetch-sitemap
```


## Usage 

```
$ fetch-sitemap --help

 Usage: fetch-sitemap [OPTIONS] SITEMAP_URL

 Fetch a given sitemap and retrieve all URLs in it.

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --basic-auth         -a  TEXT       Basic auth information. Format: 'username:password'                            │
│ --limit              -l  INTEGER    Maximum number of URLs to fetch from the given sitemap.xml.                    │
│ --concurrency-limit  -c  INTEGER    Max number of concurrent requests. [default: 5]                                │
│ --request-timeout    -t  INTEGER    Timeout for fetching a URL in seconds. [default: 30]                           │
│ --random             -r             Append a random string like ?12334232343 to each URL to bypass frontend cache. │
│ --random-length          INTEGER    Length of the --random hash. [default: 15]                                     │
│ --report-path        -p  FILE       Store results in a CSV file. Example: ./report.csv                             │
│ --output-dir         -o  DIRECTORY  Store all fetched sitemap documents in this folder. Example:                   │
│                                     /tmp/my.domain.com/                                                            │
│ --slow-threshold         FLOAT      Responses slower than this (in seconds) are considered 'slow'. [default: 5.0]  │
│ --slow-num               INTEGER    How many 'slow' responses to show. [default: 10]                               │
│ --version            -v             Show the version and exit.                                                     │
│ --help                              Show this message and exit.                                                    │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## 🤺 Local Development

```bash
poetry install
poetry run fetch-sitemap -h
poetry run ./tests.sh
```
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

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --basic-auth                -a  TEXT              Basic auth information. Format: 'username:password'                                                          │
│ --limit                     -l  INT [>=1]         Maximum number of URLs to fetch from the given sitemap.xml.                                                  │
│ --recursive/--no-recursive                        Recursively fetch all sitemap documents from the given sitemap.xml. [default: recursive]                     │
│ --concurrency-limit         -c  INT [>=1]         Max number of concurrent requests. [default: 5; >=1]                                                         │
│ --request-timeout           -t  INT [>=1]         Timeout for fetching a URL in seconds. [default: 30; >=1]                                                    │
│ --random                    -r                    Append a random string like ?12334232343 to each URL to bypass frontend cache.                               │
│ --random-length                 INT [1 to 100]    Length of the --random hash. [default: 15; 1 to 100]                                                         │
│ --report-path               -p  FILE              Store results in a CSV file. Example: ./report.csv                                                           │
│ --output-dir                -o  DIRECTORY         Store all fetched sitemap documents in this folder. Example: /tmp/my.domain.com/                             │
│ --slow-threshold                FLOAT [>=0.0]     Responses slower than this (in seconds) are considered 'slow'. [default: 5.0; >=0.0]                         │
│ --slow-num                      INTEGER OR "ALL"  How many 'slow' responses to show. [default: 10]                                                             │
│ --user-agent                    TEXT              User-Agent string set in the HTTP header. [default: Mozilla/5.0 (compatible; fetch-sitemap/23)]              │
│ --version                                         Show the version and exit.                                                                                   │
│ --help                                            Show this message and exit.                                                                                  │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## 🤺 Local Development

```bash
poetry install
poetry run fetch-sitemap -h
poetry run ./tests.sh
```
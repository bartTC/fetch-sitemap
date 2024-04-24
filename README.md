# fetch-sitemap

Retrieves all URLs of a given sitemap.xml URL and fetches each page one by one. 
Useful for (load) testing the entire site for error responses.

![Sample Output](https://raw.githubusercontent.com/bartTC/fetch-sitemap/main/example.png)

*Note:* The default concurrency limit is 5, so five URLs are fetched at once. 
Depending on your server's worker count, this might already be enough to DoS it.
Try `--concurrency-limit=2` and increase if you feel comfortable.

```
Usage: fetch-sitemap [-h] [--basic-auth BASIC_AUTH] [-l LIMIT] [-c CONCURRENCY_LIMIT]
                     [-t REQUEST_TIMEOUT] [--random] [--report-path REPORT_PATH]
                     [-o OUTPUT] [-v]
                     sitemap_url

Fetch a given sitemap and retrieve all URLs in it.

Positional Arguments:
  sitemap_url           URL of the sitemap to fetch

Options:
  -h, --help            show this help message and exit
  --basic-auth BASIC_AUTH
                        Basic auth information. Use: 'username:password' (default: None)
  -l, --limit LIMIT     Maximum number of URLs to fetch from the given sitemap.xml
                        (default: None)
  -c, --concurrency-limit CONCURRENCY_LIMIT
                        Max number of concurrent requests (default: 5)
  -t, --request-timeout REQUEST_TIMEOUT
                        Timeout for fetching a URL in seconds (default: 30)
  --random              Append a random string like ?12334232343 to each URL to bypass
                        frontend cache (default: False)
  --report-path REPORT_PATH
                        Store results in a CSV file (example: ./report.csv) (default:
                        None)
  -o, --output-dir OUTPUT
                        Store all fetched sitemap documents in this folder (default: None)
  -v, --version         Show program's version number and exit
```


## 🤺 Local Development

```bash
poetry install
poetry run fetch-sitemap -h
poetry run ./tests.sh
```
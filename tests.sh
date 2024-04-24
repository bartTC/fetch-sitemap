#!/bin/bash
set -o errexit
set -o pipefail

ruff check fetch_sitemap
ruff format --check fetch_sitemap
tox -r
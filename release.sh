#!/bin/bash
set -o errexit
set -o pipefail

# Run tests before release
./test.sh

poetry version major
git add pyproject.toml && git commit -am "Bump up version number to v$(poetry version -s)}"
git tag "v$(poetry version -s)"
git push --tags
poetry build
poetry publish
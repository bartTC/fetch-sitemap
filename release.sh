#!/bin/bash
set -o errexit
set -o pipefail

# Run tests before release
./tests.sh

poetry version major
git add pyproject.toml && git commit -am "Bump up version number to v$(poetry version -s)"
VERSION="v$(poetry version -s)"
git tag $VERSION
git push
git push --tags
gh release create --generate-notes --latest --title=v24 v24
poetry build
poetry publish

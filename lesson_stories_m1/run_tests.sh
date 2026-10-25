#!/usr/bin/env bash
# Zero dependencies: uses the standard-library unittest. (pytest also works: `pytest tests/unit`)
cd "$(dirname "$0")" && python3 -m unittest discover -s tests/unit -v

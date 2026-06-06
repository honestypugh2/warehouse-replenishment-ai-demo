# CI is defined in .github/workflows/ci.yml so GitHub Actions picks it up.
# This file documents the pipeline stages referenced in the architecture docs.
#
# Stages:
#   1. lint      — ruff (Python) + tsc --noEmit (frontend)
#   2. test      — pytest (unit + integration, MOCK_MODE=true)
#   3. evaluate  — run the evaluation harness (groundedness, decision quality)
#   4. build     — frontend production build
#
# See: ../../.github/workflows/ci.yml

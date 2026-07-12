# Standalone verification

This repository is verified independently from CrumbLLM.

GitHub CI must prove the following on Python 3.10, 3.11, and 3.12:

- the package installs from the repository root;
- all tests pass;
- the offline benchmark self-check passes;
- 31/31 bundled exact anchors are preserved;
- the interactive report and share card are generated;
- the wheel and source distribution build successfully;
- `twine check` accepts both distributions.

CodeQL runs separately on pushes, pull requests, and its scheduled scan.

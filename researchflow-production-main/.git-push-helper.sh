#!/bin/bash
# Git Push Helper - Unsets invalid GITHUB_TOKEN and uses gh CLI credentials

# Temporarily unset GITHUB_TOKEN to use gh CLI keyring
unset GITHUB_TOKEN

# Run git push with all arguments passed to this script
git push "$@"

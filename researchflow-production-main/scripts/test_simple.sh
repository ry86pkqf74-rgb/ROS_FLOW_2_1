#!/bin/bash
set -euo pipefail

var_name="POSTGRES_HOST"
var_value="${!var_name:-}"

if [[ -z "$var_value" ]]; then
    echo "ERROR: Variable not set"
    exit 1
fi

echo "Variable $var_name = $var_value"

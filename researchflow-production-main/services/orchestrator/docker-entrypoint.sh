#!/bin/sh
set -e

# Fix workspace:* references for npm compatibility (pnpm-only feature)
echo "Converting workspace:* references for npm..."
sed -i 's/"workspace:\*"/"file:.\/packages\/core"/g' /app/package.json
sed -i 's/"@researchflow\/ai-router": "file:\.\/packages\/core"/"@researchflow\/ai-router": "file:.\/packages\/ai-router"/g' /app/package.json
sed -i 's/"@researchflow\/manuscript-engine": "file:\.\/packages\/core"/"@researchflow\/manuscript-engine": "file:.\/packages\/manuscript-engine"/g' /app/package.json
sed -i 's/"@researchflow\/notion-integration": "file:\.\/packages\/core"/"@researchflow\/notion-integration": "file:.\/packages\/notion-integration"/g' /app/package.json
sed -i 's/"@researchflow\/phi-engine": "file:\.\/packages\/core"/"@researchflow\/phi-engine": "file:.\/packages\/phi-engine"/g' /app/package.json

# Check if node_modules is missing key dependencies (volume mount case)
if [ ! -d "/app/node_modules/express" ] || [ ! -d "/app/node_modules/bcryptjs" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Always sync @researchflow packages from image to node_modules
# This ensures latest code is used even when volume has cached packages
echo "Syncing @researchflow packages..."
mkdir -p ./node_modules/@researchflow
rm -rf ./node_modules/@researchflow/core ./node_modules/@researchflow/phi-engine ./node_modules/@researchflow/ai-router ./node_modules/@researchflow/manuscript-engine ./node_modules/@researchflow/notion-integration
cp -r ./packages/core ./node_modules/@researchflow/core
cp -r ./packages/phi-engine ./node_modules/@researchflow/phi-engine
cp -r ./packages/ai-router ./node_modules/@researchflow/ai-router
cp -r ./packages/manuscript-engine ./node_modules/@researchflow/manuscript-engine
cp -r ./packages/notion-integration ./node_modules/@researchflow/notion-integration 2>/dev/null || true

exec "$@"

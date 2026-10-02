#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting Bridge Telephony Frontend Deployment..."

# Get the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
# Assuming standard bench structure: apps/bridge_telephony/deploy_frontend.sh -> apps/crm/crm/www
CRM_WWW_DIR="$SCRIPT_DIR/../crm/crm/www"
BRIDGE_PUBLIC_DIR="$SCRIPT_DIR/bridge_telephony/public/frontend"

# Check if CRM directory exists
if [ ! -d "$CRM_WWW_DIR" ]; then
    echo "❌ Error: CRM app not found at $CRM_WWW_DIR"
    echo "   Please ensure you are running this in a bench environment where 'crm' app is installed."
    exit 1
fi

echo "📦 Building Frontend..."
cd "$FRONTEND_DIR"

# Install dependencies
echo "   Installing dependencies..."
yarn install

# Run custom build script
echo "   Running custom build script..."
node custom-build.cjs

# Build with increased memory limit
echo "   Building with Vite..."
NODE_OPTIONS="--max-old-space-size=8192" yarn build

echo "✅ Build complete."

# Copy index.html to CRM
echo "🔄 Installing custom frontend to CRM..."
if [ -f "$BRIDGE_PUBLIC_DIR/index.html" ]; then
    # Backup existing crm.html if it's not a symlink or already our version (optional, skipping for now to keep it simple)
    cp "$BRIDGE_PUBLIC_DIR/index.html" "$CRM_WWW_DIR/crm.html"
    echo "   Copied index.html to $CRM_WWW_DIR/crm.html"
else
    echo "❌ Error: Build artifact index.html not found at $BRIDGE_PUBLIC_DIR/index.html"
    exit 1
fi

echo "🧹 Clearing cache..."
# Navigate to bench root (assuming apps/bridge_telephony/deploy_frontend.sh)
cd "$SCRIPT_DIR/../../.."
if command -v bench &> /dev/null; then
    bench --site all clear-cache
    echo "   Cache cleared."
else
    echo "⚠️  'bench' command not found. Please run 'bench clear-cache' manually."
fi

echo "✨ Deployment successfully completed!"
echo "   Please refresh your browser (Ctrl+Shift+R) to see changes."

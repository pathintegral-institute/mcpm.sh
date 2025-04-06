#!/bin/bash

echo -e "\n📦 Setting up mcpm.sh development environment...\n"

# Check if Docker is installed and running
if ! docker info &> /dev/null; then
    echo "❌ Docker is required but not running. Please start Docker and try again."
    exit 1
fi

# Check if fswatch is installed, if not install it
if ! command -v fswatch &> /dev/null; then
    echo "🔄 Installing fswatch..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install fswatch
    else
        echo "❌ fswatch is required but not installed. Please install it manually for your system."
        exit 1
    fi
fi

# Cleanup previous development files
echo -e "🗑️ Cleaning up previously generated files...\n"
rm -rf pages/api/servers
rm -f pages/api/servers.json
rm -rf pages/registry/servers

# Create and clean _dev directory
DEV_DIR="_dev"
echo -e "🔄 Setting up development directory in $DEV_DIR\n"
mkdir -p "$DEV_DIR"

# First clear the directory to ensure clean state
rm -rf "$DEV_DIR"/*

# Copy pages directory structure with all content
echo -e "🔄 Copying site content to development directory...\n"
cp -r pages/* "$DEV_DIR"/

# Function to run prepare.sh
run_prepare() {
    echo -e "\n🔄 Changes detected, updating development environment..."
    cp -r pages/* "$DEV_DIR"/
    ./scripts/prepare.sh "$DEV_DIR"
    echo -e "✅ Update complete!\n"
}

# Run the common preparation script
mkdir -p "$DEV_DIR/registry"
./scripts/prepare.sh "$DEV_DIR"

echo -e "✅ Setup complete!\n"

echo -e "\n👀 Watching for changes in pages directory..."
echo -e "🌐 Starting Jekyll development server..."
echo "   Access the site at http://localhost:4000"
echo -e "   Press Ctrl+C to stop the server\n"

# Start fswatch in the background to watch for changes
fswatch -o pages | while read; do
    run_prepare
done &

# Start Jekyll dev server using Docker from the _dev directory
cd "$DEV_DIR" && docker run --rm -it \
  -v "$PWD:/srv/jekyll" \
  -p 4000:4000 \
  jekyll/jekyll:4.2.0 \
  jekyll serve --livereload || (echo -e "\nPort 4000 is already in use. Assuming development server is already running." && exit 0)

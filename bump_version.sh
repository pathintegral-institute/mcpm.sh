#!/bin/bash
# Script to bump the version in all places and create a git tag

# Check if a version number was provided
if [ $# -ne 1 ]; then
    echo "Usage: $0 NEW_VERSION"
    echo "Example: $0 1.1.0"
    exit 1
fi

NEW_VERSION=$1
VERSION_FILE="src/mcpm/version.py"

# Update the version file
echo '"""Single source of truth for MCPM version."""

__version__ = "'$NEW_VERSION'"' > $VERSION_FILE

# Commit the change
git add $VERSION_FILE
git commit -m "Bump version to $NEW_VERSION"

# Create and push the git tag
git tag -a v$NEW_VERSION -m "Version $NEW_VERSION release"

echo "Version updated to $NEW_VERSION"
echo "To push changes, run: git push && git push --tags"

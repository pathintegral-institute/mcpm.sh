# Development Guide for mcpm.sh

This guide covers how to set up and run the mcpm.sh website locally for development.

## Prerequisites

- [Docker](https://www.docker.com/get-started/) (for running Jekyll)
- [jq](https://stedolan.github.io/jq/download/) (for JSON processing)

## Quick Start

The easiest way to run the site locally is using the included development script:

```bash
./dev.sh
```

This script:
1. Processes server manifests into JSON files
2. Sets up the proper directory structure
3. Starts the Jekyll development server

The site will be available at http://localhost:4000 with live reloading enabled.

## Manual Development Setup

If you prefer to run the steps manually:

1. **Process the server manifests** - The automated script handles this for you, but you can examine the script to see how manifests are processed into API endpoints.

2. **Start the Jekyll server**:
   ```bash
   cd pages
   docker run --rm -it -v "$PWD:/srv/jekyll" -p 4000:4000 jekyll/jekyll:4.2.0 jekyll serve --livereload
   ```

## Making Changes

- **Website Changes**: Edit files in the `/pages` directory
- **Registry Changes**: Add or modify server manifests in `/mcp-registry/servers/<server-name>/manifest.json`

If you add a new server, run `./dev.sh` again to regenerate the JSON files.

## Testing Production Build

To test the production build that will be deployed to GitHub Pages:

```bash
cd pages
docker run --rm -it -v "$PWD:/srv/jekyll" jekyll/jekyll:4.2.0 jekyll build
```

The built site will be in `pages/_site/`.


## Debug mode for mcpm router
Set environment variable `MCPM_DEBUG` to `true` to enable debug mode.

```bash
export MCPM_DEBUG=true
```


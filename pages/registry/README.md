# mcpm.sh Website Pages

This directory contains the Jekyll website for mcpm.sh.

## Local Development

The mcpm.sh website is built using Jekyll. The easiest way to run the development server locally is using Docker, which avoids having to install Ruby and all dependencies on your machine.

### Prerequisites

- [Docker](https://www.docker.com/get-started/) installed and running

### Running the Dev Server

1. Start the Jekyll development server using Docker from this directory:
   ```bash
   docker run --rm -it -v "$PWD:/srv/jekyll" -p 4000:4000 jekyll/jekyll:4.2.0 jekyll serve --livereload
   ```

2. If port 4000 is already in use, you can specify a different port:
   ```bash
   docker run --rm -it -v "$PWD:/srv/jekyll" -p 4001:4000 jekyll/jekyll:4.2.0 jekyll serve --livereload
   ```

3. Access the site in your browser:
   - If using port 4000: http://localhost:4000
   - If using port 4001: http://localhost:4001

The server includes livereload functionality, so your browser will automatically refresh when you make changes to the site files.

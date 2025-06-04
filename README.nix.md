# MCPM Nix Packaging

This repository contains Nix packaging for MCPM (Model Context Protocol Manager).

## Using with Nix Flakes

If you have flakes enabled, you can use this package directly:

```bash
# Run MCPM directly
nix run .

# Install MCPM to your profile
nix profile install github:pathintegral-institute/mcpm.sh

# Enter a development shell
nix develop .
```

## Building from Source

To build the package from source:

1. Clone the repository:
   ```bash
   git clone https://github.com/pathintegral-institute/mcpm.sh
   cd mcpm.sh
   ```

2. Build the package:
   ```bash
   nix build
   ```

3. Run the built package:
   ```bash
   ./result/bin/mcpm --help
   ```

## Notes

- The nix package requires Python 3.12 or higher.


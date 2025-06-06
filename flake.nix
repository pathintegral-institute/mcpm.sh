{
  description = "MCPM - Model Context Protocol Manager";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config = {
            allowUnfree = true;
            permittedInsecurePackages = [ ];
          };
        };
      in
      {
        packages = {
          default = pkgs.callPackage ./default.nix { };
        };

        apps.default = flake-utils.lib.mkApp {
          drv = self.packages.${system}.default;
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.default ];

          buildInputs = with pkgs.python3.pkgs; [
            self.packages.${system}.default

            # From pyproject.toml's dev dependencies
            ipython
            pytest
            pytest-asyncio
            ruff
            jsonschema
            openai
          ];

          shellHook = ''
            echo "MCPM development environment"
          '';
        };
      }
    );
}

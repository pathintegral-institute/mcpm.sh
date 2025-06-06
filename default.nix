{
  lib,
  python3,
}:

let
  # Use Python 3.12
  python = python3; # pkgs.python312;

  # Override Python to include our custom packages
  pythonWithPackages = python.override {
    packageOverrides = self: super: {
      # Add our custom packages
    };
  };
in
pythonWithPackages.pkgs.buildPythonApplication rec {
  pname = "mcpm";
  version = "1.13.1"; # From src/mcpm/version.py

  src = ./.; # Use the local directory as the source

  format = "pyproject";

  nativeBuildInputs = with pythonWithPackages.pkgs; [
    hatchling
    setuptools
    wheel
    pip
  ];

  propagatedBuildInputs = with pythonWithPackages.pkgs; [
    # Core dependencies from pyproject.toml
    click
    rich
    requests
    pydantic
    duckdb
    psutil
    prompt-toolkit
    deprecated

    # dependencies only available for Python>=3.12 on nixpkgs
    mcp
    ruamel-yaml
    watchfiles

    # Additional dependencies that might be needed
    typer
    httpx
    anyio
    fastapi
    uvicorn
    websockets
    jinja2
    pyyaml
    toml
    python-dotenv
    packaging
    colorama
  ];

  # Disable tests for now
  #doCheck = false;

  meta = with lib; {
    description = "MCPM - Model Context Protocol Manager";
    homepage = "https://mcpm.sh";
    license = licenses.mit;
    maintainers = with maintainers; [ luochen1990 ];
    mainProgram = "mcpm";
  };
}

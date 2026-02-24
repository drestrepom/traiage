{
  description = "Triage - AI-powered SAST vulnerability validation";

  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-nix-src = {
      url = "github:pyproject-nix/pyproject.nix";
      flake = false;
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    let
      pyproject-nix-src = inputs.pyproject-nix-src;
      pyproject-build-systems = inputs.pyproject-build-systems;
      uv2nix = inputs.uv2nix;
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      perSystem =
        {
          inputs',
          pkgs,
          system,
          ...
        }:
        let
          inherit (pkgs) lib;
          workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
          overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
          python = pkgs.python314;
          pyproject-nix-build = lib.fix (
            self:
            import (pyproject-nix-src + "/build/default.nix") {
              inherit lib;
              pyproject-nix = self;
            }
          );
          pythonBase = pkgs.callPackage pyproject-nix-build.packages { inherit python; };
          triageSrcOverlay = final: prev: {
            triage = prev.triage.overrideAttrs (old: {
              src = ./.;
            });
          };
          pythonSet = pythonBase.overrideScope (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
              triageSrcOverlay
            ]
          );
          venv = pythonSet.mkVirtualEnv "triage-env" workspace.deps.all;
          owaspDocs = pkgs.fetchFromGitHub {
            owner = "OWASP";
            repo = "Top10";
            rev = "5e9a5a6e220f0280e866913617bb6e594dec6a60";
            hash = "sha256-4hVXJTYdnFZs+wjzHwBvR3F37BZTck1ZaGu6lrc/HEY=";
          };
        in
        {
          packages.default = venv;
          apps.triage = {
            type = "app";
            program = "${
              pkgs.writeShellApplication {
                name = "triage-wrapper";
                runtimeInputs = [
                  venv
                  pkgs.pandoc
                ];
                text = ''
                  export OWASP_DOCS_PATH="${owaspDocs}/2025/docs/en"
                  exec ${venv}/bin/triage "$@"
                '';
              }
            }/bin/triage-wrapper";
          };
          apps.lint = {
            type = "app";
            program = "${
              pkgs.writeShellApplication {
                name = "lint";
                runtimeInputs = [ venv ];
                text = ''
                  set -e
                  echo "Running ruff format..."
                  ${venv}/bin/ruff format src/
                  echo "Running ruff check --fix..."
                  ${venv}/bin/ruff check --fix src/
                  echo "Running mypy..."
                  ${venv}/bin/mypy src/
                  echo "All linting checks passed!"
                '';
              }
            }/bin/lint";
          };
          apps.test = {
            type = "app";
            program = "${
              pkgs.writeShellApplication {
                name = "test";
                runtimeInputs = [ venv ];
                text = ''
                  set -e
                  echo "Running unit tests..."
                  ${venv}/bin/pytest tests/unit/ -v -n auto
                  echo "Running integration & eval tests..."
                  ${venv}/bin/pytest tests/integration/ tests/evals/ -v -n auto
                  echo "All tests passed!"
                '';
              }
            }/bin/test";
          };
          devShells.default = pkgs.mkShell {
            inherit (venv) buildInputs;
            inputsFrom = [ venv ];
            packages = [
              pkgs.uv
              pkgs.pandoc
            ];
            shellHook = ''
              export OWASP_DOCS_PATH="${owaspDocs}/2025/docs/en"
            '';
          };
        };
    };
}

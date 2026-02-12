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

  outputs = inputs@{ flake-parts, ... }:
    let
      pyproject-nix-src = inputs.pyproject-nix-src;
      pyproject-build-systems = inputs.pyproject-build-systems;
      uv2nix = inputs.uv2nix;
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
      perSystem = { inputs', pkgs, system, ... }: let
        inherit (pkgs) lib;
        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
        overlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };
        python = pkgs.python314;
        pyproject-nix-build = lib.fix (self:
          import (pyproject-nix-src + "/build/default.nix") {
            inherit lib;
            pyproject-nix = self;
          }
        );
        pythonBase = pkgs.callPackage pyproject-nix-build.packages { inherit python; };
        torsimanyOverlay = final: prev: {
          torsimany = prev.torsimany.overrideAttrs (old: {
            nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ final.setuptools ];
          });
        };
        triageSrcOverlay = final: prev: {
          triage = prev.triage.overrideAttrs (old: { src = ./.; });
        };
        pythonSet = pythonBase.overrideScope (
          lib.composeManyExtensions [
            pyproject-build-systems.overlays.wheel
            overlay
            torsimanyOverlay
            triageSrcOverlay
          ]
        );
        venv = pythonSet.mkVirtualEnv "triage-env" workspace.deps.default;
      in {
        packages.default = venv;
        apps.triage = {
          type = "app";
          program = "${venv}/bin/triage";
        };
      };
    };
}

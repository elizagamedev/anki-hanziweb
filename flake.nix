{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-stable.url = "github:nixos/nixpkgs/nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, nixpkgs-stable, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pkgs-stable = nixpkgs-stable.legacyPackages.${system};
        aqt = p: p.callPackage ./aqt.nix { };
        python-with-my-packages = pkgs.python3.withPackages (p: with p; [
          (aqt p)
          python-lsp-server
          pylsp-mypy
          python-lsp-black
          pyls-isort
        ]);
      in
      {
        devShell = pkgs.mkShell
          {
            nativeBuildInputs = with pkgs; [
              pkgs-stable.clean-css-cli
              pkgs-stable.html-minifier

              black
              closurecompiler
              gnumake
              python-with-my-packages
              zip
            ];
          };
      }
    );
}

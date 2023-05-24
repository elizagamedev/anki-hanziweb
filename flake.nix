{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
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
              black
              gnumake
              python-with-my-packages
              zip
            ];
          };
      }
    );
}

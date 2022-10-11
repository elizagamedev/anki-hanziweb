{ pkgs ? import <nixpkgs> { } }:
let
  aqt = p: p.callPackage ./aqt.nix { };
  python-with-my-packages = pkgs.python3.withPackages (p: with p; [
    (aqt p)
    mypy
    python-lsp-server
  ]);
in
python-with-my-packages.env

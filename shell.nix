{ pkgs ? import <nixpkgs> { } }:
let
  aqt = p: p.callPackage ./aqt.nix { };
  python-with-my-packages = pkgs.python3.withPackages (p: with p; [
    (aqt p)
    python-lsp-server
    pylsp-mypy
    python-lsp-black
    pyls-isort
  ]);
in
pkgs.mkShell {
  nativeBuildInputs = with pkgs; [
    python-with-my-packages
    black
    gnumake
    zip
  ];
}

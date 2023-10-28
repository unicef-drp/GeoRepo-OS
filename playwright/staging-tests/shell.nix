{ pkgs ? import <nixpkgs> {} }:
#let
#  nixpkgs = builtins.fetchTarball "https://github.com/NixOS/nixpkgs/archive/9665f56e3b9c0bfaa07ca88b03b62bb277678a23.tar.gz";
#  pkgs = import nixpkgs { config = { }; overlays = [ ]; };
#in
let
  env_vars = ''
    export FOO="bar"
  '';
  extraOutputsToInstall = ["man" "dev"];
  multiPkgs = pkgs: with pkgs; [ zlib ];
in pkgs.mkShell {
  name = "env";
  buildInputs = with pkgs; [
    nodejs
    playwright
    playwright-driver
    playwright-test
  ];
  PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}";

  shellHook = ''
    # Remove playwright from node_modules, so it will be taken from playwright-test
    rm node_modules/@playwright/ -R
  '';
}

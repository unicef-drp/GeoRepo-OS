{ pkgs ? import <nixpkgs> {} }:

let
  rev = "63678e9f3d3afecfeafa0acead6239cdb447574c";
  channel = fetchTarball "https://github.com/NixOS/nixpkgs/archive/${rev}.tar.gz";
  config = {
    allowBroken = false;
  };
  pkgs = import channel { inherit config; };

in pkgs.mkShell {
  buildInputs = with pkgs; [
    nodejs
    playwright
    playwright-driver
    playwright-test
    pkgs.playwright
  ];
  PLAYWRIGHT_BROWSERS_PATH="${pkgs.playwright-driver.browsers}";
  shellHook = ''
    # Remove playwright from node_modules, so it will be taken from playwright-test
    rm node_modules/@playwright/ -R
  '';
}


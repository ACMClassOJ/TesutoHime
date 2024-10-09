let pkgs = import ./nixpkgs.nix; in
let profiles = import ./profiles.nix; in

builtins.mapAttrs (name: value: pkgs.buildEnv {
  name = "acmoj-stdenv-${name}";
  paths = value;
  postBuild = "ln -s . $out/usr";
}) profiles

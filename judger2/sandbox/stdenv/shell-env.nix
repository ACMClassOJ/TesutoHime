let pkgs = import ./nixpkgs.nix; in
let profiles = import ./profiles.nix; in

builtins.mapAttrs (name: value: pkgs.buildEnv {
  name = "acmoj-stdenv-${name}-shell";
  paths = value ++ [ pkgs.bashInteractive ];
  postBuild = "ln -s . $out/usr";
}) profiles

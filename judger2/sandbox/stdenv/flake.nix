{
  description = "TesutoHime judge sandbox environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
  };

  outputs = { self, nixpkgs }: let
    system = "x86_64-linux";
    pkgs = import nixpkgs (import ./nixpkgs.nix // { inherit system; });
    inherit(nixpkgs) lib;

    profiles = import ./profiles.nix pkgs;

    fixRandomSeed = {
      # This is actually incorrect use of -frandom-seed.
      # See https://github.com/NixOS/nixpkgs/issues/153793
      NIX_OUTPATH_USED_AS_RANDOM_SEED = "TesutoHime";
    };

    buildEnv = suffix: extraPkgs: lib.mapAttrs' (name: value: {
      name = "${name}${suffix}";
      value = (pkgs.buildEnv {
        name = "acmoj-stdenv-${name}${suffix}";
        paths = value ++ extraPkgs;
        postBuild = "ln -s . $out/usr";
      }).overrideAttrs fixRandomSeed;
    }) profiles;
    mkDevelop = suffix: extraPkgs: lib.mapAttrs' (name: value: {
      name = "${name}${suffix}";
      value = (pkgs.stdenv.mkDerivation {
        name = "${name}${suffix}";
        buildInputs = value;
      }).overrideAttrs fixRandomSeed;
    }) profiles;
  in {
    packages."${system}" = (buildEnv "" []) // (buildEnv "-shell" [ pkgs.bashInteractive ]);
    develop = (mkDevelop "" []) // (mkDevelop "-shell" [ pkgs.bashInteractive ]);
  };
}

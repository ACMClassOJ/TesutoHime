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
    buildEnv = suffix: extraPkgs: lib.mapAttrs' (name: value: {
      name = "${name}${suffix}";
      value = pkgs.buildEnv {
        # for `nix bundle`
        pname = "acmoj-stdenv-${name}${suffix}";
        meta.mainProgram = "bash";

        name = "acmoj-stdenv-${name}${suffix}";
        paths = value ++ extraPkgs;
        postBuild = "ln -s . $out/usr";
      };
    }) profiles;
    mkDevelop = suffix: extraPkgs: lib.mapAttrs' (name: value: {
      name = "${name}${suffix}";
      value = pkgs.stdenv.mkDerivation {
        name = "${name}${suffix}";
        buildInputs = value;
      };
    }) profiles;
  in {
    packages."${system}" = (buildEnv "" []) // (buildEnv "-shell" [ pkgs.bashInteractive ]);
    develop = (mkDevelop "" []) // (mkDevelop "-shell" [ pkgs.bashInteractive ]);
  };
}

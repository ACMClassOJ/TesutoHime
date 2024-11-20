# This file is modified from
# https://github.com/NixOS/nixpkgs/blob/nixos-unstable/pkgs/development/tools/parsing/antlr/4.nix
# some java related code is removed

with import ./nixpkgs.nix;

let
  mkAntlr = {
    version, sourceSha256,
    extraCppBuildInputs ? [],
    extraCppCmakeFlags ? [],
    extraPatches ? []
  }: rec {
    source = fetchFromGitHub {
      owner = "antlr";
      repo = "antlr4";
      rev = version;
      sha256 = sourceSha256;
    };

    runtime = {
      cpp = stdenv.mkDerivation {
        pname = "antlr-runtime-cpp";
        inherit version;
        src = source;

        patches = extraPatches;
        # The lib(.a,.so) will be put in out
        # The headers and cmake files will be put in dev
        outputs = [ "out" "dev" ];
        nativeBuildInputs = [ cmake ninja pkg-config ];
        cmakeDir = "../runtime/Cpp";
        cmakeFlags = extraCppCmakeFlags;
        meta = with lib; {
          description = "C++ target for ANTLR 4";
          homepage = "https://www.antlr.org/";
          license = licenses.bsd3;
          platforms = platforms.unix;
        };
      };
    };
  };
in {
  antlr4_13_1 = (mkAntlr {
    version = "4.13.1";
    sourceSha256 = "sha256-ky9nTDaS+L9UqyMsGBz5xv+NY1bPavaSfZOeXO1geaA=";
    extraCppCmakeFlags = [
      # Generate CMake config files, which are not installed by default.
      "-DANTLR4_INSTALL=ON"
        "-DCMAKE_BUILD_TYPE=Release"
      # Disable tests, since they require downloading googletest, which is
      # not available in a sandboxed build.
        "-DINSTALL_GTEST=OFF"
      "-DANTLR_BUILD_CPP_TESTS=OFF"
    ];
  }).runtime.cpp;
}
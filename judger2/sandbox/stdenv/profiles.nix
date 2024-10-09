with import ./nixpkgs.nix;

let
  libc = [
    glibc.out
    acmoj-gcc.cc.lib
  ];
  python = python313Full;
in {
  # for compile, interactor, checker
  std = [
    # stdenv packages
    gzip bzip2 xz zlib bash binutils coreutils diffutils findutils
    gawk gmp gnumake gnused gnutar gnugrep gnupatch patchelf ed file glibc
    attr acl libidn2 libunistring linuxHeaders fortify-headers

    # generic utils
    curl wget procps busybox

    # link /etc/resolv.conf
    resolv-conf

    # compiling
    git openssh acmoj-ssh-config cacert
    acmoj-gcc testlib bits-pch
    cmake  # gnumake is in stdenv
    verilog
    python

    # checker
    acmoj-checker
  ];

  # for RunType=elf
  libc = libc;
  # for RunType=valgrind
  valgrind = [ valgrind ] ++ libc;
  # for RunType=python
  python = [ python ];
}

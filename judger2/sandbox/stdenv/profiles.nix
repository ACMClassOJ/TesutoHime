nixpkgs: with nixpkgs;

let
  antlr = import ./antlr.nix nixpkgs;
  gcc = gcc15;
  libc = [
    glibc.out
    gcc.cc.lib
    # For Homework Python Interpreter
    antlr.antlr4_13_1.lib
  ];
  python = python314;
  profiles = {
    # for compile, interactor, checker
    std = [
      # stdenv packages
      binutils
      gzip bzip2 xz bash coreutils diffutils findutils gawk
      gnumake gnused gnutar gnugrep gnupatch perl

      # generic utils
      curl wget procps busybox

      # link /etc/resolv.conf
      resolv-conf

      # compiling
      git openssh acmoj-ssh-config cacert
      gcc testlib bits-pch
      cmake  # gnumake is in stdenv
      iverilog
      python

      # checker
      acmoj-checker

      # For Homework Python Interpreter
      antlr.antlr4_13_1
      antlr.antlr4_13_1.lib
    ];

    # for RunType=elf
    libc = libc;
    # for RunType=valgrind
    valgrind = [ valgrind ] ++ libc;
    # for RunType=python
    python = [ python ];
  };
in profiles // { all = builtins.concatLists (builtins.attrValues profiles); }

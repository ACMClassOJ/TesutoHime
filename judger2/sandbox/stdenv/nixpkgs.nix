{
  overlays = [
    (self: super: with super; {
      # testlib.h
      testlib = stdenv.mkDerivation {
        pname = "acmoj-testlib";
        version = "0.9.44";
        nativeBuildInputs = [ gcc15.cc ];
        src = fetchgit {
          url = "https://github.com/ACMClassOJ/testlib.git";
          sparseCheckout = [ "testlib.h" "Makefile" ];
          hash = "sha256-Jd1MV1WuMM5BpVGTwLX15XcgexSIPrDtUCwWe6FFUG4=";
        };
        installPhase = ''
          mkdir -p $out/include
          make "PREFIX=$out" install
        '';
      };

      # precompile <bits/stdc++.h>
      bits-pch = runCommand "acmoj-bits-pch" {
        nativeBuildInputs = [ gcc15.cc which ];
      } ''
        mkdir -p $out/include/bits
        cd $out/include/bits
        cp "$(find "$(dirname "$(which g++)")/.." -name 'stdc++.h')" .
        g++ -x c++-header -O2 -DONLINE_JUDGE -std=c++20 stdc++.h
        rm stdc++.h
      '';

      # include /etc/resolv.conf
      resolv-conf = runCommand "acmoj-stdenv-dummy-resolv-conf" {} ''
        mkdir -p $out/etc
        ln -s /acmoj/resolv.conf $out/etc/resolv.conf
      '';

      # checker
      acmoj-checker = stdenv.mkDerivation {
        name = "acmoj-checker";
        nativeBuildInputs = [ gcc15 cmake ];
        src = lib.fileset.toSource {
          root = ../../checker;
          fileset = ../../checker;
        };
      };

      # /etc/ssh/ssh_config and /etc/passwd
      acmoj-ssh-config = runCommand "acmoj-ssh-config" {
        meta = {
          priority = 1;
        };
      } ''
        cat << 'EOF' > ssh_config
        Host github.com
        User git
        Hostname ssh.github.com
        Port 443

        Host *
        IdentityFile /id_acmoj
        StrictHostKeyChecking no
        UserKnownHostsFile /dev/null
        LogLevel ERROR
        EOF

        cat << 'EOF' > passwd
        root:x:0:0::/root:/bin/bash
        nobody:x:65534:65534:Nobody:/:/bin/false
        EOF

        install -Dm644 ssh_config $out/etc/ssh/ssh_config
        install -Dm644 passwd $out/etc/passwd
      '';
    })

    (self: super: with super; {
      binutils = binutils.overrideAttrs {
        # lower priority of binutils, or else bin/ld will clash with gcc-wrapper
        meta = {
          priority = 11;
        };
      };
    })
  ];
}

sources = $(shell find -name '*.nix')
profiles = $(shell nix flake show --json | jq -r '.packages."x86_64-linux"|keys[]')
requisites = $(profiles:%=profiles/%/requisites)
envs = $(profiles:%=profiles/%/env)

all: $(requisites) $(envs)
clean:
	rm -rf profiles
.PHONY: all clean

profiles/%/requisites: profiles/%/result $(sources)
	nix path-info -r $< > $@

profiles/%/env: profiles/%/result $(sources)
	nix develop -i '.#develop.$*' --command env | grep -E "NIX_.*(FLAGS|CC_WRAPPER|HARDENING).*|NIX_SSL_CERT_FILE" > $@

.PRECIOUS: profiles/%/result
profiles/%/result: $(sources)
	mkdir -p profiles/$*
	nix build '.#$*' -o $@

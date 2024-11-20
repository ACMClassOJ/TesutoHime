sources = $(shell find -name '*.nix')
profiles = $(shell bash -c "nix-instantiate --eval --json - <<< 'builtins.attrNames (import ./profiles.nix)' | jq -r '.[]'")
requisites = $(profiles:%=profiles/%/requisites)
envs = $(profiles:%=profiles/%/env)

all: $(requisites) $(envs)
clean:
	rm -rf profiles
.PHONY: all clean

profiles/%/requisites: profiles/%/result $(sources)
	nix-store --query --requisites $< > $@

profiles/%/env: profiles/%/result $(sources)
	nix-shell --pure -p '(import ./profiles.nix).$*' --command 'env | grep -E "NIX_.*(FLAGS|CC_WRAPPER|HARDENING).*"' > $@

profiles/%-shell/env: profiles/%-shell/result $(sources)
	nix-shell --pure -p '(import ./profiles.nix).$*' --command 'env | grep -E "NIX_.*(FLAGS|CC_WRAPPER|HARDENING).*"' > $@

.PRECIOUS: profiles/%/result
profiles/%/result: $(sources)
	mkdir -p profiles/$*
	nix-build -A $* -o $@

.PRECIOUS: profiles/%-shell/result
profiles/%-shell/result: $(sources)
	mkdir -p profiles/$*-shell
	nix-build shell-env.nix -A $* -o $@

sources = $(shell find -name '*.nix')
profiles = $(shell bash -c "nix-instantiate --eval --json - <<< 'builtins.attrNames (import ./profiles.nix)' | jq -r '.[]'")
requisites = $(profiles:%=profiles/%/requisites)

all: $(requisites)
clean:
	rm -rf profiles
.PHONY: all clean

profiles/%/requisites: profiles/%/result $(sources)
	nix-store --query --requisites $< > $@

.PRECIOUS: profiles/%/result
profiles/%/result: $(sources)
	mkdir -p profiles/$*
	cd profiles/$*; nix-build ../../default.nix -A $*

.PRECIOUS: profiles/%-shell/result
profiles/%-shell/result: $(sources)
	mkdir -p profiles/$*-shell
	cd profiles/$*-shell; nix-build ../../shell-env.nix -A $*

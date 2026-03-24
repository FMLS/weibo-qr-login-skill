OUT_DIR := out
SKILL_NAME := weibo-qr-login-skill

SRC_FILES := SKILL.md scripts/fetch-weibo-qr.py scripts/weibo_cookies.py scripts/setup.sh

REMOTE_HOST ?=
REMOTE_DIR  := ~/.openclaw/workspace/skills

.PHONY: build clean deploy

build: clean
	@mkdir -p $(OUT_DIR)/$(SKILL_NAME)/scripts
	@for f in $(SRC_FILES); do \
		cp $$f $(OUT_DIR)/$(SKILL_NAME)/$$f; \
	done
	@echo "Build complete → $(OUT_DIR)/$(SKILL_NAME)/"

clean:
	@rm -rf $(OUT_DIR)

deploy: build
	@if [ -z "$(REMOTE_HOST)" ]; then echo "Error: REMOTE_HOST is required. Usage: make deploy REMOTE_HOST=user@host"; exit 1; fi
	rsync -avz --delete $(OUT_DIR)/$(SKILL_NAME)/ $(REMOTE_HOST):$(REMOTE_DIR)/$(SKILL_NAME)/
	@echo "Deployed to $(REMOTE_HOST):$(REMOTE_DIR)/$(SKILL_NAME)/"

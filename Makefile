OUT_DIR := out
SKILL_NAME := weibo-qr-login-skill

SRC_FILES := SKILL.md scripts/fetch-weibo-qr.py scripts/weibo_cookies.py scripts/setup.sh

.PHONY: build clean

build: clean
	@mkdir -p $(OUT_DIR)/$(SKILL_NAME)/scripts
	@for f in $(SRC_FILES); do \
		cp $$f $(OUT_DIR)/$(SKILL_NAME)/$$f; \
	done
	@echo "Build complete → $(OUT_DIR)/$(SKILL_NAME)/"

clean:
	@rm -rf $(OUT_DIR)

.PHONY: help status tree

help:
@echo "Enterprise Analyst AI Stack Lab"
@echo ""
@echo "Available commands:"
@echo " make status - Show repository status"
@echo " make tree - Show the top-level repository structure"

status:
git status --short
git log -1 --oneline

tree:
find . -maxdepth 2 -type d
-not -path "./.git*"
-not -path "./.venv*"
| sort

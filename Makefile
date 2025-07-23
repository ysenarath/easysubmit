setup:
	curl -LsSf https://gist.githubusercontent.com/ysenarath/ccadf71f7d5cd2d2c52bea974a7b33df/raw/6e5b0962644f41ac5466fd39cba0cf4adde6a29a/uv-venv-setup.sh | sh

pre-commit:
	bash .git/hooks/pre-commit

clean-notebooks:
	jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace notebooks/*.ipynb

clean:
	rm -rf dist

build:
	hatch build

publish:
	twine upload dist/*

sync:
	bash scripts/bin/sync-scratch.sh
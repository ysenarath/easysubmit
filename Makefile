clean-notebooks:
	jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace notebooks/*.ipynb

clean:
	rm -rf dist

build:
	hatch build

publish:
	twine upload dist/*
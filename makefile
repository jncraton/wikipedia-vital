all: articles

articles:
	mkdir -p articles
	python3 spider.py

clean:
	rm -rf articles
all: test wikipedia-vital.zim

wikipedia-vital.zim: articles zimwriterfs
	./zimwriterfs -f logo.png -w index.html -l en -t "Vital Wikipedia" -d Wikipedia -c Wikipedia -p jncraton -i articles $@
	ls -lah $@

articles:
	mkdir -p articles
	cp logo.png articles/
	python3 spider.py

zimwriterfs:
	wget --quiet https://download.openzim.org/release/zim-tools/zim-tools_linux-x86_64-3.1.3.tar.gz
	tar -xvf zim-tools_linux-x86_64-3.1.3.tar.gz --strip=1

test:
	python3 -m doctest spider.py

clean:
	rm -rf articles
	rm -f *.zim
	rm -f zim*
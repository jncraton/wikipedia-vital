all: wikipedia-vital.zim

wikipedia-vital.zim: articles zimwriterfs
	./zimwriterfs -f logo.png -w index.html -l en -t "Vital Wikipedia" -d Wikipedia -c Wikipedia -p jncraton -i articles wikipedia-vital.zim

articles:
	mkdir -p articles
	cp logo.png articles/
	python3 spider.py

zimwriterfs:
	wget https://download.openzim.org/release/zimwriterfs/zimwriterfs_linux-x86_64-1.3.3.tar.gz
	tar -xvf zimwriterfs_linux-x86_64-1.3.3.tar.gz --strip=1

clean:
	rm -rf articles
	rm -f wikipedia-vital.zim
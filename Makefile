.PHONY: deb deb-install clean

deb:
	scripts/build_deb.sh

deb-install: deb
	sudo dpkg -i _build/*.deb

clean:
	rm -rf _build



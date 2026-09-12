PYTHON ?= python3
PYINSTALLER ?= $(PYTHON) -m PyInstaller

.PHONY: update diff test check install-tools bundle-linux clean

update:
	@transwarp -D specification -I templates/python/ -L templates/lib -O libflagship -u
	@transwarp -D specification -I templates/js/     -L templates/lib -O static      -u

diff:
	@transwarp -D specification -I templates/python/ -L templates/lib -O libflagship -d
	@transwarp -D specification -I templates/js/     -L templates/lib -O static      -d

test:
	@$(PYTHON) -m pytest

check:
	@$(PYTHON) -m compileall ankerctl.py cli libflagship web tests
	@$(PYTHON) -m pytest

bundle-linux:
	@$(PYINSTALLER) --noconfirm --clean packaging/pyinstaller/ankerctl.spec
	@tar -C dist -czf dist/ankerctl-linux-amd64.tar.gz ankerctl

install-tools:
	git submodule update --init
	pip install ./transwarp

clean:
	@find -name '*~' -o -name '__pycache__' -print0 | xargs -0 rm -rfv

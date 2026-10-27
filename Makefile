.PHONY: install paper live test docker

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt pytest
	cp -n config.example.yaml config.yaml || true
	cp -n .env.example .env || true

paper:
	set -a; . ./.env; set +a; python -m petri

live:
	set -a; . ./.env; set +a; PETRI_LIVE=1 python -m petri --live

test:
	python -m pytest -q

docker:
	docker build -t petri . && docker run --env-file .env -v $$PWD/petri_memory.sqlite:/app/petri_memory.sqlite petri

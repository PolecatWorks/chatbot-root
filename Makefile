
BE_DIR=container-be
PYTHON_DIR=container-python

NAME=polecat-chatbot
HELM_NAME=chatbot
TAG ?= 0.3.0
REPO ?= dockerreg.k8s:5000/polecatworks

DOCKER=docker

BASE_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
VENV := ${BASE_DIR}venv
PIP := ${VENV}/bin/pip
POETRY := ${VENV}/bin/poetry



.ONESHELL:
docker-build:
	{ \
	$(DOCKER) build container-python -t $(NAME) -f Dockerfile; \
	$(DOCKER) image ls $(NAME); \
	}

docker:
	$(DOCKER)  build container-python -t $(NAME) -f container-python/Dockerfile

dockerx:
	$(DOCKER)  buildx build --push container-python -t $(REPO)/$(NAME):$(TAG) -f container-python/Dockerfile --platform linux/arm64/v8,linux/amd64




k8s-creds: export PG_SECRET=log4ham-pg
k8s-creds: export PG_USER=$(shell kubectl -n log4ham get secret $(PG_SECRET) -o jsonpath="{.data.DB_USER}" | base64 --decode)
k8s-creds: export PGPASSWORD=$(shell kubectl -n log4ham get secret $(PG_SECRET) -o jsonpath="{.data.DB_PASS}" | base64 --decode)
k8s-creds: export PG_NAME=$(shell kubectl -n log4ham get secret $(PG_SECRET) -o jsonpath="{.data.DB_NAME}" | base64 --decode)
k8s-creds: export DATABASE_URL=postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}
k8s-creds:
	@echo Creating k8s creds



guard-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	fi

local-creds:
	@echo Creating local creds: ${DATABASE_URL}


watch-run:
	cd ${BE_DIR} && DATABASE_URL=${DATABASE_URL} cargo watch  -x "run -- start --config test-data/config-localhost.yaml --secrets test-data/secrets"

watch-app-auth:
	cd ${BE_DIR} && DATABASE_URL=${DATABASE_URL} cargo watch  -x "run -- app-auth --config test-data/config-localhost.yaml --secrets test-data/secrets"

watch-test:
	cd ${BE_DIR} && DATABASE_URL=${DATABASE_URL} cargo watch --ignore test_data -x "test"


terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan

terraform-apply:
#   add TF_LOG=DEBUG to debug
	cd terraform && terraform apply

terraform-destroy:
	cd terraform && terraform destroy

${VENV}:
	@echo Creating python venv
	python3 -m venv venv && \
	${PIP} install --upgrade pip && \
	${PIP} install poetry && \
	cd container-python && \
	${POETRY} install --with dev && \
	${PIP} install -e .[dev]

python-venv: ${VENV}


python-run: ${VENV}
	@echo Running python app
	cd container-python && \
	${VENV}/bin/chatbot start --secrets tests/test_data/secrets --config tests/test_data/config.yaml


python-dev: ${VENV}
	@echo Dev run python app
	cd container-python && \
	${VENV}/bin/adev runserver


python-docker:
	$(DOCKER) build container-python -t $(NAME) -f container-python/Dockerfile

python-docker-run: python-docker
	$(DOCKER) run -it --rm \
		--name $(NAME) \
		-v $(shell pwd)/container-python/tests/test_data/secrets:/opt/app/secrets \
		-v $(shell pwd)/container-python/tests/test_data/config.yaml:/opt/app/configs/config.yaml \
		-p 8080:8080 -p 8079:8079 \
		$(NAME) \
		start --secrets /opt/app/secrets --config /opt/app/configs/config.yaml

helm:
	@echo Creating helm chart
	cd charts && \
	helm package ${HELM_NAME}

pg-login:
	@PGPASSWORD=${PGPASSWORD} psql -h localhost -U ${PG_USER} -d ${PG_NAME}

pg-connection:
	@echo postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}

pg-schema-info:
	@cd container-be && sqlx migrate info --database-url postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}

pg-schema-run:
	@cd container-be && sqlx migrate run --database-url postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}

pg-schema-revert:
	@cd container-be && sqlx migrate revert --database-url postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}

pg-sqlx-prepare:
	@cd container-be && cargo sqlx prepare --database-url postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}

pg-test-container:
	@kubectl delete pod pg-test-pod || true
	@kubectl run -it --rm pg-test-pod --image=postgres:17.4 --env="POSTGRES_USER=${PG_USER}" --env="POSTGRES_PASSWORD=${PGPASSWORD}" --env="POSTGRES_DB=${PG_NAME}" --port=5432

pg-docker-test-container: local-creds
	@docker rm -f pg-test-container || true
	@echo starting DB with ${DATABASE_URL}
	@docker run -it --rm --name pg-test-container -e POSTGRES_USER=${PG_USER} -e POSTGRES_PASSWORD=${PGPASSWORD} -e POSTGRES_DB=${PG_NAME} -p 5432:5432 postgres:17.4

pg-test-forward:
	kubectl port-forward pod/pg-test-pod 5432:5432


ngrok:
	ngrok http --host-header=rewrite --url=informally-large-terrier.ngrok-free.app 8080
ngrok-python-dev:
	ngrok http --host-header=rewrite --url=informally-large-terrier.ngrok-free.app 8000
ngrok-python:
	ngrok http --host-header=rewrite --url=informally-large-terrier.ngrok-free.app 8080
ngrok-k8s:
	ngrok http --host-header=rewrite --url=informally-large-terrier.ngrok-free.app http://chatbot.k8s
ngrok-mgt:
	open http://127.0.0.1:4040/inspect/http

python-app: guard-MicrosoftAppId guard-MicrosoftAppPassword
	cd container-python/initial_chat_bot && \
		MicrosoftAppId=${MicrosoftAppId} MicrosoftAppPassword=${MicrosoftAppPassword} ../venv/bin/python3 app.py

curl-hello:
	curl -v http://localhost:8080/polecatteamsbot/hello

curl-messages:
	curl -v http://localhost:8080/api/messages

curl-messages-post:
	curl -X POST -H "Content-Type: application/json" -d '{"text": "Hello, world!"}' http://localhost:8080/api/messages

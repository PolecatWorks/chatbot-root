
BE_DIR=container-be

PG_SECRET=log4ham-pg
PG_USER=$(shell kubectl -n log4ham get secret $(PG_SECRET) -o jsonpath="{.data.DB_USER}" | base64 --decode)
PGPASSWORD=$(shell kubectl -n log4ham get secret $(PG_SECRET) -o jsonpath="{.data.DB_PASS}" | base64 --decode)
PG_NAME=$(shell kubectl -n log4ham get secret $(PG_SECRET) -o jsonpath="{.data.DB_NAME}" | base64 --decode)
DATABASE_URL=postgres://${PG_USER}:${PGPASSWORD}@localhost/${PG_NAME}


watch-run:
	cd ${BE_DIR} && DATABASE_URL=${DATABASE_URL} cargo watch  -x "run -- start --config test-data/config-localhost.yaml --secrets test-data/secrets"

watch-app-auth:
	cd ${BE_DIR} && DATABASE_URL=${DATABASE_URL} cargo watch  -x "run -- app-auth --config test-data/config-localhost.yaml --secrets test-data/secrets"



terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan

terraform-apply:
#   add TF_LOG=DEBUG to debug
	cd terraform &&  terraform apply



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

pg-docker-test-container:
	@docker rm -f pg-test-container || true
	@docker run -it --rm --name pg-test-container -e POSTGRES_USER=${PG_USER} -e POSTGRES_PASSWORD=${PGPASSWORD} -e POSTGRES_DB=${PG_NAME} -p 5432:5432 postgres:17.4

pg-test-forward:
	kubectl port-forward pod/pg-test-pod 5432:5432


ngrok:
	ngrok http --url=informally-large-terrier.ngrok-free.app 8080
ngrok-mgt:
	open http://127.0.0.1:4040/inspect/http


curl-hello:
	curl -v http://localhost:8080/polecatteamsbot/hello

curl-messages:
	curl -v http://localhost:8080/api/messages

curl-messages-post:
	curl -X POST -H "Content-Type: application/json" -d '{"text": "Hello, world!"}' http://localhost:8080/api/messages

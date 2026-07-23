up:
	docker compose up -d
down:
	docker compose down
logs:
	docker compose logs -f web
sh:
	docker compose exec web bash
mm:
	docker compose exec web python manage.py makemigrations
migrate:
	docker compose exec web python manage.py migrate
test:
	docker compose exec web pytest
lint:
	docker compose exec web ruff check --fix . && docker compose exec web ruff format .
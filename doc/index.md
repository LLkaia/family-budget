# Family budget

```{toctree}
---
maxdepth: 2
---
./modules.rst
```

## Quick Start

### Install Git LFS locally
Follow this [documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage).

### Clone the Repository
Clone the repository to your local machine:
```shell
git clone git@github.com:LLkaia/family-budget.git
cd family-budget
```

### Set environment variables
Rename example of `.env` file:
```shell
mv app/.env.example app/.env
```
And fulfill it with valid data.

### Run the Docker Compose
```shell
docker compose up
```

### Open OpenApi documentation
http://localhost:8000

## Database schema
![schema.png](https://github.com/LLkaia/family-budget/blob/gh-pages/_static/schema.png?raw=true)

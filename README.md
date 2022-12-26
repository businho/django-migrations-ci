# django-migrations-ci

Reuse database state on CI. Run migrations on CI tests only on changes,
integrating CI caching to database state.

Migrations are slow, but you have to run it on CI for testing reasons, so avoid
to run them when the database state was already tested.

## Install

Install the package with pip:

```shell
pip install django-migrations-ci
```

Add `django_migrations_ci` to Django settings `INSTALLED_APPS`.

```python
INSTALLED_APPS = [
    ...,  # other packages
    "django_migrations_ci",
]
```

## How to use

The command `migrateci` execute all migrations and generate dump files `migrateci-*` to be cached on CI.

If these files already exist on disk, they are used to prepare the database without running all migrations again.

Configure your CI to cache these `migrateci-*` files, based on migration files.

## Workflow

This is how the "run test" CI job should work.

```shell
# Load migrateci-* from CI cache.

./manage.py migrateci
./manage.py test --keepdb

# Save migrateci-* to CI cache.
```

It works with `pytest-django` too:

```shell
./manage.py migrateci --pytest
pytest --reuse-db
```

## Parallel tests

```shell
./manage.py migrateci --parallel $(nproc)
./manage.py test --keepdb --parallel $(nproc)
```

### Parallel tests with pytest-django

When running parallel tests using `pytest-django`, use option `--pytest`,
because generated database names are different and lib handle it internally.

```shell
./manage.py migrateci --pytest --parallel $(nproc)
pytest --reuse-db --parallel $(nproc)
```

Check [database names for parallel tests](#database-names-for-parallel-tests) for
details. 

## Cache example on GitHub

```
    steps:
    - uses: actions/cache@v3
      name: Cache migrations
      with:
        path: migrateci-*
        key: ${{ hashFiles('requirements.txt', '**/migrations/*.py') }}
    - name: Migrate database
      run: ./manage.py migrateci --parallel $(nproc)
    - name: Test with Django
      run: ./manage.py test --keepdb --parallel $(nproc)
```

## Cache example on GitLab

```
test_job:
  stage: test
  script:
    # GitLab cache works only for files in $CI_PROJECT_DIR.
    - ./manage.py migrateci $(nproc) --directory $CI_PROJECT_DIR
    - ./manage.py test --keepdb --parallel $(nproc)
  cache:
    key:
      # GitLab docs say it accepts only two files, but for some reason it works
      # with wildcards too. You can't add more than two lines here.
      files:
        - requirements.txt
        - "*/migrations/*.py"
    paths:
      - migrateci-*
```

## Local migration caching

It is not possible to use "CI caching" for local runs, but we can use a folder
to cache on disk. Use `--local` option to add a suffix checksum to save a state
to disk and reuse it when it is available.

```shell
./manage.py migrateci --parallel $(nproc) --local --directory ~/.migrateci
./manage.py test --keepdb --parallel $(nproc)
```

It works with `pytest-django` too.

## Why migrations are slow?

Django migrations are slow because of state recreation for every migration and other internal Django magic.

In the past, I tried to optimize that on Django core, but learnt it's a [running issue](https://code.djangoproject.com/ticket/29898).

## Supported databases

* mysql
* postgresql
* sqlite3

Django default run sqlite3 tests as in memory database and does not work because
`migrateci` runs in a different process. Add a test database name to settings,
like [sqlite test settings](django_migrations_ci/tests/testapp/settings_sqlite.py).

Django supports oracle, but the dump function is not implemented here.

## Database names for parallel tests

Django test framework has a `--parallel N` flag to test with N parallel processes,
naming databases from 1 to N.

* On sqlite3, a `db.sqlite3` generate `db_N.sqlite3` files.
* On other databases, a `db` generate `test_db_N`.

Pytest `pytest-django` use `pytest-xdist` for parallel support, naming databases
from 0 to N-1.

* On sqlite3, a `db.sqlite3` generate `db.sqlite3_gwN` files.
* On other databases, a `db` generate `test_db_gwN`.

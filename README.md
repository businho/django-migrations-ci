# django-migrations-ci

Reuse database state on CI. Run migrations on CI tests only for changes.

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

The command `migrateci` execute all migrations and save dump files `migrateci-*`.

If these files already exist on disk, they are used to prepare the database
without running all migrations again.

## Workflow

This is how the "run test" CI job should work.

```shell
./manage.py migrateci
./manage.py test --keepdb
```

It works with `pytest-django` too as a plugin:

```shell
pytest --migrateci --reuse-db
```

The recommended way to work with it is configuring default [pytest `addopts`](https://docs.pytest.org/en/7.1.x/example/simple.html#how-to-change-command-line-options-defaults) with `--migrateci --reuse-db` to run without recreating database. When you want to recreate, run pytest with `--create-db` that has precedence over `--reuse-db`.


## Parallel tests

```shell
./manage.py migrateci --parallel $(nproc)
./manage.py test --keepdb --parallel $(nproc)
```

### Parallel tests with pytest-django

```shell
pytest --migrateci --reuse-db --parallel $(nproc)
```

Also check [database names for parallel tests](#database-names-for-parallel-tests).

## Settings

##### `MIGRATECI_STORAGE="django.core.files.storage.FileSystemStorage"`

File storage class. The [django-storages](https://pypi.org/project/django-storages/) package has many backends implemented.

Saving cache files to an external storage allow the lib to reuse partial migrations.
When you write a new migration, it will try to get a cache without this
last migration and load from it, running only the new migrations.

The [example app has a basic S3 configuration](example/settings.py#L29-L34), but it's possible
to use any custom backend:

```python
from storages.backends.s3boto3 import S3Boto3Storage

class MigrateCIStorage(S3Boto3Storage):
    bucket_name = "mybucket-migrateci-cache"
    region_name = "us-east-1"
    object_parameters = {
        "StorageClass": "REDUCED_REDUNDANCY",
    }
```

##### `MIGRATECI_LOCATION=""`

[File storage API](https://docs.djangoproject.com/en/4.1/ref/files/storage/#the-filesystemstorage-class) has a location arg that all backend use in some way.

If no storage is defined, it defaults to `~/.migrateci` to make it easy to work local.

##### `MIGRATECI_PYTEST=False`

The [`pytest-django`](https://pypi.org/project/pytest-django) package use custom test database names.

If you use it and don´t change their default fixtures, just use `MIGRATECI_PYTEST=True`.


#### `MIGRATECI_PARALLEL=None`

Before tests, Django execute all migrations in one database and clone it to be able to run parallel tests.
Use `MIGRATECI_PARALLEL="auto"` to create one database per process or define the exact number of processes with `MIGRATECI_PARALLEL=4`.

It supports how Django test and how [pytest-xdist](https://pypi.org/project/pytest-xdist) works.

#### `MIGRATECI_DEPTH=1`

This is how we decide which migration cache to use.

First, it'll try to find a cache with all migration files, but in some cases it's not possible,
like when you just pushed a new migration.

For `MIGRATECI_DEPTH=1`, it'll remove one migration a time for each Django app installed and check if some cached migration exists. It support the most common use case and it's reasonably fast.

Bigger values cause a cost operation, it'll remove N migrations a time and check if some cached migration exists. It's a combination of every Django app. E.g. for 10 apps, it'll take at most 10^N checks, with some hashing operations.

### Command line settings

All below settings can be defined through command line args.

```
manage.py migrateci [-h] [-n PARALLEL] [--storage STORAGE_CLASS] [--location LOCATION]
[--pytest] [--depth DEPTH] [-v {0,1,2,3}]

options:
  -h, --help            show this help message and exit
  -n PARALLEL, --parallel PARALLEL
  --storage STORAGE_CLASS
  --location LOCATION
  --pytest
  --depth DEPTH
  -v {0,1,2,3}
```

## Local migration caching

As a stretch of this package, it's possible to use the same strategy during local
development. It'll by default cache files at `~/.migrateci`.

```shell
./manage.py migrateci --parallel $(nproc)
./manage.py test --keepdb --parallel $(nproc)
```

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

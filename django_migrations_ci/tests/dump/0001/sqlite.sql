BEGIN TRANSACTION;
CREATE TABLE "django_migrations" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" datetime NOT NULL);
INSERT INTO "django_migrations" VALUES(1,'testapp','0001_initial','2022-10-30 11:53:54.066733');
CREATE TABLE "testapp_bus" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "plate" text NOT NULL);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('django_migrations',1);
COMMIT;

from storages.backends.s3boto3 import S3Boto3Storage


class MigrateCIStorage(S3Boto3Storage):
    bucket_name = "example-migrateci-cache"
    region_name = "us-east-2"

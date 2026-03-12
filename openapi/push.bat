@echo off

aws s3 sync --delete --exact-timestamps ^
. ^
s3://openapi.example-cloud.com/image-analysis

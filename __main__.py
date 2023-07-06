import pulumi
import pulumi_aws as aws
import json

# Import the program's configuration settings.
config = pulumi.Config()
path = config.get("path") or "./www"
index_document = config.get("indexDocument") or "index.html"
error_document = config.get("errorDocument") or "error.html"
aws_account_number = config.get("aws_account_number")

# Create an S3 bucket 
bucket = aws.s3.Bucket(
    "content",    
    acl="private"
)

origin_access_control_policy = aws.cloudfront.OriginAccessControl("oacpolicy",
    description="OAC Policy",
    origin_access_control_origin_type="s3",
    signing_behavior="always",
    signing_protocol="sigv4"
)

# Create a CloudFront CDN to distribute and cache the website.
cdn = aws.cloudfront.Distribution(
    "cdn",
    enabled=False,
    origins=[
        aws.cloudfront.DistributionOriginArgs(
            origin_id=bucket.arn,
            domain_name=bucket.bucket_domain_name,
            origin_access_control_id =origin_access_control_policy.id,
        ),
    ],
    default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
        target_origin_id=bucket.arn,
        viewer_protocol_policy="redirect-to-https",
        allowed_methods=[
            "GET",
            "HEAD",
            "OPTIONS",
        ],
        cached_methods=[
            "GET",
            "HEAD",
            "OPTIONS",
        ],
        default_ttl=600,
        max_ttl=600,
        min_ttl=600,
        forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
            query_string=True,
            cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                forward="all",
            ),
        ),
    ),
    price_class="PriceClass_100",
    custom_error_responses=[
        aws.cloudfront.DistributionCustomErrorResponseArgs(
            error_code=404,
            response_code=404,
            response_page_path=f"/{error_document}",
        )
    ],
    restrictions=aws.cloudfront.DistributionRestrictionsArgs(
        geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none",
        ),
    ),
    viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True,
    ),
)

bucket_policy = aws.s3.BucketPolicy(
    "cloudfront-bucket-policy",
    bucket=bucket.bucket,
    policy=pulumi.Output.all(
        bucket_arn=bucket.arn,
        cdn_arn = cdn.arn,
    ).apply(
        lambda args: json.dumps({
                "Version": "2008-10-17",
                "Id": "PolicyForCloudFrontPrivateContent",
                "Statement": [
                    {
                        "Sid": "AllowCloudFrontServicePrincipal",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "cloudfront.amazonaws.com"
                        },
                        "Action": "s3:GetObject",
                        "Resource": f"{args['bucket_arn']}/*",
                        "Condition": {
                            "StringLike": {
                                "AWS:SourceArn": f"{args['cdn_arn']}"
                            }
                        }
                    }
                ]
            }
        )
    ),
    opts=pulumi.ResourceOptions(parent=bucket)
)

# Export the URLs and hostnames of the bucket and distribution.
#pulumi.export("originURL", pulumi.Output.concat("http://", bucket.website_endpoint))
#pulumi.export("originHostname", bucket.website_endpoint)
#pulumi.export("cdnURL", pulumi.Output.concat("https://", cdn.domain_name))
#pulumi.export("cdnHostname", cdn.domain_name)

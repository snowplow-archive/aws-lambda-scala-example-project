# Copyright (c) 2015 Snowplow Analytics Ltd. All rights reserved.
#
# This program is licensed to you under the Apache License Version 2.0,
# and you may not use this file except in compliance with the Apache License Version 2.0.
# You may obtain a copy of the Apache License Version 2.0 at http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the Apache License Version 2.0 is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the Apache License Version 2.0 for the specific language governing permissions and limitations there under.

import datetime, json, uuid, time
from functools import partial
from random import choice
from invoke import run, task
import boto
from boto import kinesis
import boto.dynamodb2
from boto.dynamodb2.fields import HashKey, RangeKey, KeysOnlyIndex, GlobalAllIndex
from boto.dynamodb2.table import Table
from boto.dynamodb2.types import NUMBER
import boto.cloudformation
import time
import math, os
from filechunkio import FileChunkIO

# setting for AWS Lambda and Lambda-Exec-Role
REGION = "us-east-1"
IAM_ROLE_ARN = ""
IAM_ROLE = ""
POLICY = """{
    "Statement":[{
    "Effect":"Allow",
    "Action":["*"],
    "Resource":["*"]}]}"""
POLICY_NAME = "AdministratorAccess"
STACK_NAME = "LambdaStack"
TEMPLATE_URL = "https://snowplow-hosted-assets.s3.amazonaws.com/third-party/aws-lambda/lambda-admin.template"
CAPABILITIES = ["CAPABILITY_IAM"]
S3_BUCKET = "aws_scala_lambda_bucket"
S3_KEY = "aws-lambda-scala-example-project-0.1.0"
JARFILE = "./target/scala-2.11/aws-lambda-scala-example-project-0.1.0"
FUNCTION_NAME = "ProcessingKinesisLambdaDynamoDB"
# Selection of EventType values
COLORS = ['Red','Orange','Yellow','Green','Blue']
# DynamoDB settings
THROUGHPUT_READ = 20
THROUGHPUT_WRITE = 20


# AWS Kinesis Data Generator
def picker(seq):
    """
    Returns a new function that can be called without arguments
    to select and return a random color
    """
    return partial(choice, seq)

def create_event():
    """
    Returns a choice of color and builds and event
    """
    event_id = str(uuid.uuid4())
    color_choice = picker(COLORS)

    return (event_id, {
      "id": event_id,
      "timestamp": datetime.datetime.now().isoformat(),
      "eventType": color_choice()
    })

def write_event(conn, stream_name):
    """
    Returns the event and event event_payload
    """
    event_id, event_payload = create_event()
    event_json = json.dumps(event_payload)
    conn.put_record(stream_name, event_json, event_id)
    return event_json

@task
def upload_s3():
    """
    Upload jar file to s3
    """
    source_path = JARFILE
    source_size = os.stat(source_path).st_size

    # create bucket
    import boto
    conn = boto.connect_s3()
    bucket = conn.create_bucket(S3_BUCKET)

    # upload
    c = boto.connect_s3()
    b = c.get_bucket(S3_BUCKET) 
    # Create a multipart upload request
    mp = b.initiate_multipart_upload(os.path.basename(source_path))

    # Use a chunk size of 5 MiB
    chunk_size = 5242880
    chunk_count = int(math.ceil(source_size / float(chunk_size)))

    # Send the file parts, using FileChunkIO to create a file-like object
    # that points to a certain byte range within the original file. We
    # set bytes to never exceed the original file size.
    for i in range(chunk_count):
        offset = chunk_size * i
        bytes = min(chunk_size, source_size - offset)
        with FileChunkIO(source_path, 'r', offset=offset,
                         bytes=bytes) as fp:
            mp.upload_part_from_file(fp, part_num=i + 1)

    # Finish the upload
    mp.complete_upload()
    print("Jar uploaded to S3 bucket " + S3_BUCKET)

@task
def create_role():
    """
    Creates IAM role using CloudFormation for AWS Lambda service
    """
    client_cf = boto.cloudformation.connect_to_region(REGION)
    response = client_cf.create_stack(
        stack_name=STACK_NAME,
        template_url=TEMPLATE_URL,
        capabilities=CAPABILITIES
    )
    print response
    time.sleep(7)
    print "Creating roles"
    time.sleep(7)
    print "Still creating"
    time.sleep(7)
    print "Giving Lambda proper permissions"
    # get name of LambdaExecRole
    client_iam = boto.connect_iam()
    roles = client_iam.list_roles()
    list_roles = roles['list_roles_response']['list_roles_result']['roles']
    for i in range(len(list_roles)):
        if STACK_NAME+"-LambdaExecRole" in list_roles[i].arn:
            IAM_ROLE = list_roles[i].role_name
    print "Trying..."
    # grants Admin access to LambdaExecRole to access Cloudwatch, DynamoDB, Kinesis
    client_iam.put_role_policy(IAM_ROLE, POLICY_NAME, POLICY)
    print "Created role"


@task
def generate_events(profile, region, stream):
    """
    load demo data with python generator script for SimpleEvents
    """
    conn = kinesis.connect_to_region(region, profile_name=profile)
    while True:
        event_json = write_event(conn, stream)
        print "Event sent to Kinesis: {}".format(event_json)

@task
def create_lambda():
    """
    Create aws-lambda-scala-example-project AWS Lambda service
    """
    # TODO: switch to use all boto
    IAM_ROLE_ARN = get_iam_role_arn()
    print("Creating AWS Lambda function.")
    run("aws lambda create-function --region {} \
                                    --function-name {} \
                                    --code S3Bucket={},S3Key={} \
                                    --role {} \
                                    --handler com.snowplowanalytics.awslambda.LambdaFunction::recordHandler \
                                    --runtime java8 --timeout 60 --memory-size 1024".format(REGION, FUNCTION_NAME, S3_BUCKET, S3_KEY, IAM_ROLE_ARN), pty=True)
 
def get_iam_role_arn():
    client_iam = boto.connect_iam()
    roles = client_iam.list_roles()
    list_roles = roles['list_roles_response']['list_roles_result']['roles']
    for i in range(len(list_roles)):
        if STACK_NAME+"-LambdaExecRole" in list_roles[i].arn:
            IAM_ROLE_ARN = list_roles[i].arn
    return IAM_ROLE_ARN

@task
def configure_lambda(stream):
    """
    Configure Lambda function to use Kinesis
    """
    print("Configured AWS Lambda service")
    IAM_ROLE_ARN = get_iam_role_arn()
    aws_lambda = boto.connect_awslambda()
    event_source = kinesis_stream(stream)
    response_add_event_source = aws_lambda.add_event_source(event_source, 
                                                            FUNCTION_NAME, 
                                                            IAM_ROLE_ARN,
                                                            batch_size=100, 
                                                            parameters=None)
    event_source_id = response_add_event_source['UUID']

    while response_add_event_source['IsActive'] != 'true':
        print('Waiting for the event source to become active')
        sleep(5)
        response_add_event_source = aws_lambda.get_event_source(event_source_id)
    
    print('Added Kinesis as event source for Lambda function')


@task
def create_dynamodb_table(profile, region, table):
    """
    DynamoDB table creation with AWS Boto library in Python
    """
    connection = boto.dynamodb2.connect_to_region(region, profile_name=profile)
    aggregate = Table.create(table,
                             schema=[
                                 HashKey("BucketStart"),
                                 RangeKey("EventType"),
                             ],
                             throughput={
                                 'read': THROUGHPUT_READ,
                                 'write': THROUGHPUT_WRITE
                             },
                             connection=connection
                             )

@task
def create_kinesis_stream(stream):
    """
    Creates our Kinesis stream
    """
    kinesis = boto.connect_kinesis()
    response = kinesis.create_stream(stream, 1)
    pause_until_kinesis_active(stream)
    print("Kinesis successfully created")

def pause_until_kinesis_active(stream):
    kinesis = boto.connect_kinesis()
    # Wait for Kinesis stream to be active
    while kinesis.describe_stream(stream)['StreamDescription']['StreamStatus'] != 'ACTIVE':
        print('Kinesis stream [' + stream + '] not active yet')
        time.sleep(5)

def kinesis_stream(stream):
    """
    Returns Kinesis stream arn
    """
    kinesis = boto.connect_kinesis()
    return kinesis.describe_stream(stream)['StreamDescription']['StreamARN']
    
@task
def describe_kinesis_stream(stream):
    """
    Prints status Kinesis stream
    """
    print("Created: ")
    print(kinesis_stream(stream))   

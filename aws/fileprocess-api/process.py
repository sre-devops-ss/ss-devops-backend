import boto3, json, base64, os

ec2 = boto3.client("ec2")

def choose_instance_type(file_size):
    if file_size < 100:
        return "t3.medium"
    elif file_size < 500:
        return "m5.large"
    else:
        return "m5.xlarge"

def lambda_handler(event, context):
    body = json.loads(event["body"])
    file_size = int(body["file_size"])
    s3_url = body["s3Url"]
    ami_id=body["amiId"] or os.environ["AMI_ID"]
    instance_role = os.environ["INSTANCE_PROFILE_ARN"]
    subnet_id=body["subnetId"] or os.environ["SUBNET_ID"]
    vpc_id=body["vpcId"] or os.environ["VPC_ID"]
    sg_id= body["sg_id"] or os.environ["SG_ID"]
    key_name= body["keyName"] or os.environ["KEY_NAME"]



    instance_type = choose_instance_type(file_size)

    userdata = f"""<powershell>
    $file_size = "{file_size}"
    $s3Url = "{s3_url}"
    New-Item -ItemType Directory -Force -Path "C:\\temp"
    Invoke-WebRequest $s3Url -OutFile "C:\\temp\\inputfile.dat"
    Start-Process "C:\\processor\\processor.exe" -ArgumentList "$file_size","$s3Url"
    </powershell>
    """

    resp = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={'Arn': instance_role},
        UserData=base64.b64encode(userdata.encode("utf-8")).decode("utf-8"),
        SubnetId=subnet_id,
        SecurityGroupIds= [sg_id],
        KeyName=key_name


    )

    instance_id = resp["Instances"][0]["InstanceId"]
    return {
        "statusCode": 200,
        "body": json.dumps({"instanceId": instance_id})
    }

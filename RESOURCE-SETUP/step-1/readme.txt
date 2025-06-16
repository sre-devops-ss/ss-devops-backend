create a common lambda role  for multiple lambda
---
common-lambda-ss-backend-role
--
permission
---
AmazonSSMReadOnlyAccess
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:ap-south-1:979453078508:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}

-----
below sts should be updated with new client account
--
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": [
                "arn:aws:iam::979453078508:role/devops-ui-cross-account",
                "arn:aws:iam::861276115734:role/devops-ui-cross-account",
                "arn:aws:iam::318590069095:role/devops-ui-cross-account",
                "arn:aws:iam::301832774858:role/devops-ui-cross-account",
                "arn:aws:iam::339712786273:role/devops-ui-cross-account"
            ]
        }
    ]
}

--

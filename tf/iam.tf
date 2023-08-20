### ECS Agent for EC2 instance
data "aws_iam_policy_document" "ecs_agent" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_agent" {
  name               = "ecs-agent"
  assume_role_policy = data.aws_iam_policy_document.ecs_agent.json
}


resource "aws_iam_role_policy_attachment" "ecs_agent" {
  role       = aws_iam_role.ecs_agent.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
  depends_on = [aws_iam_role.ecs_agent]
}

resource "aws_iam_instance_profile" "ecs_agent" {
  name = "ecs-agent"
  role = aws_iam_role.ecs_agent.name
}
###

### ECS Task role

resource "aws_iam_role" "ecs_task_role" {
  name = "ecs_task_role"
  assume_role_policy = file("ecs-task-assume-role.json")
}

resource "aws_iam_policy" "ecs_task_policy" {
  name        = "ecs_task_policy"
  path        = "/"
  description = "ECS task policy"
  policy      = file("ecs-task-policy.json")
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

resource "aws_iam_policy" "ecs_logging" {
  name        = "ECSLogging"
  description = "Permissions for ECS to log to CloudWatch"
  
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect   = "Allow",
        Resource = aws_cloudwatch_log_group.ecs_logs.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_logging_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_logging.arn
}

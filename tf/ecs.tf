resource "aws_ecs_cluster" "main" {
  name = "main-cluster"
}

data "template_file" "container_definition" {
  template = file("ecs-container-definition.tpl")
  
  vars = {
    container_image = "${aws_ecr_repository.main.repository_url}:latest"
    logs_group      = aws_cloudwatch_log_group.ecs_logs.name
    logs_region     = var.region
  }
}

resource "aws_ecs_task_definition" "main" {
  family = "main-task"
  container_definitions = data.template_file.container_definition.rendered
  task_role_arn = aws_iam_role.ecs_task_role.arn
}

resource "aws_ecs_service" "main" {
  name            = "main-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.main.arn
  desired_count   = 1
  launch_type     = "EC2"
}

resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "ecs-logs"
  retention_in_days = 14
}

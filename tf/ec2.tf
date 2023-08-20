data "template_file" "user_data" {
  template = file("user-data.sh")

  vars = {
    ecs_cluster_name = aws_ecs_cluster.main.name
  }
}

data "aws_ssm_parameter" "ecs_ami_id" {
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2/arm64/recommended"
}

locals {
  ecs_ami_id = jsondecode(data.aws_ssm_parameter.ecs_ami_id.value)["image_id"]
}

resource "aws_instance" "main" {
  ami                    = local.ecs_ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.private.id
  user_data              = data.template_file.user_data.rendered
  iam_instance_profile   = aws_iam_instance_profile.ecs_agent.name
  vpc_security_group_ids = [aws_security_group.ec2_ecs_instance.id]
}

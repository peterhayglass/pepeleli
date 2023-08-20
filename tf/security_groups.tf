resource "aws_security_group" "ec2_ecs_instance" {
  name        = "Allow internal VPC traffic"
  description = "Allow internal VPC traffic"
  vpc_id      = aws_vpc.main.id
}

resource "aws_security_group_rule" "allow_internal_VPC_traffic" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["10.0.0.0/16"]
  security_group_id = aws_security_group.ec2_ecs_instance.id
}

resource "aws_security_group_rule" "allow_outbound_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.ec2_ecs_instance.id
}
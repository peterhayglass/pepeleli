locals {
  config_values = yamldecode(file("config.yml"))
}

locals {
  config_keys_json = jsonencode(keys(local.config_values))
}

resource "aws_ssm_parameter" "config" {
  for_each = local.config_values

  name  = each.key
  type  = "String"
  value = tostring(each.value)
}

resource "aws_ssm_parameter" "param_keys" {
  name  = "PARAM_KEYS"
  type  = "String"
  value = local.config_keys_json
}
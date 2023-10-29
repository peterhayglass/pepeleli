resource "aws_dynamodb_table" "chat_history" {
  name           = "pepeleli-chat-history"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "channel_id"
  range_key      = "timestamp"

  attribute {
    name = "channel_id"
    type = "N"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  tags = {
    Terraform = "true"
    Application = "pepeleli"
  }
}
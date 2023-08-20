[
  {
    "name": "pepeleli-main",
    "image": "${container_image}",
    "memory": 200,
    "cpu": 1024,
    "essential": true,
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "${logs_group}",
        "awslogs-region": "${logs_region}",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }
]
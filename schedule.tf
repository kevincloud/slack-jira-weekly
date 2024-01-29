resource "aws_scheduler_schedule" "project_schedule" {
  name       = "${var.unique_identifier}-project-schedule"
  group_name = aws_scheduler_schedule_group.project_schedule_group.name

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  schedule_expression          = "cron(${var.weekly_schedule_mins} ${var.weekly_schedule_hour} ? * ${var.weekly_schedule_dayofweek} *)"
  schedule_expression_timezone = var.timezone

  target {
    arn      = aws_lambda_function.lambda_projectapp.arn
    role_arn = aws_iam_role.schedule_iam_role.arn
  }
}

resource "aws_scheduler_schedule_group" "project_schedule_group" {
  name = "${var.unique_identifier}-schedule-group"
}

resource "aws_iam_role" "schedule_iam_role" {
  name = "${var.unique_identifier}-iam-for-schedule"

  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        Action : "sts:AssumeRole",
        Effect : "Allow",
        Principal : {
          "Service" : "scheduler.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "schedule_policy" {
  name = "${var.unique_identifier}-schedule-iam-policy"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "lambda:InvokeFunction"
        ],
        "Resource" : [
          "${aws_lambda_function.lambda_projectapp.arn}:*",
          aws_lambda_function.lambda_projectapp.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "schedule_iam_access_policy" {
  name   = "${var.unique_identifier}-schedule-access-policy"
  role   = aws_iam_role.schedule_iam_role.id
  policy = aws_iam_policy.schedule_policy.policy
}


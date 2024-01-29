locals {
  projectapp_fname    = "${var.unique_identifier}_lambda_projectapp"
  projectapp_loggroup = "/aws/lambda/${local.projectapp_fname}"
}

provider "aws" {
  region = var.aws_region
}

provider "archive" {}

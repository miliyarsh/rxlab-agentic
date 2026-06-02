###############################################################################
# Shared Python Lambda deployment package (service/ + pydantic).
# Built once per apply; all zip-based Lambdas reuse the same artifact.
###############################################################################

locals {
  service_sources = [
    for f in fileset("${local.repo_root}/service", "**") :
    f if !can(regex("(^|/)tests(/|$)|__pycache__|\\.pyc$", f))
  ]

  service_package_trigger = sha256(join(",", concat(
    [filesha256("${local.repo_root}/pyproject.toml")],
    [filesha256("${local.repo_root}/scripts/package_lambda_zip.py")],
    [for f in local.service_sources : filesha256("${local.repo_root}/service/${f}")],
  )))

  service_zip_path         = "${local.repo_root}/.build/rxlab-service.zip"
  service_source_code_hash = base64sha256(local.service_package_trigger)
}

resource "terraform_data" "service_package" {
  triggers_replace = [local.service_package_trigger]

  provisioner "local-exec" {
    interpreter = ["python", "${local.repo_root}/scripts/package_lambda_zip.py"]
    command     = local.service_zip_path
  }
}

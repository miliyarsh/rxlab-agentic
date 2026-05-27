"""RxLab Agentic — service package.

This package contains:

- ``service.common`` — pydantic models, structured logger, error envelope
  shared by every Lambda.
- ``service.api`` — REST API Lambda handlers (added in C6).
- ``service.agents`` — pipeline agent Lambdas (added in C7+).
- ``service.canary`` — scheduled health-check Lambda (added in C10).

The corresponding AWS infrastructure lives outside this package in
``infra/`` and is deployed via Terraform.
"""

__version__ = "0.1.0"

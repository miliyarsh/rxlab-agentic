FROM public.ecr.aws/lambda/python:3.11

COPY service ${LAMBDA_TASK_ROOT}/service
COPY service/agents/analyzer/handler.py ${LAMBDA_TASK_ROOT}/
COPY service/agents/analyzer/cpic_rules.py ${LAMBDA_TASK_ROOT}/
COPY service/agents/analyzer/data ${LAMBDA_TASK_ROOT}/data

RUN pip install --no-cache-dir "pydantic>=2.6,<3" "boto3>=1.34,<2"

CMD ["handler.handler"]

{
  "Comment": "RxLab full pipeline: Intake -> Analyzer -> FHIR -> Summarizer -> Critic",
  "StartAt": "IntakeTask",
  "States": {
    "IntakeTask": {
      "Type": "Task",
      "Resource": "${intake_lambda_arn}",
      "Next": "AnalyzerTask",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "PipelineFailed"
        }
      ]
    },
    "AnalyzerTask": {
      "Type": "Task",
      "Resource": "${analyzer_lambda_arn}",
      "Next": "FhirComposerTask",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "PipelineFailed"
        }
      ]
    },
    "FhirComposerTask": {
      "Type": "Task",
      "Resource": "${fhir_composer_lambda_arn}",
      "Next": "SummarizerTask",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "PipelineFailed"
        }
      ]
    },
    "SummarizerTask": {
      "Type": "Task",
      "Resource": "${summarizer_lambda_arn}",
      "Next": "CriticTask",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "PipelineFailed"
        }
      ]
    },
    "CriticTask": {
      "Type": "Task",
      "Resource": "${critic_lambda_arn}",
      "Next": "CriticChoice",
      "Retry": [
        {
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 2,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "PipelineFailed"
        }
      ]
    },
    "CriticChoice": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.verdict",
          "StringEquals": "approve",
          "Next": "PipelineSucceeded"
        }
      ],
      "Default": "PipelineRejected"
    },
    "PipelineSucceeded": {
      "Type": "Succeed"
    },
    "PipelineRejected": {
      "Type": "Succeed",
      "Comment": "Critic rejected the summary; job marked failed in DynamoDB (normal outcome)."
    },
    "PipelineFailed": {
      "Type": "Fail",
      "Error": "PipelineError",
      "Cause": "One or more pipeline agents failed. See agent_runs and CloudWatch logs."
    }
  }
}

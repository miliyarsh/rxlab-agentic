{
  "Comment": "RxLab deterministic pipeline: Intake -> Analyzer -> FHIR Composer",
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
      "Next": "PipelineSucceeded",
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
    "PipelineSucceeded": {
      "Type": "Succeed"
    },
    "PipelineFailed": {
      "Type": "Fail",
      "Error": "PipelineError",
      "Cause": "One or more pipeline agents failed. See agent_runs and CloudWatch logs."
    }
  }
}

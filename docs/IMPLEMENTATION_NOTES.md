# Implementation notes

## Report alignment
The source report names these modules: Load Data, Data Collection, Data Pre-processing, Feature Selection, Feature Extraction, and Machine Learning. It also describes Decision Tree, Random Forest, Gradient Boosting and SVM. The Python training script in this modernization package compares those four algorithms and reports accuracy, precision, recall, F1 and ROC-AUC on a held-out split.

## What changed from the report's original stack
- Original report: Python frontend/backend references including Tkinter, HTML/CSS/JavaScript, MySQL (WAMP).
- Modernized implementation: Spring Boot REST API, HTML/CSS/JavaScript dashboard, MySQL, Python FastAPI model service.
- No original Python source/model was available in the uploaded material, so the provided Python service starts in rule-based demo mode until a model is trained from an appropriate labeled dataset.

## Suggested follow-up improvements
1. Add authentication and role-based access before exposing any non-local deployment.
2. Add pagination and filtering for transaction history.
3. Add model version metadata, thresholds selected on validation data, and drift monitoring.
4. Add integration tests with Testcontainers or a dedicated test database.
5. Configure secrets using environment variables or a secret manager.
6. Do not deploy or use for real financial decisions without independent security and model validation.

# UPI Fraud Detection System with Explainable AI (XAI)

A full-stack portfolio project that demonstrates fraud-risk scoring for simulated UPI-style transactions using Java, Spring Boot, MySQL, Python, FastAPI, and a web dashboard.

## Technology Stack

- **Backend:** Java 17, Spring Boot, REST APIs
- **Database:** MySQL
- **Machine Learning API:** Python, FastAPI, scikit-learn
- **Frontend:** HTML, CSS, JavaScript
- **Explainability:** Per-transaction feature sensitivity analysis and model-level feature importance where supported

## Important Scope and Limitations

This is an educational prototype. PaySim is a **synthetic mobile-money dataset**, not a real UPI transaction dataset. The project does not connect to banks or UPI payment networks, access bank accounts, or initiate payments.

Predictions are risk estimates, not proof of fraud. Real-world deployment would require authorized transaction-data integration, representative labeled data, rigorous evaluation, security controls, and human review.

## Prerequisites

- Java 17 or later
- Maven installed and available in your terminal
- MySQL Server and MySQL Workbench
- Python 3.12 (64-bit recommended for this tested setup)
- VS Code or another code editor

## 1. Set Up the Database

Open MySQL Workbench and execute:

```sql
CREATE DATABASE upi_fraud_detection;
```

## 2. Configure and Run Spring Boot

Open PowerShell in the project root directory.

Set the database connection variables. Replace the example password with your own local MySQL password; do not commit real credentials.

```powershell
$env:DB_URL="jdbc:mysql://localhost:3306/upi_fraud_detection"
$env:DB_USERNAME="root"
$env:DB_PASSWORD="YOUR_LOCAL_MYSQL_PASSWORD"
$env:ML_SERVICE_URL="http://localhost:8000"
```

If your MySQL account has no password, use:

```powershell
$env:DB_PASSWORD=""
```

Start the backend using installed Maven:

```powershell
mvn spring-boot:run
```

The backend runs at `http://localhost:8080`.

Keep this terminal open while using the application.

## 3. Set Up and Run the Python ML Service

Open a **second PowerShell terminal** and navigate to the ML service directory:

```powershell
cd ml-service
```

Create the virtual environment if you have not already created it:

```powershell
py -3.12 -m venv .venv
```

Install the dependencies using the virtual environment's Python executable:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start FastAPI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
```

The ML service runs at `http://localhost:8000`.

Health endpoint: `http://localhost:8000/health`

Keep this terminal open as well.

## 4. Open the Dashboard

Once both services are running, open:

`http://localhost:8080`

Submit a transaction through the dashboard to view its risk assessment and explanation.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend health |
| POST | `/api/transactions` | Submit a transaction and request risk scoring |
| GET | `/api/transactions` | List recent transactions |
| GET | `/api/transactions/{id}` | Retrieve a transaction |
| GET | `/api/dashboard/summary` | Retrieve dashboard summary statistics |

### Example Transaction Request

```json
{
  "senderUpi": "anil@upi",
  "receiverUpi": "shop@upi",
  "amount": 1500.00,
  "transactionType": "P2P",
  "hourOfDay": 22,
  "locationMismatch": false,
  "failedAttempts": 0,
  "deviceChanged": false
}
```

## Dashboard Features

- MySQL-backed transaction history
- Search by transaction ID, sender or receiver UPI ID, risk level, or transaction type
- Summary counts for transactions, high-risk results, and transactions requiring review
- Average risk score and risk-level distribution for recent saved transactions
- Display of prediction results and explanation details

## Explainable AI (XAI)

The Python API provides fraud-risk scoring and, when available, additional information about the model's behavior.

- `POST /predict` returns risk-prediction information, including ML and rules scores, contributing factors, rule triggers, and explanation metadata.
- `GET /explainability/feature-importance` provides model-level feature importance when supported by the trained estimator.
- The dashboard can display the ML-versus-rules score comparison and available local or global contribution information.

The local explanation uses a single-feature ablation/sensitivity approximation. It is **not SHAP**, does not establish causation, and does not prove that any feature caused fraud. Some models may not expose native global feature-importance values.

If a trained model is unavailable, the service may use a clearly identified rules-based fallback. A fallback score must not be represented as a trained model prediction.

## Optional Model Training

The training script is located at `ml-service/train_model.py`.

A suitable labeled CSV should contain the following fields, with `is_fraud` encoded as 0 or 1:

```text
amount,hourOfDay,locationMismatch,failedAttempts,deviceChanged,transactionType,is_fraud
```

The dataset must contain examples from both classes. Confirm the required columns and data types in the training script before running it.

From the `ml-service` directory, run:

```powershell
.\.venv\Scripts\python.exe train_model.py --csv .\your_labeled_dataset.csv
```

The script compares Decision Tree, Random Forest, Gradient Boosting, and SVM models and reports applicable evaluation metrics. The selected pipeline is saved locally.

Use representative, authorized, appropriately anonymized data. PaySim's synthetic mobile-money records should not be described as real UPI transactions.

## Security and Production Considerations

This project is intended for learning and portfolio demonstration, not production payment security.

Before any real-world use, additional work would be needed for:

- Authorized integration with a bank or payment provider
- Secure authentication, authorization, and secrets management
- Validation of incoming transaction data
- Testing on representative held-out data
- Model calibration and fraud-focused evaluation metrics
- Fairness and subgroup checks
- Monitoring, audit trails, and analyst review

Never commit database passwords, API keys, access tokens, or other secrets to GitHub.
# UPI Fraud Detection System

A portfolio project based on the supplied report **“UPI Fraud Detection Using Machine Learning”**, modernized to use:
- Java 17 + Spring Boot REST API
- MySQL for transaction and prediction history
- Python FastAPI service for fraud-risk scoring / optional trained scikit-learn model
- Responsive HTML/CSS/JavaScript dashboard

## Important scope note
The report describes SVM, Random Forest, Decision Tree and Gradient Boosting, plus data loading, preprocessing, feature selection and extraction. The original trained model, original Python source, and real dataset were not included with the report upload. Therefore this package includes a transparent baseline risk-scoring service and a training script that can train/compare those four classifiers when you supply a labeled CSV. Do not describe demo scores as validated real-world fraud detection or use this as a real payment security system.

## Prerequisites
- Java 17+
- MySQL Server running locally (Workbench is only the client)
- Python 3.11 recommended
- Maven Wrapper (`mvnw.cmd`) included if you copy it from your generated project, or Maven installed

## 1. Database
In MySQL Workbench, execute:
```sql
CREATE DATABASE upi_fraud_detection;
```

## 2. Configure Spring Boot
Set environment variables in the VS Code terminal before starting:
```powershell
$env:DB_URL="jdbc:mysql://localhost:3306/upi_fraud_detection"
$env:DB_USERNAME="root"
$env:DB_PASSWORD="YOUR_LOCAL_MYSQL_PASSWORD"
$env:ML_SERVICE_URL="http://localhost:8000"
.\mvnw.cmd spring-boot:run
```
If you have no MySQL password, set `$env:DB_PASSWORD=""`. Never commit real credentials.

Backend runs at http://localhost:8080.

## 3. Start the Python ML service
Open a second terminal:
```powershell
cd ml-service
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
ML service runs at http://localhost:8000. Health: http://localhost:8000/health

## 4. Open dashboard
After Spring Boot starts, open http://localhost:8080 in a browser.

## API
- `GET /api/health`
- `POST /api/transactions` create transaction and get risk prediction
- `GET /api/transactions` list recent transactions
- `GET /api/transactions/{id}` get one transaction
- `GET /api/dashboard/summary` dashboard counts

Example POST:
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

## Model training (optional)
Provide a CSV with columns matching the features described in `ml-service/train_model.py`, including a binary `is_fraud` target (0/1). Then run:
```powershell
python train_model.py --csv path\to\your_dataset.csv
```
The script compares Decision Tree, Random Forest, Gradient Boosting, and SVM using a stratified split and reports precision, recall, F1 and ROC-AUC where possible. It saves the best model pipeline locally. Model files are ignored by Git and should not be committed unless intended.

## Safety
This is an educational prototype. It does not initiate UPI payments, access bank accounts, or establish that a transaction is genuinely fraudulent. Use synthetic or properly authorized, anonymized data only.


## Dashboard features
- MySQL-backed transaction history (latest 100 records)
- Search history by transaction ID, sender/receiver UPI ID, risk level, or transaction type
- Dashboard summary for total transactions, high-risk transactions, and transactions needing review
- Average risk score and risk-level distribution for the latest 100 saved transactions
- Fraud predictions are educational prototype outputs based on simulated PaySim data; they are not proof of real-world fraud

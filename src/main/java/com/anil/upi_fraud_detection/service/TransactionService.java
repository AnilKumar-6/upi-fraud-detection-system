
package com.anil.upi_fraud_detection.service;

import java.util.List;
import java.util.NoSuchElementException;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.anil.upi_fraud_detection.dto.PredictionResult;
import com.anil.upi_fraud_detection.dto.TransactionRequest;
import com.anil.upi_fraud_detection.model.Transaction;
import com.anil.upi_fraud_detection.repository.TransactionRepository;

@Service
public class TransactionService {

    private final TransactionRepository repository;
    private final FraudScoringClient scoringClient;

    public TransactionService(
            TransactionRepository repository,
            FraudScoringClient scoringClient) {
        this.repository = repository;
        this.scoringClient = scoringClient;
    }

    @Transactional
    public Transaction create(TransactionRequest request) {
        PredictionResult result = scoringClient.predict(request);

        Transaction tx = new Transaction();
        tx.setSenderUpi(request.senderUpi().trim());
        tx.setReceiverUpi(request.receiverUpi().trim());
        tx.setAmount(request.amount());
        tx.setTransactionType(request.transactionType());
        tx.setHourOfDay(request.hourOfDay());
        tx.setLocationMismatch(request.locationMismatch());
        tx.setFailedAttempts(request.failedAttempts());
        tx.setDeviceChanged(request.deviceChanged());
        tx.setUtr(request.utr());
        tx.setSenderAccountMasked(request.senderAccountMasked());
        tx.setReceiverAccountMasked(request.receiverAccountMasked());
        tx.setPaymentStatus("PENDING");

        tx.setPrediction(result.prediction());
        tx.setRiskScore(result.riskScore());
        tx.setPredictionSource(result.source());

        return repository.save(tx);
    }

    public List<Transaction> list() {
        return repository.findTop100ByOrderByCreatedAtDesc();
    }

    public Transaction get(Long id) {
        return repository.findById(id)
                .orElseThrow(() ->
                        new NoSuchElementException(
                                "Transaction not found: " + id));
    }

    public long total() {
        return repository.countAllTransactions();
    }

    public long highRisk() {
        return repository.countByPrediction("HIGH_RISK");
    }

    public long review() {
        return repository.countByPrediction("REVIEW");
    }
}

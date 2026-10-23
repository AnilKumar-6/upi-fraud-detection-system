package com.anil.upi_fraud_detection.service;

import com.anil.upi_fraud_detection.dto.*;
import com.anil.upi_fraud_detection.model.Transaction;
import com.anil.upi_fraud_detection.repository.TransactionRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class TransactionService {
    private final TransactionRepository repository;
    private final FraudScoringClient scoringClient;

    public TransactionService(TransactionRepository repository, FraudScoringClient scoringClient) {
        this.repository = repository; this.scoringClient = scoringClient;
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
        tx.setPrediction(result.prediction());
        tx.setRiskScore(result.riskScore());
        tx.setPredictionSource(result.source());
        tx.setMlScore(result.mlScore());
        tx.setRulesScore(result.rulesScore());
        tx.setExplanation(result.explanation());
        tx.setContributingFactors(result.contributingFactors());
        tx.setRuleTriggers(result.ruleTriggers());
        tx.setModelFeatureImportance(result.modelFeatureImportance());
        tx.setXaiMethod(result.xaiMethod());
        return repository.save(tx);
    }
    public List<Transaction> list() { return repository.findTop100ByOrderByCreatedAtDesc(); }
    public Transaction get(Long id) {
        return repository.findById(id).orElseThrow(() -> new java.util.NoSuchElementException("Transaction not found: " + id));
    }
    public long total() { return repository.countAllTransactions(); }
    public long highRisk() { return repository.countByPrediction("HIGH_RISK"); }
    public long review() { return repository.countByPrediction("REVIEW"); }
}

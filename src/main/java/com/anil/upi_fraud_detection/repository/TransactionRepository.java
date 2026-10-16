package com.anil.upi_fraud_detection.repository;

import com.anil.upi_fraud_detection.model.Transaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface TransactionRepository extends JpaRepository<Transaction, Long> {
    List<Transaction> findTop100ByOrderByCreatedAtDesc();
    long countByPrediction(String prediction);
    @Query("select count(t) from Transaction t")
    long countAllTransactions();
}

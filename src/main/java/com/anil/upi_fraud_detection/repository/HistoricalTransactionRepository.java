
package com.anil.upi_fraud_detection.repository;

import java.time.LocalDate;
import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

import com.anil.upi_fraud_detection.model.HistoricalTransaction;

public interface HistoricalTransactionRepository
        extends JpaRepository<HistoricalTransaction, Long> {

    boolean existsByExternalTransactionId(String externalTransactionId);

    List<HistoricalTransaction> findAllByOrderByTransactionDateDesc();

    List<HistoricalTransaction> findByTransactionDateBetweenOrderByTransactionDateDesc(
            LocalDate startDate,
            LocalDate endDate
    );

    long countByDirection(String direction);
}

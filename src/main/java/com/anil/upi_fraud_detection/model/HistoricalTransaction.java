
package com.anil.upi_fraud_detection.model;

import java.math.BigDecimal;
import java.time.LocalDate;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
    name = "historical_transactions",
    uniqueConstraints = {
        @UniqueConstraint(
            name = "uk_historical_transaction_id",
            columnNames = "external_transaction_id"
        )
    }
)
public class HistoricalTransaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "transaction_date", nullable = false)
    private LocalDate transactionDate;

    @Column(name = "transaction_time", length = 20)
    private String transactionTime;

    @Column(length = 255)
    private String description;

    @Column(nullable = false, length = 10)
    private String direction;

    @Column(name = "amount_inr", nullable = false, precision = 12, scale = 2)
    private BigDecimal amountInr;

    @Column(name = "external_transaction_id", nullable = false, unique = true, length = 80)
    private String externalTransactionId;

    @Column(length = 50)
    private String source;

    protected HistoricalTransaction() {
    }

    public HistoricalTransaction(
            LocalDate transactionDate,
            String transactionTime,
            String description,
            String direction,
            BigDecimal amountInr,
            String externalTransactionId,
            String source) {
        this.transactionDate = transactionDate;
        this.transactionTime = transactionTime;
        this.description = description;
        this.direction = direction;
        this.amountInr = amountInr;
        this.externalTransactionId = externalTransactionId;
        this.source = source;
    }

    public Long getId() { return id; }
    public LocalDate getTransactionDate() { return transactionDate; }
    public String getTransactionTime() { return transactionTime; }
    public String getDescription() { return description; }
    public String getDirection() { return direction; }
    public BigDecimal getAmountInr() { return amountInr; }
    public String getExternalTransactionId() { return externalTransactionId; }
    public String getSource() { return source; }
}


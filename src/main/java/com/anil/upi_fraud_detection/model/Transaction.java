package com.anil.upi_fraud_detection.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "transactions")
public class Transaction {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 120)
    private String senderUpi;

    @Column(nullable = false, length = 120)
    private String receiverUpi;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal amount;

    @Column(nullable = false, length = 20)
    private String transactionType;

    private Integer hourOfDay;
    private Boolean locationMismatch;
    private Integer failedAttempts;
    private Boolean deviceChanged;

    @Column(nullable = false, length = 24)
    private String prediction;

    @Column(nullable = false)
    private Double riskScore;

    @Column(nullable = false, length = 40)
    private String predictionSource;

    @Column(unique = true, length = 100)
    private String utr;

    @Column(length = 20)
    private String senderAccountMasked;

    @Column(length = 20)
    private String receiverAccountMasked;

    @Column(nullable = false, length = 20)
    private String paymentStatus = "PENDING";

    @Column(nullable = false)
    private LocalDateTime createdAt;

    @PrePersist
    void onCreate() { if (createdAt == null) createdAt = LocalDateTime.now(); }

    public Long getId() { return id; }
    public String getSenderUpi() { return senderUpi; }
    public void setSenderUpi(String senderUpi) { this.senderUpi = senderUpi; }
    public String getReceiverUpi() { return receiverUpi; }
    public void setReceiverUpi(String receiverUpi) { this.receiverUpi = receiverUpi; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public String getTransactionType() { return transactionType; }
    public void setTransactionType(String transactionType) { this.transactionType = transactionType; }
    public Integer getHourOfDay() { return hourOfDay; }
    public void setHourOfDay(Integer hourOfDay) { this.hourOfDay = hourOfDay; }
    public Boolean getLocationMismatch() { return locationMismatch; }
    public void setLocationMismatch(Boolean locationMismatch) { this.locationMismatch = locationMismatch; }
    public Integer getFailedAttempts() { return failedAttempts; }
    public void setFailedAttempts(Integer failedAttempts) { this.failedAttempts = failedAttempts; }
    public Boolean getDeviceChanged() { return deviceChanged; }
    public void setDeviceChanged(Boolean deviceChanged) { this.deviceChanged = deviceChanged; }
    public String getPrediction() { return prediction; }
    public void setPrediction(String prediction) { this.prediction = prediction; }
    public Double getRiskScore() { return riskScore; }
    public void setRiskScore(Double riskScore) { this.riskScore = riskScore; }
    public String getPredictionSource() { return predictionSource; }
    public void setPredictionSource(String predictionSource) { this.predictionSource = predictionSource; }
    public LocalDateTime getCreatedAt() { return createdAt; }

    public String getUtr() { return utr; }
    public void setUtr(String utr) { this.utr = utr; }

    public String getSenderAccountMasked() { return senderAccountMasked; }
    public void setSenderAccountMasked(String value) { this.senderAccountMasked = value; }

    public String getReceiverAccountMasked() { return receiverAccountMasked; }
    public void setReceiverAccountMasked(String value) { this.receiverAccountMasked = value; }

    public String getPaymentStatus() { return paymentStatus; }
    public void setPaymentStatus(String paymentStatus) { this.paymentStatus = paymentStatus; }
}

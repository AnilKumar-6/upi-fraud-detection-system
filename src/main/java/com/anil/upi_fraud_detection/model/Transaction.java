package com.anil.upi_fraud_detection.model;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;

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

    @Column(nullable = false)
    private LocalDateTime createdAt;

@Column
private Double mlScore;

@Column
private Double rulesScore;

@Column(columnDefinition = "TEXT")
private String explanation;

@Convert(converter = JsonMapListConverter.class)
@Column(columnDefinition = "TEXT")
private List<Map<String, Object>> contributingFactors = List.of();

@Convert(converter = JsonMapListConverter.class)
@Column(columnDefinition = "TEXT")
private List<Map<String, Object>> ruleTriggers = List.of();

@Convert(converter = JsonMapListConverter.class)
@Column(columnDefinition = "TEXT")
private List<Map<String, Object>> modelFeatureImportance = List.of();

@Column(length = 100)
private String xaiMethod;



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
    public Double getMlScore() { return mlScore; }
    public void setMlScore(Double mlScore) { this.mlScore = mlScore; }
    public Double getRulesScore() { return rulesScore; }
    public void setRulesScore(Double rulesScore) { this.rulesScore = rulesScore; }
    public String getExplanation() { return explanation; }
    public void setExplanation(String explanation) { this.explanation = explanation; }
    public List<Map<String,Object>> getContributingFactors() { return contributingFactors; }
    public void setContributingFactors(List<Map<String,Object>> v) { this.contributingFactors = v == null ? List.of() : v; }
    public List<Map<String,Object>> getRuleTriggers() { return ruleTriggers; }
    public void setRuleTriggers(List<Map<String,Object>> v) { this.ruleTriggers = v == null ? List.of() : v; }
    public List<Map<String,Object>> getModelFeatureImportance() { return modelFeatureImportance; }
    public void setModelFeatureImportance(List<Map<String,Object>> v) { this.modelFeatureImportance = v == null ? List.of() : v; }
    public String getXaiMethod() { return xaiMethod; }
    public void setXaiMethod(String xaiMethod) { this.xaiMethod = xaiMethod; }
}

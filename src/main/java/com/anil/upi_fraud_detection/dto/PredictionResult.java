package com.anil.upi_fraud_detection.dto;

public record PredictionResult(String prediction, double riskScore, String source, String explanation) {}

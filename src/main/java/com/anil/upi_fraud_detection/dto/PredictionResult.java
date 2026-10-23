package com.anil.upi_fraud_detection.dto;
import java.util.List;
import java.util.Map;
public record PredictionResult(String prediction, double riskScore, String source, String explanation,
                               Double mlScore, double rulesScore, List<Map<String,Object>> contributingFactors,
                               List<Map<String,Object>> ruleTriggers, List<Map<String,Object>> modelFeatureImportance,
                               String xaiMethod) {}

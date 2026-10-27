package com.anil.upi_fraud_detection.service;

import com.anil.upi_fraud_detection.dto.PredictionResult;
import com.anil.upi_fraud_detection.dto.TransactionRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import java.util.Map;
import java.util.List;
import java.util.Collections;

@Component
public class FraudScoringClient {
    private final RestClient client;

    public FraudScoringClient(@Value("${app.ml-service-url:http://localhost:8000}") String url) {
        this.client = RestClient.builder().baseUrl(url).build();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String,Object>> castList(Object value) {
        return value instanceof List<?> list ? (List<Map<String,Object>>) list : List.of();
    }

    public PredictionResult predict(TransactionRequest request) {
        try {
            Map<?, ?> response = client.post().uri("/predict")
                .contentType(MediaType.APPLICATION_JSON).body(request).retrieve().body(Map.class);
            if (response != null) {
                String prediction = String.valueOf(response.containsKey("prediction") ? response.get("prediction") : "REVIEW");
                double score = Double.parseDouble(String.valueOf(response.containsKey("riskScore") ? response.get("riskScore") : 0.5));
                String source = String.valueOf(response.containsKey("source") ? response.get("source") : "python-service");
                String explanation = String.valueOf(response.containsKey("explanation") ? response.get("explanation") : "Model response");
                Double mlScore = response.get("mlScore") instanceof Number n ? n.doubleValue() : null;
                double rulesScore = response.get("rulesScore") instanceof Number n ? n.doubleValue() : score;
                List<Map<String,Object>> factors = castList(response.get("contributingFactors"));
                List<Map<String,Object>> triggers = castList(response.get("ruleTriggers"));
                List<Map<String,Object>> importance = castList(response.get("modelFeatureImportance"));
                String method = String.valueOf((response.containsKey("xaiMethod") ? response.get("xaiMethod") : "unavailable"));
                return new PredictionResult(prediction, score, source, explanation, mlScore, rulesScore, factors, triggers, importance, method);
            }
        } catch (Exception ignored) {
            // Deliberately use an explicitly labelled fallback if the Python service is offline.
        }
        double score = 0.0;
        if (request.amount().doubleValue() >= 50000) score += 0.35;
        else if (request.amount().doubleValue() >= 20000) score += 0.20;
        if (request.hourOfDay() <= 5 || request.hourOfDay() >= 23) score += 0.15;
        if (Boolean.TRUE.equals(request.locationMismatch())) score += 0.25;
        if (request.failedAttempts() >= 3) score += 0.20;
        if (Boolean.TRUE.equals(request.deviceChanged())) score += 0.15;
        score = Math.min(1.0, score);
        String label = score >= 0.60 ? "HIGH_RISK" : score >= 0.30 ? "REVIEW" : "LOW_RISK";
        return new PredictionResult(label, score, "RULE_BASED_FALLBACK",
            "Python ML service unavailable; result uses simple demo rules and is not a trained-model prediction.", null, score,
            List.of(), List.of(), List.of(), "transparent Java fallback rules");
    }
}


package com.anil.upi_fraud_detection.service;

import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import com.anil.upi_fraud_detection.dto.PredictionResult;
import com.anil.upi_fraud_detection.dto.TransactionRequest;

@Component
public class FraudScoringClient {

    private static final Logger log =
            LoggerFactory.getLogger(FraudScoringClient.class);

    private final RestClient client;

    public FraudScoringClient(
            @Value("${app.ml-service-url:http://127.0.0.1:8000}") String url) {
        this.client = RestClient.builder()
                .baseUrl(url)
                .build();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> castList(Object value) {
        return value instanceof List<?> list
                ? (List<Map<String, Object>>) list
                : List.of();
    }

    public PredictionResult predict(TransactionRequest request) {
        try {
            Map<?, ?> response = client.post()
                    .uri("/predict")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(request)
                    .retrieve()
                    .body(Map.class);

            if (response == null) {
                throw new IllegalStateException(
                        "Python ML service returned an empty response");
            }

String prediction = String.valueOf(
        response.containsKey("prediction")
                ? response.get("prediction") : "REVIEW");

            double score = number(response.get("riskScore"), 0.5);
            String source = String.valueOf(
        response.containsKey("source")
                ? response.get("source") : "python-service");
            String explanation = String.valueOf(
        response.containsKey("explanation")
                ? response.get("explanation") : "Model response");
            Double mlScore = response.get("mlScore") instanceof Number n
                    ? n.doubleValue() : null;

            double rulesScore = number(response.get("rulesScore"), score);

          return new PredictionResult(
        prediction,
        score,
        source,
        explanation,
        mlScore,
        rulesScore,
        castList(response.get("contributingFactors")),
        castList(response.get("ruleTriggers")),
        castList(response.get("modelFeatureImportance")),
        String.valueOf(
                response.containsKey("xaiMethod")
                        ? response.get("xaiMethod")
                        : "unavailable"
        )
);

        } catch (Exception ex) {
            log.error("Python ML prediction request failed: {}", ex.getMessage(), ex);
            return fallback(request);
        }
    }

    private double number(Object value, double defaultValue) {
        return value instanceof Number n
                ? n.doubleValue()
                : defaultValue;
    }

    private PredictionResult fallback(TransactionRequest request) {
        double score = 0.0;

        if (request.amount().doubleValue() >= 50000) {
            score += 0.35;
        } else if (request.amount().doubleValue() >= 20000) {
            score += 0.20;
        }

        if (request.hourOfDay() <= 5 || request.hourOfDay() >= 23) {
            score += 0.15;
        }
        if (Boolean.TRUE.equals(request.locationMismatch())) {
            score += 0.25;
        }
        if (request.failedAttempts() >= 3) {
            score += 0.20;
        }
        if (Boolean.TRUE.equals(request.deviceChanged())) {
            score += 0.15;
        }

        score = Math.min(1.0, score);
        String label = score >= 0.60 ? "HIGH_RISK"
                : score >= 0.30 ? "REVIEW" : "LOW_RISK";

        return new PredictionResult(
                label, score, "RULE_BASED_FALLBACK",
                "Python ML service request failed; check the Spring Boot logs.",
                null, score, List.of(), List.of(), List.of(),
                "transparent Java fallback rules"
        );
    }
}

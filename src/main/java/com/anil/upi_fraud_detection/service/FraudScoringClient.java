
package com.anil.upi_fraud_detection.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import com.anil.upi_fraud_detection.dto.PredictionResult;
import com.anil.upi_fraud_detection.dto.TransactionRequest;

@Component
public class FraudScoringClient {

    private static final Logger log =
            LoggerFactory.getLogger(FraudScoringClient.class);

    private final RestClient client;

    public FraudScoringClient(
            @Value("${app.ml-service-url:http://127.0.0.1:8000}")
            String url) {

        this.client = RestClient.builder()
                .baseUrl(url)
                .build();

        log.info("Python ML service configured at: {}", url);
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> castList(Object value) {
        if (value instanceof List<?> list) {
            return (List<Map<String, Object>>) list;
        }
        return List.of();
    }

    public PredictionResult predict(TransactionRequest request) {

        // Build the JSON payload explicitly.
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("senderUpi", request.senderUpi());
        payload.put("receiverUpi", request.receiverUpi());
        payload.put("amount", request.amount());
        payload.put("transactionType", request.transactionType());
        payload.put("hourOfDay", request.hourOfDay());
        payload.put("locationMismatch", request.locationMismatch());
        payload.put("failedAttempts", request.failedAttempts());
        payload.put("deviceChanged", request.deviceChanged());

        try {
            log.info("Sending transaction to Python ML service.");
            log.debug("JSON payload: {}", payload);

           
Map<?, ?> response = client.post()
        .uri("/predict")
        .contentType(MediaType.APPLICATION_JSON)
        .accept(MediaType.APPLICATION_JSON)
        .body(payload)
        .retrieve()
        .body(Map.class);


            if (response == null) {
                log.error("Python ML service returned an empty response.");
                return fallback(request);
            }

            log.info("Python ML response received: {}", response);
Object predictionValue = response.get("prediction");
String prediction = predictionValue == null
        ? "REVIEW"
        : predictionValue.toString();

            double score = number(
                    response.get("riskScore"), 0.5);

Object sourceValue = response.get("source");
String source = sourceValue == null
        ? "python-service"
        : sourceValue.toString();

       Object explanationValue = response.get("explanation");
String explanation = explanationValue == null
        ? "Model response received."
        : explanationValue.toString();

            Double mlScore = nullableNumber(response.get("mlScore"));
            double rulesScore = number(
                    response.get("rulesScore"), score);

            List<Map<String, Object>> factors =
                    castList(response.get("contributingFactors"));

            List<Map<String, Object>> triggers =
                    castList(response.get("ruleTriggers"));

            List<Map<String, Object>> importance =
                    castList(response.get("modelFeatureImportance"));

    Object methodValue = response.get("xaiMethod");
String method = methodValue == null
        ? "unavailable"
        : methodValue.toString();

            return new PredictionResult(
                    prediction,
                    score,
                    source,
                    explanation,
                    mlScore,
                    rulesScore,
                    factors,
                    triggers,
                    importance,
                    method
            );

        } catch (RestClientResponseException e) {
            log.error(
                    "Python ML service returned HTTP {}. Response body: {}",
                    e.getStatusCode(),
                    e.getResponseBodyAsString()
            );

        } catch (ResourceAccessException e) {
            log.error(
                    "Cannot connect to Python ML service. Check that it is running.",
                    e
            );

        } catch (Exception e) {
            log.error("Unexpected error calling Python ML service.", e);
        }

        return fallback(request);
    }

    private double number(Object value, double defaultValue) {
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        try {
            return value == null
                    ? defaultValue
                    : Double.parseDouble(value.toString());
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }

    private Double nullableNumber(Object value) {
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        try {
            return value == null ? null
                    : Double.valueOf(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
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

        String label = score >= 0.60
                ? "HIGH_RISK"
                : score >= 0.30 ? "REVIEW" : "LOW_RISK";

        log.warn(
                "Using RULE_BASED_FALLBACK. Risk score: {}",
                score
        );

        return new PredictionResult(
                label,
                score,
                "RULE_BASED_FALLBACK",
                "Python ML service failed or returned no usable response. "
                        + "This result uses demo rules, not a trained-model prediction.",
                null,
                score,
                List.of(),
                List.of(),
                List.of(),
                "transparent Java fallback rules"
        );
    }
}

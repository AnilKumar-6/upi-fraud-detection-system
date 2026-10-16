
package com.anil.upi_fraud_detection.service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import com.anil.upi_fraud_detection.dto.PredictionResult;
import com.anil.upi_fraud_detection.dto.TransactionRequest;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class FraudScoringClient {

    private static final Logger logger =
            LoggerFactory.getLogger(FraudScoringClient.class);

    private final String url;
    private final ObjectMapper objectMapper;
    private final HttpClient httpClient;

    public FraudScoringClient(
            @Value("${app.ml-service-url:http://localhost:8000}")
            String url,
            ObjectMapper objectMapper) {

        this.url = url;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
        .version(HttpClient.Version.HTTP_1_1)
        .build();

        logger.info("Python ML service URL: {}", url);
    }

    public PredictionResult predict(TransactionRequest request) {
        try {
            String jsonRequest =
                    objectMapper.writeValueAsString(request);

            logger.info("JSON being sent to Python: {}", jsonRequest);

            HttpRequest httpRequest = HttpRequest.newBuilder()
                    .uri(URI.create(url + "/predict"))
                    .header("Content-Type", "application/json")
                    .header("Accept", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(
                            jsonRequest, StandardCharsets.UTF_8))
                    .build();

            HttpResponse<String> response = httpClient.send(
                    httpRequest,
                    HttpResponse.BodyHandlers.ofString(
                            StandardCharsets.UTF_8));

            logger.info("Python API HTTP status: {}",
                    response.statusCode());
            logger.info("Raw Python response: {}",
                    response.body());

            if (response.statusCode() < 200
                    || response.statusCode() >= 300) {
                throw new IllegalStateException(
                        "Python API returned HTTP "
                                + response.statusCode()
                                + ": " + response.body());
            }

            Map<?, ?> result = objectMapper.readValue(
                    response.body(), Map.class);

            String prediction =
                    String.valueOf(result.get("prediction"));

            double riskScore = Double.parseDouble(
                    String.valueOf(result.get("riskScore")));

            String source = result.get("source") == null
                    ? "PYTHON_SERVICE"
                    : result.get("source").toString();

            String explanation =
                    result.get("explanation") == null
                    ? "Prediction received from Python"
                    : result.get("explanation").toString();

            return new PredictionResult(
                    prediction, riskScore, source, explanation);

        } catch (Exception ex) {
            logger.error("Python ML request failed: {}",
                    ex.getMessage(), ex);

            return ruleBasedFallback(request);
        }
    }

    private PredictionResult ruleBasedFallback(
            TransactionRequest request) {

        double score = 0.0;

        if (request.amount() != null) {
            double amount = request.amount().doubleValue();

            if (amount >= 50000) {
                score += 0.35;
            } else if (amount >= 20000) {
                score += 0.20;
            }
        }

        if (request.hourOfDay() != null
                && (request.hourOfDay() <= 5
                || request.hourOfDay() >= 23)) {
            score += 0.15;
        }

        if (Boolean.TRUE.equals(request.locationMismatch())) {
            score += 0.25;
        }

        if (request.failedAttempts() != null
                && request.failedAttempts() >= 3) {
            score += 0.20;
        }

        if (Boolean.TRUE.equals(request.deviceChanged())) {
            score += 0.15;
        }

        score = Math.min(1.0, score);

        String prediction = score >= 0.60
                ? "HIGH_RISK"
                : score >= 0.30
                    ? "REVIEW"
                    : "LOW_RISK";

        logger.warn(
                "Using rule-based fallback: prediction={}, score={}",
                prediction, score);

        return new PredictionResult(
                prediction,
                score,
                "RULE_BASED_FALLBACK",
                "Python request failed; this is a rule-based demo result.");
    }
}

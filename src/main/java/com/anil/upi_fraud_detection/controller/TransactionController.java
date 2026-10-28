
package com.anil.upi_fraud_detection.controller;

import java.util.List;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.anil.upi_fraud_detection.dto.TransactionRequest;
import com.anil.upi_fraud_detection.model.Transaction;
import com.anil.upi_fraud_detection.service.TransactionService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api")
public class TransactionController {

    private final TransactionService service;

    public TransactionController(TransactionService service) {
        this.service = service;
    }

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of(
                "status", "UP",
                "application", "upi-fraud-detection"
        );
    }

    @PostMapping("/transactions")
    @ResponseStatus(HttpStatus.CREATED)
    public Transaction create(
            @Valid @RequestBody TransactionRequest request) {
        return service.create(request);
    }

    @GetMapping("/transactions")
    public List<Transaction> list() {
        return service.list();
    }

    @GetMapping("/transactions/{id}")
    public Transaction get(@PathVariable Long id) {
        return service.get(id);
    }

    @GetMapping("/dashboard/summary")
    public Map<String, Long> summary() {
        return Map.of(
                "totalTransactions", service.total(),
                "highRisk", service.highRisk(),
                "needsReview", service.review(),
                "lowRisk", service.lowRisk()
        );
    }
}

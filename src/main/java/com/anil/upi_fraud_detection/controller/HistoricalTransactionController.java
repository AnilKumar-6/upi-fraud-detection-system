
package com.anil.upi_fraud_detection.controller;

import java.io.IOException;
import java.util.List;
import java.util.Map;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.anil.upi_fraud_detection.model.HistoricalTransaction;
import com.anil.upi_fraud_detection.service.HistoricalTransactionService;

@RestController
@RequestMapping("/api/historical-transactions")
public class HistoricalTransactionController {

    private final HistoricalTransactionService service;

    public HistoricalTransactionController(
            HistoricalTransactionService service) {
        this.service = service;
    }

    @PostMapping(
            value = "/import",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public HistoricalTransactionService.ImportResult importCsv(
            @RequestParam("file") MultipartFile file) throws IOException {
        return service.importCsv(file);
    }

    @GetMapping
    public List<HistoricalTransaction> getAll() {
        return service.getAll();
    }

    @GetMapping("/summary")
    public Map<String, Long> summary() {
        return Map.of(
                "debits", service.countDebits(),
                "credits", service.countCredits()
        );
    }
}

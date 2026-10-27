
package com.anil.upi_fraud_detection.service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import com.anil.upi_fraud_detection.model.HistoricalTransaction;
import com.anil.upi_fraud_detection.repository.HistoricalTransactionRepository;

@Service
public class HistoricalTransactionService {

    private final HistoricalTransactionRepository repository;

    public HistoricalTransactionService(
            HistoricalTransactionRepository repository) {
        this.repository = repository;
    }

    @Transactional
    public ImportResult importCsv(MultipartFile file) throws IOException {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Please upload a non-empty CSV file.");
        }

        int imported = 0;
        int skipped = 0;
        int rowNumber = 0;

        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(file.getInputStream(), StandardCharsets.UTF_8))) {

            String line;
            while ((line = reader.readLine()) != null) {
                rowNumber++;

                if (rowNumber == 1) {
                    continue; // CSV header
                }

                if (line.isBlank()) {
                    continue;
                }

                String[] columns = parseCsvLine(line);

                if (columns.length != 7) {
                    throw new IllegalArgumentException(
                            "Invalid CSV format at row " + rowNumber
                    );
                }

                LocalDate date = LocalDate.parse(columns[0].trim());
                String time = columns[1].trim();
                String description = columns[2].trim();
                String direction = columns[3].trim().toUpperCase();
                BigDecimal amount = new BigDecimal(columns[4].trim());
                String transactionId = columns[5].trim();
                String source = columns[6].trim();

                if (!direction.equals("DEBIT") && !direction.equals("CREDIT")) {
                    throw new IllegalArgumentException(
                            "Invalid transaction direction at row " + rowNumber
                    );
                }

                if (transactionId.isBlank() || amount.signum() < 0) {
                    throw new IllegalArgumentException(
                            "Invalid transaction ID or amount at row " + rowNumber
                    );
                }

                if (repository.existsByExternalTransactionId(transactionId)) {
                    skipped++;
                    continue;
                }

                HistoricalTransaction transaction = new HistoricalTransaction(
                        date, time, description, direction,
                        amount, transactionId, source
                );

                repository.save(transaction);
                imported++;
            }
        }

        return new ImportResult(imported, skipped);
    }

    private String[] parseCsvLine(String line) {
        List<String> values = new java.util.ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inQuotes = false;

        for (int i = 0; i < line.length(); i++) {
            char ch = line.charAt(i);

            if (ch == '"') {
                if (inQuotes && i + 1 < line.length()
                        && line.charAt(i + 1) == '"') {
                    current.append('"');
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (ch == ',' && !inQuotes) {
                values.add(current.toString());
                current.setLength(0);
            } else {
                current.append(ch);
            }
        }

        if (inQuotes) {
            throw new IllegalArgumentException("Invalid CSV: unclosed quote.");
        }

        values.add(current.toString());
        return values.toArray(new String[0]);
    }

    public List<HistoricalTransaction> getAll() {
        return repository.findAllByOrderByTransactionDateDesc();
    }

    public long countDebits() {
        return repository.countByDirection("DEBIT");
    }

    public long countCredits() {
        return repository.countByDirection("CREDIT");
    }

    public record ImportResult(int imported, int skipped) {}
}

package com.anil.upi_fraud_detection.dto;

import jakarta.validation.constraints.*;
import java.math.BigDecimal;

public record TransactionRequest(
    @NotBlank @Size(max=120) String senderUpi,
    @NotBlank @Size(max=120) String receiverUpi,
    @NotNull @DecimalMin("0.01") @Digits(integer=10, fraction=2) BigDecimal amount,
    @NotBlank @Pattern(regexp="P2P|P2M|BILL_PAYMENT|OTHER") String transactionType,
    @NotNull @Min(0) @Max(23) Integer hourOfDay,
    @NotNull Boolean locationMismatch,
    @NotNull @Min(0) @Max(100) Integer failedAttempts,
    @NotNull Boolean deviceChanged
) {}

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
    @NotNull Boolean deviceChanged,

    @Size(max=100)
    @Pattern(regexp="^[A-Za-z0-9-]*$", message="Invalid UTR format")
    String utr,

    @Pattern(regexp="^(X{2,16}[0-9]{4})?$", message="Use a masked account ending in four digits")
    String senderAccountMasked,

    @Pattern(regexp="^(X{2,16}[0-9]{4})?$", message="Use a masked account ending in four digits")
    String receiverAccountMasked
) {}
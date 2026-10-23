
package com.anil.upi_fraud_detection.dto;

import java.math.BigDecimal;
import java.util.Set;

import org.junit.jupiter.api.AfterAll;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;

class TransactionRequestTest {

    private static ValidatorFactory factory;
    private static Validator validator;

    @BeforeAll
    static void setUp() {
        factory = Validation.buildDefaultValidatorFactory();
        validator = factory.getValidator();
    }

    @AfterAll
    static void tearDown() {
        factory.close();
    }

    @Test
    void validTransactionShouldHaveNoViolations() {
        TransactionRequest request = new TransactionRequest(
                "anil@upi",
                "shop@upi",
                new BigDecimal("500.00"),
                "P2P",
                3,
                true,
                3,
                true);

        Set<?> violations = validator.validate(request);

        assertTrue(violations.isEmpty(),
                "A valid transaction should have no validation errors");
    }

    @Test
    void negativeAmountShouldBeRejected() {
        TransactionRequest request = new TransactionRequest(
                "anil@upi",
                "shop@upi",
                new BigDecimal("-100.00"),
                "P2P",
                3,
                true,
                3,
                true);

        assertEquals(1, validator.validate(request).size());
    }

    @Test
    void invalidTransactionTypeShouldBeRejected() {
        TransactionRequest request = new TransactionRequest(
                "anil@upi",
                "shop@upi",
                new BigDecimal("500.00"),
                "INVALID",
                3,
                true,
                3,
                true);

        assertEquals(1, validator.validate(request).size());
    }

    @Test
    void hourOutsideRangeShouldBeRejected() {
        TransactionRequest request = new TransactionRequest(
                "anil@upi",
                "shop@upi",
                new BigDecimal("500.00"),
                "P2P",
                25,
                true,
                3,
                true);

        assertEquals(1, validator.validate(request).size());
    }
}

package com.anil.upi_fraud_detection.controller;

import com.anil.upi_fraud_detection.service.TransactionService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(TransactionController.class)
class TransactionControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private TransactionService service;

    @Test
    void healthEndpointShouldReturnUp() throws Exception {
        mockMvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.application")
                        .value("upi-fraud-detection"));
    }

    @Test
    void listTransactionsShouldReturnEmptyList() throws Exception {
        when(service.list()).thenReturn(List.of());

        mockMvc.perform(get("/api/transactions"))
                .andExpect(status().isOk())
                .andExpect(content().json("[]"));

        verify(service).list();
    }

    @Test
    void dashboardSummaryShouldReturnCounts() throws Exception {
        when(service.total()).thenReturn(10L);
        when(service.highRisk()).thenReturn(3L);
        when(service.review()).thenReturn(2L);

        mockMvc.perform(get("/api/dashboard/summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.totalTransactions").value(10))
                .andExpect(jsonPath("$.highRisk").value(3))
                .andExpect(jsonPath("$.needsReview").value(2));
    }

    @Test
    void invalidTransactionShouldReturnBadRequest() throws Exception {
        String request = """
                {
                  "senderUpi": "anil@upi",
                  "receiverUpi": "shop@upi",
                  "amount": -100,
                  "transactionType": "P2P",
                  "hourOfDay": 3,
                  "locationMismatch": false,
                  "failedAttempts": 0,
                  "deviceChanged": false
                }
                """;

        mockMvc.perform(post("/api/transactions")
                        .contentType("application/json")
                        .content(request))
                .andExpect(status().isBadRequest());

        verifyNoInteractions(service);
    }
}
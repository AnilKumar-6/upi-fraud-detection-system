
package com.anil.upi_fraud_detection.model;

import java.util.List;
import java.util.Map;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter
public class JsonMapListConverter
        implements AttributeConverter<List<Map<String, Object>>, String> {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final TypeReference<List<Map<String, Object>>> TYPE =
            new TypeReference<>() {};

    @Override
    public String convertToDatabaseColumn(
            List<Map<String, Object>> value) {

        if (value == null) {
            return "[]";
        }

        try {
            return MAPPER.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalArgumentException(
                    "Could not serialize transaction explanation", e);
        }
    }

    @Override
    public List<Map<String, Object>> convertToEntityAttribute(
            String value) {

        if (value == null || value.isBlank()) {
            return List.of();
        }

        try {
            return MAPPER.readValue(value, TYPE);
        } catch (Exception e) {
            throw new IllegalArgumentException(
                    "Could not deserialize transaction explanation", e);
        }
    }
}

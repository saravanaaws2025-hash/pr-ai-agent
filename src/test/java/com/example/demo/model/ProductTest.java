package com.example.demo.model;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import static org.junit.jupiter.api.Assertions.*;

class ProductTest {

    private Product product;

    @BeforeEach
    void setUp() {
        product = new Product();
    }

    @Test
    @DisplayName("Should set and get id correctly")
    void testIdGetterSetter() {
        Long expectedId = 1L;
        product.setId(expectedId);
        assertEquals(expectedId, product.getId());
    }

    @Test
    @DisplayName("Should set and get name correctly")
    void testNameGetterSetter() {
        String expectedName = "Test Product";
        product.setName(expectedName);
        assertEquals(expectedName, product.getName());
    }

    @Test
    @DisplayName("Should set and get description correctly")
    void testDescriptionGetterSetter() {
        String expectedDescription = "This is a test product description";
        product.setDescription(expectedDescription);
        assertEquals(expectedDescription, product.getDescription());
    }

    @Test
    @DisplayName("Should set and get price correctly")
    void testPriceGetterSetter() {
        double expectedPrice = 99.99;
        product.setPrice(expectedPrice);
        assertEquals(expectedPrice, product.getPrice());
    }

    @Test
    @DisplayName("Should set and get quantity correctly")
    void testQuantityGetterSetter() {
        int expectedQuantity = 100;
        product.setQuantity(expectedQuantity);
        assertEquals(expectedQuantity, product.getQuantity());
    }

    @Test
    @DisplayName("Should handle null values for all fields")
    void testNullValues() {
        assertNull(product.getId());
        assertNull(product.getName());
        assertNull(product.getDescription());
        assertNull(product.getPrice());
        assertNull(product.getQuantity());
    }

    @Test
    @DisplayName("Should create product with all fields set")
    void testProductWithAllFields() {
        product.setId(1L);
        product.setName("Complete Product");
        product.setDescription("A product with all fields set");
        product.setPrice(49.99);
        product.setQuantity(50);

        assertAll(
            () -> assertEquals(1L, product.getId()),
            () -> assertEquals("Complete Product", product.getName()),
            () -> assertEquals("A product with all fields set", product.getDescription()),
            () -> assertEquals(49.99, product.getPrice()),
            () -> assertEquals(50, product.getQuantity())
        );
    }

    @Test
    @DisplayName("Should handle zero and negative values for price")
    void testPriceEdgeCases() {
        product.setPrice(0.0);
        assertEquals(0.0, product.getPrice());

        product.setPrice(-10.50);
        assertEquals(-10.50, product.getPrice());
    }

    @Test
    @DisplayName("Should handle zero and negative values for quantity")
    void testQuantityEdgeCases() {
        product.setQuantity(0);
        assertEquals(0, product.getQuantity());

        product.setQuantity(-5);
        assertEquals(-5, product.getQuantity());
    }

    @Test
    @DisplayName("Should handle empty string for name and description")
    void testEmptyStringValues() {
        product.setName("");
        assertEquals("", product.getName());

        product.setDescription("");
        assertEquals("", product.getDescription());
    }

    @Test
    @DisplayName("Should handle very large values for price and quantity")
    void testLargeValues() {
        double largePrice = Double.MAX_VALUE;
        product.setPrice(largePrice);
        assertEquals(largePrice, product.getPrice());

        int largeQuantity = Integer.MAX_VALUE;
        product.setQuantity(largeQuantity);
        assertEquals(largeQuantity, product.getQuantity());
    }
}
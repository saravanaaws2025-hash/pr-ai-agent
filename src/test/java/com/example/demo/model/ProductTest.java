package com.example.demo.model;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;

import static org.junit.jupiter.api.Assertions.*;

public class ProductTest {

    private Product product;

    @BeforeEach
    void setUp() {
        product = new Product();
    }

    @Test
    @DisplayName("Should set and get id correctly")
    void testSetAndGetId() {
        Long expectedId = 123L;
        product.setId(expectedId);
        assertEquals(expectedId, product.getId());
    }

    @Test
    @DisplayName("Should set and get name correctly")
    void testSetAndGetName() {
        String expectedName = "Test Product";
        product.setName(expectedName);
        assertEquals(expectedName, product.getName());
    }

    @Test
    @DisplayName("Should set and get description correctly")
    void testSetAndGetDescription() {
        String expectedDescription = "This is a test product description";
        product.setDescription(expectedDescription);
        assertEquals(expectedDescription, product.getDescription());
    }

    @Test
    @DisplayName("Should set and get price correctly")
    void testSetAndGetPrice() {
        double expectedPrice = 99.99;
        product.setPrice(expectedPrice);
        assertEquals(expectedPrice, product.getPrice());
    }

    @Test
    @DisplayName("Should set and get quantity correctly")
    void testSetAndGetQuantity() {
        int expectedQuantity = 50;
        product.setQuantity(expectedQuantity);
        assertEquals(expectedQuantity, product.getQuantity());
    }

    @Test
    @DisplayName("Should return true when product is in stock")
    void testIsInStockWhenQuantityGreaterThanZero() {
        product.setQuantity(10);
        assertTrue(product.isInStock());
    }

    @Test
    @DisplayName("Should return false when product is out of stock")
    void testIsInStockWhenQuantityIsZero() {
        product.setQuantity(0);
        assertFalse(product.isInStock());
    }

    @Test
    @DisplayName("Should return false when product has negative quantity")
    void testIsInStockWhenQuantityIsNegative() {
        product.setQuantity(-5);
        assertFalse(product.isInStock());
    }

    @Test
    @DisplayName("Should handle null values for name and description")
    void testNullValues() {
        product.setName(null);
        product.setDescription(null);
        assertNull(product.getName());
        assertNull(product.getDescription());
    }

    @Test
    @DisplayName("Should handle edge case values for price")
    void testPriceEdgeCases() {
        product.setPrice(0.0);
        assertEquals(0.0, product.getPrice());
        
        product.setPrice(Double.MAX_VALUE);
        assertEquals(Double.MAX_VALUE, product.getPrice());
        
        product.setPrice(-99.99);
        assertEquals(-99.99, product.getPrice());
    }

    @Test
    @DisplayName("Should handle edge case values for quantity")
    void testQuantityEdgeCases() {
        product.setQuantity(Integer.MAX_VALUE);
        assertEquals(Integer.MAX_VALUE, product.getQuantity());
        
        product.setQuantity(Integer.MIN_VALUE);
        assertEquals(Integer.MIN_VALUE, product.getQuantity());
    }

    @Test
    @DisplayName("Should create product with default values")
    void testDefaultValues() {
        Product newProduct = new Product();
        assertEquals(0L, newProduct.getId());
        assertNull(newProduct.getName());
        assertNull(newProduct.getDescription());
        assertEquals(0.0, newProduct.getPrice());
        assertEquals(0, newProduct.getQuantity());
        assertFalse(newProduct.isInStock());
    }
}

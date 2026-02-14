package com.example.demo.model;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;

class ProductTest {

    private Product product;

    @BeforeEach
    void setUp() {
        product = new Product();
    }

    @Test
    void testGetAndSetId() {
        Long expectedId = 1L;
        product.setId(expectedId);
        assertEquals(expectedId, product.getId());
    }

    @Test
    void testGetAndSetIdNull() {
        product.setId(null);
        assertNull(product.getId());
    }

    @Test
    void testGetAndSetName() {
        String expectedName = "Test Product";
        product.setName(expectedName);
        assertEquals(expectedName, product.getName());
    }

    @Test
    void testGetAndSetNameNull() {
        product.setName(null);
        assertNull(product.getName());
    }

    @Test
    void testGetAndSetNameEmpty() {
        String expectedName = "";
        product.setName(expectedName);
        assertEquals(expectedName, product.getName());
    }

    @Test
    void testDefaultValues() {
        assertNull(product.getId());
        assertNull(product.getName());
    }

    @Test
    void testMultiplePropertyChanges() {
        Long id1 = 1L;
        Long id2 = 2L;
        String name1 = "Product 1";
        String name2 = "Product 2";

        product.setId(id1);
        product.setName(name1);
        assertEquals(id1, product.getId());
        assertEquals(name1, product.getName());

        product.setId(id2);
        product.setName(name2);
        assertEquals(id2, product.getId());
        assertEquals(name2, product.getName());
    }
}
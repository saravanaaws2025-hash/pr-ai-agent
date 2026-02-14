package com.example.demo.service;

import com.example.demo.model.Product;
import com.example.demo.repository.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    @Mock
    private ProductRepository productRepository;

    @InjectMocks
    private ProductService productService;

    private Product product1;
    private Product product2;

    @BeforeEach
    void setUp() {
        product1 = new Product();
        product1.setId(1L);
        product1.setName("Product 1");
        
        product2 = new Product();
        product2.setId(2L);
        product2.setName("Product 2");
    }

    @Test
    void getAllProducts_ReturnsListOfProducts() {
        List<Product> expectedProducts = Arrays.asList(product1, product2);
        when(productRepository.findAll()).thenReturn(expectedProducts);

        List<Product> actualProducts = productService.getAllProducts();

        assertNotNull(actualProducts);
        assertEquals(2, actualProducts.size());
        assertEquals(expectedProducts, actualProducts);
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void getAllProducts_ReturnsEmptyListWhenNoProducts() {
        when(productRepository.findAll()).thenReturn(Collections.emptyList());

        List<Product> actualProducts = productService.getAllProducts();

        assertNotNull(actualProducts);
        assertTrue(actualProducts.isEmpty());
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void deleteProduct_CallsRepositoryDeleteById() {
        Long productId = 1L;

        productService.deleteProduct(productId);

        verify(productRepository, times(1)).deleteById(productId);
    }

    @Test
    void deleteProduct_WithNullId_CallsRepositoryDeleteById() {
        productService.deleteProduct(null);

        verify(productRepository, times(1)).deleteById(null);
    }
}
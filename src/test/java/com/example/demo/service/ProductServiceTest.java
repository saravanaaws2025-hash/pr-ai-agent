package com.example.demo.service;

import com.example.demo.model.Product;
import com.example.demo.repository.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ProductServiceTest {

    @Mock
    private ProductRepository productRepository;

    private ProductService productService;

    @BeforeEach
    void setUp() {
        productService = new ProductService(productRepository);
    }

    @Test
    void getAllProducts_ReturnsListOfProducts() {
        Product product1 = new Product();
        Product product2 = new Product();
        List<Product> expectedProducts = Arrays.asList(product1, product2);

        when(productRepository.findAll()).thenReturn(expectedProducts);

        List<Product> actualProducts = productService.getAllProducts();

        assertEquals(expectedProducts, actualProducts);
        assertEquals(2, actualProducts.size());
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void getAllProducts_ReturnsEmptyListWhenNoProducts() {
        when(productRepository.findAll()).thenReturn(Collections.emptyList());

        List<Product> actualProducts = productService.getAllProducts();

        assertTrue(actualProducts.isEmpty());
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void getAllProducts_ReturnsNullWhenRepositoryReturnsNull() {
        when(productRepository.findAll()).thenReturn(null);

        List<Product> actualProducts = productService.getAllProducts();

        assertNull(actualProducts);
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void deleteProduct_CallsRepositoryDeleteById() {
        Long productId = 123L;

        productService.deleteProduct(productId);

        verify(productRepository, times(1)).deleteById(productId);
    }

    @Test
    void deleteProduct_WithNullId() {
        productService.deleteProduct(null);

        verify(productRepository, times(1)).deleteById(null);
    }

    @Test
    void deleteProduct_ThrowsExceptionWhenRepositoryThrows() {
        Long productId = 456L;
        doThrow(new RuntimeException("Database error")).when(productRepository).deleteById(productId);

        assertThrows(RuntimeException.class, () -> productService.deleteProduct(productId));
        verify(productRepository, times(1)).deleteById(productId);
    }
}
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

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class ProductServiceTest {

    @Mock
    private ProductRepository repository;

    @InjectMocks
    private ProductService productService;

    private Product product1;
    private Product product2;

    @BeforeEach
    void setUp() {
        product1 = new Product();
        product1.setId(1L);
        product1.setName("Product 1");
        product1.setPrice(10.99);
        product1.setQuantity(5);
        product1.setDescription("Description 1");

        product2 = new Product();
        product2.setId(2L);
        product2.setName("Product 2");
        product2.setPrice(20.99);
        product2.setQuantity(0);
        product2.setDescription("Description 2");
    }

    @Test
    void getAllProducts_ReturnsListOfProducts() {
        List<Product> expectedProducts = Arrays.asList(product1, product2);
        when(repository.findAll()).thenReturn(expectedProducts);

        List<Product> actualProducts = productService.getAllProducts();

        assertNotNull(actualProducts);
        assertEquals(2, actualProducts.size());
        assertEquals(expectedProducts, actualProducts);
        verify(repository, times(1)).findAll();
    }

    @Test
    void getAllProducts_ReturnsEmptyListWhenNoProducts() {
        when(repository.findAll()).thenReturn(Collections.emptyList());

        List<Product> actualProducts = productService.getAllProducts();

        assertNotNull(actualProducts);
        assertTrue(actualProducts.isEmpty());
        verify(repository, times(1)).findAll();
    }

    @Test
    void deleteProduct_CallsRepositoryDeleteById() {
        Long productId = 1L;
        doNothing().when(repository).deleteById(productId);

        productService.deleteProduct(productId);

        verify(repository, times(1)).deleteById(productId);
    }

    @Test
    void deleteProduct_WithNullId_CallsRepositoryDeleteById() {
        Long productId = null;
        doNothing().when(repository).deleteById(productId);

        productService.deleteProduct(productId);

        verify(repository, times(1)).deleteById(productId);
    }

    @Test
    void deleteProduct_WhenRepositoryThrowsException_PropagatesException() {
        Long productId = 1L;
        RuntimeException expectedException = new RuntimeException("Delete failed");
        doThrow(expectedException).when(repository).deleteById(productId);

        assertThrows(RuntimeException.class, () -> productService.deleteProduct(productId));
        verify(repository, times(1)).deleteById(productId);
    }
}

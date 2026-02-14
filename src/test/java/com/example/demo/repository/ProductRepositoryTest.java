package com.example.demo.repository;

import com.example.demo.model.Product;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
class ProductRepositoryTest {

    @Autowired
    private TestEntityManager entityManager;

    @Autowired
    private ProductRepository productRepository;

    private Product testProduct;

    @BeforeEach
    void setUp() {
        testProduct = new Product();
        testProduct.setName("Test Product");
        testProduct.setDescription("Test Description");
        testProduct.setPrice(99.99);
        testProduct.setQuantity(10);
    }

    @Test
    void testSaveProduct() {
        Product savedProduct = productRepository.save(testProduct);
        
        assertThat(savedProduct).isNotNull();
        assertThat(savedProduct.getId()).isNotNull();
        assertThat(savedProduct.getName()).isEqualTo("Test Product");
        assertThat(savedProduct.getDescription()).isEqualTo("Test Description");
        assertThat(savedProduct.getPrice()).isEqualTo(99.99);
        assertThat(savedProduct.getQuantity()).isEqualTo(10);
    }

    @Test
    void testFindById() {
        Product persistedProduct = entityManager.persistAndFlush(testProduct);
        
        Optional<Product> foundProduct = productRepository.findById(persistedProduct.getId());
        
        assertThat(foundProduct).isPresent();
        assertThat(foundProduct.get().getId()).isEqualTo(persistedProduct.getId());
        assertThat(foundProduct.get().getName()).isEqualTo("Test Product");
    }

    @Test
    void testFindByIdNotFound() {
        Optional<Product> foundProduct = productRepository.findById(999L);
        
        assertThat(foundProduct).isEmpty();
    }

    @Test
    void testFindAll() {
        Product product1 = new Product();
        product1.setName("Product 1");
        product1.setPrice(50.0);
        product1.setQuantity(5);
        
        Product product2 = new Product();
        product2.setName("Product 2");
        product2.setPrice(75.0);
        product2.setQuantity(8);
        
        entityManager.persistAndFlush(product1);
        entityManager.persistAndFlush(product2);
        
        List<Product> products = productRepository.findAll();
        
        assertThat(products).hasSize(2);
        assertThat(products).extracting(Product::getName)
                .containsExactlyInAnyOrder("Product 1", "Product 2");
    }

    @Test
    void testUpdateProduct() {
        Product persistedProduct = entityManager.persistAndFlush(testProduct);
        
        persistedProduct.setName("Updated Product");
        persistedProduct.setPrice(149.99);
        Product updatedProduct = productRepository.save(persistedProduct);
        
        assertThat(updatedProduct.getName()).isEqualTo("Updated Product");
        assertThat(updatedProduct.getPrice()).isEqualTo(149.99);
        assertThat(updatedProduct.getId()).isEqualTo(persistedProduct.getId());
    }

    @Test
    void testDeleteProduct() {
        Product persistedProduct = entityManager.persistAndFlush(testProduct);
        Long productId = persistedProduct.getId();
        
        productRepository.deleteById(productId);
        entityManager.flush();
        
        Optional<Product> deletedProduct = productRepository.findById(productId);
        assertThat(deletedProduct).isEmpty();
    }

    @Test
    void testDeleteAll() {
        Product product1 = new Product();
        product1.setName("Product 1");
        product1.setPrice(50.0);
        product1.setQuantity(5);
        
        Product product2 = new Product();
        product2.setName("Product 2");
        product2.setPrice(75.0);
        product2.setQuantity(8);
        
        entityManager.persistAndFlush(product1);
        entityManager.persistAndFlush(product2);
        
        productRepository.deleteAll();
        
        List<Product> products = productRepository.findAll();
        assertThat(products).isEmpty();
    }

    @Test
    void testCount() {
        Product product1 = new Product();
        product1.setName("Product 1");
        product1.setPrice(50.0);
        product1.setQuantity(5);
        
        Product product2 = new Product();
        product2.setName("Product 2");
        product2.setPrice(75.0);
        product2.setQuantity(8);
        
        entityManager.persistAndFlush(product1);
        entityManager.persistAndFlush(product2);
        
        long count = productRepository.count();
        
        assertThat(count).isEqualTo(2);
    }

    @Test
    void testExistsById() {
        Product persistedProduct = entityManager.persistAndFlush(testProduct);
        
        boolean exists = productRepository.existsById(persistedProduct.getId());
        boolean notExists = productRepository.existsById(999L);
        
        assertThat(exists).isTrue();
        assertThat(notExists).isFalse();
    }
}
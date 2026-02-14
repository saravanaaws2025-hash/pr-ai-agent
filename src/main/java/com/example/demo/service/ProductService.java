package com.example.demo.service;
import com.example.demo.model.Product;
import com.example.demo.repository.ProductRepository;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class ProductService {
    private final ProductRepository repository;
    public ProductService(ProductRepository repository) { this.repository = repository; }
    
    public List<Product> getAllProducts() {
        return repository.findAll();
    }

    public void deleteProduct(Long id) { 
        repository.deleteById(id); 
    }
}// touch Sat Feb 14 12:08:42 PST 2026

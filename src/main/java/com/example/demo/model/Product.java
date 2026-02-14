package com.example.demo.model;

import jakarta.persistence.*;
@Entity
public class Product {
    @Id @GeneratedValue
    private Long id;
    private String name;
    private Double price;
    private Integer quantity;
    private String description;


    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public void setDescription(String string) {
        this.description = string;
    }
    public void setPrice(double d) {
        this.price = d;
    }
    public void setQuantity(int i) {
        this.quantity = i;
    }
    public String getDescription() {
        return description;
    }
    public Double getPrice() {
        return this.price;
    }
    public Integer getQuantity() {
        return this.quantity;
    }
}
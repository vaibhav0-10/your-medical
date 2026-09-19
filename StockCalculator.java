package com.medicalstore;
public class StockCalculator {
    public static int availableStock(int opening, int purchased, int sold, int damaged, int returnedOut) {
        return opening + purchased - sold - damaged - returnedOut;
    }
    public static double profit(double selling, double purchase, double discount) {
        return selling - purchase - discount;
    }
    public static void main(String[] args) {
        System.out.println("Available stock: " + availableStock(100,50,30,5,0));
        System.out.println("Profit example: " + profit(150,100,10));
    }
}

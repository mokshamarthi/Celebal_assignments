CREATE DATABASE superstore_2;
use superstore_2;

-- Step 1: Setup Data 

-- 1.Import the Superstore dataset into a table named superstore_raw.  
CREATE TABLE superstore_raw (
    Row_ID INT,
    Order_ID VARCHAR(20),
    Order_Date VARCHAR(20),
    Ship_Date VARCHAR(20),
    Ship_Mode VARCHAR(50),
    Customer_ID VARCHAR(20),
    Customer_Name VARCHAR(100),
    Segment VARCHAR(50),
    Country VARCHAR(50),
    City VARCHAR(50),
    State VARCHAR(50),
    Postal_Code VARCHAR(20),
    Region VARCHAR(20),
    Product_ID VARCHAR(30),
    Category VARCHAR(50),
    Sub_Category VARCHAR(50),
    Product_Name VARCHAR(255),
    Sales DECIMAL(10,2),
    Quantity INT,
    Discount DECIMAL(4,2),
    Profit DECIMAL(10,2)
);

LOAD DATA LOCAL INFILE '/Users/mokshasrimarthineni/Downloads/Sample-Superstore-UTF8.csv'
INTO TABLE superstore_raw
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

ALTER TABLE superstore_raw
ADD COLUMN Order_Date_New DATE,
ADD COLUMN Ship_Date_New DATE;

SET SQL_SAFE_UPDATES = 0;
UPDATE superstore_raw
SET
    Order_Date_New = STR_TO_DATE(Order_Date, '%m/%d/%Y'),
    Ship_Date_New = STR_TO_DATE(Ship_Date, '%m/%d/%Y');
SET SQL_SAFE_UPDATES = 1;    

ALTER TABLE superstore_raw
DROP COLUMN Order_Date,
DROP COLUMN Ship_Date;

ALTER TABLE superstore_raw
CHANGE Order_Date_New Order_Date DATE,
CHANGE Ship_Date_New Ship_Date DATE;

-- Create these 3 tables from it:  customers,orders,products  and Insert data into these tables using SELECT DISTINCT.  
CREATE TABLE customers as
SELECT DISTINCT customer_id, customer_name,segment,country,city, state,region
FROM superstore_raw;

CREATE TABLE products as
SELECT DISTINCT product_id,product_name,category,sub_category
FROM superstore_raw;

CREATE TABLE orders as
SELECT DISTINCT order_id,order_date,ship_date, ship_mode,customer_id,product_id,sales,quantity,discount, profit
FROM superstore_raw;

-- Step 2: Perform Required Queries 

-- 1.Find all orders where sales are greater than the average sales. (Subquery)  
-- SELECT avg(sales) from orders;
SELECT * FROM orders
WHERE sales> (SELECT avg(sales) from orders);

-- 2.Find the highest sales order for each customer. (Subquery)  
SELECT DISTINCT c.customer_id, c.customer_name, o.order_id,o.sales 
FROM orders o
JOIN customers c ON o.customer_id=c.customer_id
WHERE o.sales= ( SELECT max(o2.sales) FROM orders o2 
				WHERE o2.customer_id=o.customer_id)
LIMIT 10;

-- 3.Calculate total sales for each customer. (CTE)  
with total_sales as(
	SELECT customer_id, sum(sales) as sum_of_sales 
    FROM orders
    GROUP BY customer_id)
SELECT * 
FROM total_sales;

-- 4.Find customers whose total sales are above average. (CTE + Subquery)  
with c_sales as(
	SELECT customer_id, sum(sales) as sum_of_sales 
    FROM orders
    GROUP BY customer_id)
    
SELECT c.customer_id, c.customer_name, c_sales.sum_of_sales,(SELECT avg(sum_of_sales) FROM c_sales) as avg_sales
FROM c_sales
JOIN customers c ON c_sales.customer_id=c.customer_id
WHERE sum_of_sales>(
		SELECT avg(sum_of_sales)
        FROM c_sales);
        
-- 5.Rank all customers based on total sales. (Window Function)  
with c_sales as(
	SELECT customer_id, sum(sales) as sum_of_sales 
    FROM orders
    GROUP BY customer_id)
    
SELECT DISTINCT c.customer_id, c.customer_name, c_sales.sum_of_sales,DENSE_RANK() OVER (ORDER BY c_sales.sum_of_sales DESC) as cust_rank
FROM c_sales
JOIN customers c
ON c_sales.customer_id=c.customer_id;

-- 6.Assign row numbers to each order within a customer. (Window Function + PARTITION BY)  
SELECT customer_id,order_id, order_date, sales, profit,
    ROW_NUMBER() OVER( PARTITION BY customer_id ORDER BY order_date) AS row_no
FROM orders;

-- 7.Display top 3 customers based on total sales. (Window Function) 
WITH c_sales AS (
    SELECT c.customer_id,c.customer_name,SUM(o.sales) AS total_sales
    FROM orders o
    JOIN customers c
	ON o.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)

SELECT customer_id,customer_name,total_sales
FROM (
    SELECT *,DENSE_RANK() OVER (ORDER BY total_sales DESC) AS sales_rank
    FROM c_sales
) ranked_customers WHERE sales_rank <= 3;

-- Step 3: Final Combined Query 
with c_sales as(
    SELECT customer_id,SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT DISTINCT c.customer_name, c_sales.total_sales,DENSE_RANK() OVER (ORDER BY c_sales.total_sales DESC) AS customer_rank
FROM c_sales
JOIN customers c
ON c_sales.customer_id = c.customer_id
ORDER BY customer_rank;

-- Mini Project: Customer Sales Insights 

-- 1.Who are the top 5 customers?  
with c_sales as(
	SELECT customer_id, sum(sales) as sum_of_sales 
    FROM orders
    GROUP BY customer_id)
SELECT DISTINCT c.customer_name, c_sales.sum_of_sales
FROM c_sales
JOIN customers c
ON c_sales.customer_id = c.customer_id
ORDER BY c_sales.sum_of_sales DESC
LIMIT 5;

-- 2.Who are the bottom 5 customers?
with c_sales as(
	SELECT customer_id, sum(sales) as sum_of_sales 
    FROM orders
    GROUP BY customer_id)
SELECT DISTINCT c.customer_name, c_sales.sum_of_sales
FROM c_sales
JOIN customers c
ON c_sales.customer_id = c.customer_id
ORDER BY c_sales.sum_of_sales ASC
LIMIT 5;

-- 3.Which customers made only one order?  
SELECT c.customer_id,c.customer_name,COUNT(o.order_id) AS order_count
FROM customers c
JOIN orders o
ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
HAVING COUNT(o.order_id) = 1;

-- 4.Which customers have above-average sales? 
with c_sales as (
SELECT customer_id, SUM(sales) AS total_sales
FROM orders
GROUP BY customer_id
)

SELECT c.customer_id,c.customer_name,c_sales.total_sales
FROM c_sales
JOIN customers c
ON c_sales.customer_id = c.customer_id
WHERE c_sales.total_sales >
(
    SELECT AVG(total_sales)
    FROM c_sales
);

-- 5.What is the highest order value per customer?
SELECT c.customer_id,c.customer_name,max(o.sales) AS highest_order
FROM customers c
JOIN orders o
ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name;
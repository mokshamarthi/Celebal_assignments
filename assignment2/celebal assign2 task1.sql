-- 1.Load dataset into a SQL database.
CREATE DATABASE superstore_db;
use superstore_db;

CREATE TABLE sales (
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

LOAD DATA LOCAL INFILE '/Users/mokshasrimarthineni/Downloads/Superstore_UTF8.csv'
INTO TABLE sales
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

SELECT Order_Date, Ship_Date
FROM sales
LIMIT 10;

ALTER TABLE sales
ADD COLUMN Order_Date_New DATE,
ADD COLUMN Ship_Date_New DATE;

SET SQL_SAFE_UPDATES = 0;
UPDATE sales
SET
    Order_Date_New = STR_TO_DATE(Order_Date, '%m/%d/%Y'),
    Ship_Date_New = STR_TO_DATE(Ship_Date, '%m/%d/%Y');
SET SQL_SAFE_UPDATES = 1;    

SELECT Order_Date,
       Order_Date_New,
       Ship_Date,
       Ship_Date_New
FROM sales
LIMIT 10;

ALTER TABLE sales
DROP COLUMN Order_Date,
DROP COLUMN Ship_Date;

ALTER TABLE sales
CHANGE Order_Date_New Order_Date DATE,
CHANGE Ship_Date_New Ship_Date DATE;

-- 2.Explore table (schema, sample data).
DESCRIBE sales;

-- to check first 5 rows in the table.
SELECT * FROM sales 
LIMIT 5;

-- to check number of rows
SELECT COUNT(*) FROM sales;

-- 3.Apply WHERE filters (region, category, date, sales).

-- to see sales from east region
SELECT * FROM sales
WHERE Region='East'
LIMIT 10;

-- to filter top 5 rows that contain sales greater than 100 and printed it’s City, Country, Postal Code and Sales.
SELECT City,Country,Postal_Code,Sales FROM sales
WHERE sales>100
LIMIT 5;

-- to filter top 6 rows where the sales are greater than 100 and category is furniture from the table.
SELECT * FROM sales
WHERE category='Furniture' AND sales>100
LIMIT 6;

-- filter top 5 rows where profit is greater than 200 and the sales is in decending order.
SELECT Product_Name,Sales,Quantity, Discount,Profit FROM sales
WHERE profit>200
ORDER BY sales desc
LIMIT 5;

-- print top 5 rows which have 2015 in order date from the table.
SELECT * FROM sales
WHERE Order_Date LIKE '2015%'
LIMIT 5;

-- 4.Use GROUP BY for aggregations (sales, quantity, averages). 

-- average sales of each category in descending order.
SELECT Category,avg(sales) as Average_Sales FROM sales
GROUP BY Category
ORDER BY Average_Sales DESC
LIMIT 5;

-- total profit in ascending order of each category.
SELECT Category,sum(profit) as Total_Profit FROM sales
GROUP BY Category
ORDER BY Total_Profit ASC
LIMIT 5;

-- grouping region, categories and then filtering total sales greater than 200000 and displaying highest 5 sales.
SELECT Region,Category, Round(sum(sales),2) as Total_Sales FROM sales
GROUP BY Region,Category
HAVING Total_Sales>200000
ORDER BY Total_Sales DESC
LIMIT 5;

-- 5.Sort and limit results (top products, top categories).

-- print the top 10 Customers who make more sales.
SELECT Customer_Name, round(sum(sales),2) as Total_Sales
FROM sales
GROUP BY Customer_Name
ORDER BY Total_Sales DESC
LIMIT 10;

-- display the top 10 City Category combinations with highest total profit sorted in descending order.
SELECT City,Category, round(sum(profit),2) as Total_Profit FROM sales
GROUP BY City,Category
ORDER BY Total_Profit DESC
LIMIT 10;

-- print the total items sold in each sub category.
SELECT Sub_Category,sum(quantity) as Total_sold_items FROM sales
GROUP BY Sub_Category
LIMIT 5;

-- 6.Solve use cases (monthly trends, top customers, duplicates). 

-- groups the data by year and month to calculate total sales from each period.
SELECT YEAR(Order_Date) AS Year, MONTH(Order_Date) AS Month, round(sum(sales),2) as total_sales FROM sales
GROUP BY Year,Month
ORDER BY Year,Month
LIMIT 5;

-- top 5 region wise total profits.
SELECT Region,sum(profit) as Total_Profit FROM sales
GROUP BY Region
LIMIT 5;

-- order id that has more than 1 count so that it identifies duplicates
SELECT Order_ID,COUNT(*) as occurences FROM sales
GROUP BY Order_ID
HAVING COUNT(*)>1;

-- 7.Validate results (row counts, data quality).

-- row count
SELECT COUNT(*) as row_count
FROM sales;

-- print the unique number of customer Ids
SELECT count(distinct Customer_ID) as unique_customers
FROM sales;

-- print the unique number of order Ids
SELECT count(distinct Order_ID) as unique_orders
FROM sales;

-- print the minimum sales, maximum sales, average sales, minimum profit and maximum profit.
SELECT min(sales) as MIN_SALES,
max(sales) as MAX_SALES,
round(avg(sales),2) as avg_sales,
min(profit) as MIN_PROFIT,
max(profit) as MAX_PROFIT
FROM sales;
Brief Summary of Assignment 1

This assignment depicts the basic data exploration and data cleaning using pandas.

1.	Loading the dataset

Firstly I have uploaded the Combined_dataset.csv file to jupyter. Then in the notebook, I imported pandas and I have loaded dataset by using read_csv function.

2.	Exploring the dataset

Next I explored the data using head(), tail(), shape, columns, dtypes, info(), describe().
•	head()- displays first rows of the dataset (default-5)
•	tail()- displays last rows of the dataset(default-5)
•	shape- displays number of rows and columns
•	dtypes- displays the datatype of each column
•	columns-displays names of the columns in the dataset
•	describe()- displays the statistical data
•	info()- displays the summary of the dataset

3.	Handling Missing Values

 Next I have handled the missing data values. 
•	Using isnull().sum() I have analysed which columns have missing values. So I have replaced the discount missing values with the mean of discounts present in dataset. 
•	Then using seller name I tried to group and replace the missing values of seller information using seller name. Then I placed Not Available for seller name, seller information, videos, variants and what customers said. I have placed not available because all these parameters will not be accurate if they we use mode, forward fill or backward fill.

4.	Filtering Data

I have performed actions to filter rows and select columns. For that, 
•	I have used loc and iloc to select specific rows, columns and individual cells.
•	I have filtered products based on rating, initial price, discount, category using conditions.

5.	Drop Duplicates

In this step I have removed duplicates using drop_duplicates and then verified if still duplicated are present by using duplicated().

6.	Creating Derived Column

In this step we have derived a column
•	Firstly I created a quantity column using a formula by interpreting that high rating means high quantity and high discount means high sales so automatically results in high quantity.
•	Then I observed final price is in object datatype so I converted it to float and then created a column total_amount.

7.	Exporting the cleaned dataset

Lastly, I have converted the cleaned dataset to a csv file using to_csv().

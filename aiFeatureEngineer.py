import requests
import pandas as pd
import os
import re
import streamlit as st
import time
import openai
import anthropic
import concurrent.futures
import datarobotx as drx

st.set_page_config(page_title="AI Feature Engineer", layout="wide")
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

#Connect to openai and anthropic
openaiClient = openai.OpenAI()
anthropicClient = anthropic.Anthropic()



INTERACTIVE_FE_SYSTEM_PROMPT = """
           You are a data scientist and feature engineering expert in Python. 
           You are a Data Scientist talking with a Suject Matter Expert (SME).  They are giving you ideas and thoughts on how to best engineer some features.
           Your job is to write a python function called engineer_features() which takes a single parameter as input, a pandas 
           dataframe, and returns the dataset with the newly engineered features as additional columns. 

           FEATURE ENGINEERING:
           Based on what you know about the data and what the user wants to create, come up with some feature engineering steps that would improve a 
           machine learning model's ability to estimate the target.

           METADATA:
           You will see the first 3 rows of the dataset.
           For categorical data, you will see all of the unique values.
           You will get a data dictionary.
           You will be informed of the target variable in the machine learning project.
           You will be informed of any data quality problems. 
           You may or may not receive a first pass at generating the engineer_features() function. If you receive it,
           you can improve or add to it. 

           YOUR RESPONSE:
           Your response shall only contain a Python function called engineer_features(). 
           The code should be redundant to errors, with a high likelihood of successfully executing. 
           The function may only rely on Python, pandas, numpy, scikit-learn, xgboost, SciPy, Statsmodels and no other libraries.
           Any libraries your function requires should be imported

           KEY CONSIDERATIONS: 
               Only reference columns that actually exist in the dataset. 
               Column names must be spelled exactly as they are in the dataset. 
               Your code should be robust to errors.
               Ensure type compatability! 
               I.e. cast columns to float when using numeric operations on those columns!
               I.e. cast columns to string when using string operations on those columns!                                      
               Your entire response must be the Python function and NO OTHER text. 
               Do NOT include an explanation of how the function works!
               Do NOT provide an example of how to use the function!
               Any text that is not Python code MUST be commented!
               The entire response MUST ONLY BE THE PYTHON FUNCTION ITSELF.     

           """


AI_SYSTEM_PROMPT = """
           You are a data scientist and feature engineering expert in Python. 
           Your job is to write a python function called engineer_features() which takes a single parameter as input, a pandas 
           dataframe, and returns the dataset with the newly engineered features as additional columns. 

           FEATURE ENGINEERING:
           You will be provided with information about the machine learning use case such as the modeling objectives
           and the target variable. You will also be provided with a data quality report that identifies missing values, 
           and other issues that might impede models' ability to learn from the data. 
           Based on what you know about the data, come up with some feature engineering steps that would improve a 
           machine learning model's ability to estimate the target.
           Some feature engineering steps you might consider:           
           - Consider resolving some or all of the data quality problems
           - Include anomaly detection or clustering
           - Look for ratios
           - Look for features that you could sum, and use as a numerator in a ratio
           - Interaction terms
           - polynomial features
           - normalizing and scaling
           - log transformation
           - outlier detection using Z-scores, the Interquartile Range (IQR) method, or using algorithms like Isolation Forest
           - No need to one-hot-encode categorical data

           METADATA:
           You will see the first 3 rows of the dataset.
           For categorical data, you will see all of the unique values.
           You will get a data dictionary.
           You will be informed of the target variable in the machine learning project.
           You will be informed of any data quality problems. 
           You may or may not receive a first pass at generating the engineer_features() function. If you receive it,
           you can improve or add to it. 

           YOUR RESPONSE:
           Your response shall only contain a Python function called engineer_features(). 
           The code should be redundant to errors, with a high likelihood of successfully executing. 
           The function may only rely on Python, pandas, numpy, scikit-learn, xgboost, SciPy, Statsmodels and no other libraries.
           Any libraries your function requires should be imported

           KEY CONSIDERATIONS: 
               Only reference columns that actually exist in the dataset. 
               Column names must be spelled exactly as they are in the dataset. 
               Your code should be robust to errors.
               Ensure type compatability! 
               I.e. cast columns to float when using numeric operations on those columns!
               I.e. cast columns to string when using string operations on those columns!                         
               No need to one-hot-encode or create dummy features.
               Your entire response must be the Python function and NO OTHER text. 
               Do NOT include an explanation of how the function works!
               Do NOT provide an example of how to use the function!
               Any text that is not Python code MUST be commented!
               The entire response MUST ONLY BE THE PYTHON FUNCTION ITSELF.     

           """

@st.cache_data(show_spinner=False)
def getDataDictionary(prompt):
    '''
    Submits the data, gets dictionary
    '''

    data = pd.DataFrame({"promptText": [prompt]})
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65af61f272721c6041f825db'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code

def getDataDictionary2(prompt, df):
    types = str(df.dtypes)
    system_prompt = """
        You are a data dictionary maker. 
        You will receive the following:
        1) The data type of each column
        2) The first 10 rows of a dataframe
        3) A summary of the data computed using pandas .describe()
        4) For categorical data, a list of the unique values limited to the top 10 most frequent values.
        
        Inspect this metadata to decipher what each column in the dataset is about is about.        
        Write a description for each column that will help an analyst effectively leverage this data in their analysis.
        The description should communicate what any acronymns might mean, what the business value of the data is, and what the analytic value might be. 
        You must describe ALL of the columns in the dataset to the best of your ability. 
        Your response should be formatted in markdown as a table or list containing all of the columns names, their data type, along with your best attempt to describe what the column is about. 
            
        DATA TYPES:  
        """ + types
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f22baee48be774cda48a81' #openai
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code


def getPythonCode(prompt):
    '''
    Submits the user's prompt to DataRobot, gets Python
    '''

    data = pd.DataFrame({"promptText": [prompt]})
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65aedd564840bad380f81455'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code
def executePythonCode(prompt, df):
    '''
    Executes the Python Code generated by the LLM
    '''
    print("Generating code...")
    pythonCode = getPythonCode(prompt)
    # print(pythonCode.replace("```python", "").replace("```", ""))
    # pythonCode = pythonCode.replace("```python", "").replace("```", "")
    print("Executing...")
    function_dict = {}
    exec(pythonCode, function_dict)  # execute the code created by our LLM
    analyze_data = function_dict['analyze_data']  # get the function that our code created
    results = analyze_data(df)
    return pythonCode, results
def getChartCode(prompt):
    '''
    Given the question, the Python Code, and the Result, build the charts
    '''
    data = pd.DataFrame({"promptText": [prompt]})
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65af555c75771a4f76bae9af'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )

    # Safely get the 'data' key
    data = predictions_response.json().get("data")
    if data:
        return predictions_response.json()["data"][0]["prediction"]
    else:
        print(predictions_response.json())
        return predictions_response.json()
def createCharts(prompt, pythonCode, results):
    # Wait for 2 seconds to avoid rate limit
    time.sleep(2.1)
    print("getting chart code...")
    chartCode = getChartCode(prompt + str(pythonCode) + str(results))
    print(chartCode.replace("```python", "").replace("```", ""))
    function_dict = {}
    exec(chartCode.replace("```python", "").replace("```", ""), function_dict)  # execute the code created by our LLM
    print("executing chart code...")
    create_charts = function_dict['create_charts']  # get the function that our code created
    fig1, fig2 = create_charts(results)
    return fig1, fig2
def getBusinessAnalysis(prompt):
    '''
    Given the question, the Python Code, and the Result, retrieve the business analysis and suggestions.
    '''
    # Wait for 2 seconds to avoid rate limit
    time.sleep(2.1)
    data = pd.DataFrame({"promptText": [prompt]})
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65aede355dcbc38e6fbae6db'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    # Safely get the 'data' key
    data = predictions_response.json().get("data")
    if data:
        return predictions_response.json()["data"][0]["prediction"]
    else:
        print(predictions_response.json())
        return predictions_response.json()
def get_top_frequent_values(df):
    # Select non-numeric columns
    non_numeric_cols = df.select_dtypes(exclude=['number']).columns

    # Prepare a list to store the results
    results = []

    # Iterate over non-numeric columns
    for col in non_numeric_cols:
        try:
            # Ensure strings and fill NaNs to prevent type issues
            cleaned_col = df[col].fillna('Missing').astype(str)

            # Find top 10 most frequent values for the column
            top_values = cleaned_col.value_counts().head(10).index.tolist()

            # Append the column name and its frequent values to the results
            results.append({'Non-numeric column name': col, 'Frequent Values': top_values})
        except Exception as e:
            print(f"Error processing column {col}: {e}")
            # Optionally, append an error indicator or use a placeholder value
            results.append({'Non-numeric column name': col, 'Frequent Values': ['Error processing column']})

    # Create a new DataFrame for the results
    result_df = pd.DataFrame(results)

    return result_df
def extract_python_code(markdown_text):
    # Pattern to match code blocks that optionally start with ```python or just ```
    pattern = r'```(?:python)?\n(.*?)```'
    matches = re.findall(pattern, markdown_text, re.DOTALL)

    # Join all matches into a single string, separated by two newlines
    python_code = '\n\n'.join(matches)
    return python_code
@st.cache_data(show_spinner=False)
def getDataQualityReport(prompt):
    system_prompt = """
        You are a data quality analyst and Python expert. 
        Your job is to write a python function called quality_report() which takes a single parameter as input, a pandas 
        dataframe, and returns a data quality report in the form of a python dictionary. 
        
        DATA QUALITY REPORT:
        Your data quality report may consist of, but should not be limited to any of the following.
        - Columns containing missing, null, nan, or None values, and the count.
        - Columns containing outliers, and the count of outliers.    
        - Columns containing anomalies and the count of anomalies.
        - Duplicate rows
        - Duplicate columns
        - Columns that are constants
        - Columns that are empty
        - Columns containing useless information 
        - Columns containing mixed data types
        - Any other data quality problems by column that you notice   
        
            
        METADATA:
        You will see the first 3 rows of the dataset.
        For categorical data, you will see all of the unique values.
        You will get a data dictionary.
        
        YOUR RESPONSE:
        Your response shall only contain a Python function called quality_report(). The function shall evaluate
        the data for potential data quality problems such as those noted. The function should return a report in the 
        form of a python dictionary that simply identifies the columns that contain the issues
        
        The code should be redundant to errors, with a high likelihood of successfully executing. 
        The function may only rely on Python, pandas, numpy, scikit-learn, xgboost, SciPy, Statsmodels and no other libraries.
        
        KEY CONSIDERATIONS: 
        Your entire response must be a Python function and NO OTHER text. 
        Do NOT include an explanation of how the function works!
        Do NOT provide an example of how to use the function!
        Any text that is not Python code MUST be commented!
        The entire response MUST ONLY BE THE PYTHON FUNCTION ITESELF.     
          
        """
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f22baee48be774cda48a81' #openai
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code
def executeDataQualityReport(prompt, df):
    '''
    Executes the Python Code generated by the LLM
    '''
    print("Generating data quality report code...")
    pythonCode = getDataQualityReport(prompt)
    pythonCode = extract_python_code(pythonCode)
    print(pythonCode)
    print("Executing data quality report code...")
    function_dict = {}
    exec(pythonCode, function_dict)  # execute the code created by our LLM
    quality_report = function_dict['quality_report']  # get the function that our code created
    results = quality_report(df)
    return pythonCode, results
@st.cache_data(show_spinner=False)
def interpretDataQualityReport(report):
    message = openaiClient.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": """
            Your job is to summarize the data quality report provided. You will be provided a dictionary of 
            data quality problems. Create a bullet list summarizing the report.    
               
            """},
            {"role": "user", "content": str(report)}
        ]
    )
    return message.choices[0].message.content

def createFeatureEngineeringCode(prompt):
    message = anthropicClient.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        system="""
           You are a data scientist and feature engineering expert in Python. 
           Your job is to write a python function called engineer_features() which takes a single parameter as input, a pandas 
           dataframe, and returns the dataset with the newly engineered features as additional columns. 
           
           FEATURE ENGINEERING:
           You will be provided with information about the machine learning use case such as the modeling objectives
           and the target variable. You will also be provided with a data quality report that identifies missing values, 
           and other issues that might impede models' ability to learn from the data. 
           Based on what you know about the data, come up with some feature engineering steps that would improve a 
           machine learning model's ability to estimate the target.
           Some feature engineering steps you might consider:           
           - Consider resolving some or all of the data quality problems
           - Include anomaly detection or clustering
           - Look for ratios
           - Look for features that you could sum, and use as a numerator in a ratio
           - Interaction terms
           - polynomial features
           - normalizing and scaling
           - log transformation
           - outlier detection using Z-scores, the Interquartile Range (IQR) method, or using algorithms like Isolation Forest
           - No need to one-hot-encode categorical data
                 
           METADATA:
           You will see the first 3 rows of the dataset.
           For categorical data, you will see all of the unique values.
           You will get a data dictionary.
           You will be informed of the target variable in the machine learning project.
           You will be informed of any data quality problems. 
           You may or may not receive a first pass at generating the engineer_features() function. If you receive it,
           you can improve or add to it. 

           YOUR RESPONSE:
           Your response shall only contain a Python function called engineer_features(). 
           The code should be redundant to errors, with a high likelihood of successfully executing. 
           The function may only rely on Python, pandas, numpy, scikit-learn, xgboost, SciPy, Statsmodels and no other libraries.
           Any libraries your function requires should be imported

           KEY CONSIDERATIONS: 
           No need to one-hot-encode
           Your entire response must be the Python function and NO OTHER text. 
           Do NOT include an explanation of how the function works!
           Do NOT provide an example of how to use the function!
           Any text that is not Python code MUST be commented!
           The entire response MUST ONLY BE THE PYTHON FUNCTION ITSELF.     

           """,
        messages=[
            {"role": "user", "content": str(prompt)}
        ]
    )
    return message.content[0].text

def createFeatureEngineeringCodeGemini(prompt, system_prompt = AI_SYSTEM_PROMPT):
    '''
        Submits the prompt, gets feature engineering code
    '''
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f2135562c4c2778aa48813'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code

def createFeatureEngineeringCodeAnthropic(prompt, system_prompt = AI_SYSTEM_PROMPT):
    '''
        Submits the prompt, gets feature engineering code
    '''
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f220b5cc4961bfcda48c5b'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code



def createFeatureEngineeringCodeOpenAI(prompt, sytem_prompt = AI_SYSTEM_PROMPT):
    '''
        Submits the prompt, gets feature engineering code
    '''
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f22baee48be774cda48a81'
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code

def combineFeatureEngineeringCodeResponses(prompt, geminiFeatureEngCode, anthropicFeatureEngCode, openaiFeatureEngCode):
    '''
            Submits code from 3 LLMs, combines the solutions
    '''
    system_prompt = """
               You are a data scientist and feature engineering expert in Python. 
               You will be provided with 3 versions of a function called engineer_features().
               Your job is to combine ideas and techniques from these functions into a final function. 
               The goal is a final version that is more comprehensive and better than any of the individual functions. 
               Your final version of the engineer_features() function will take a single parameter as input, a pandas 
               dataframe, and return the dataset with the engineered features as additional columns. Be sure that your
               solution does not result in any duplicate column names.                

               METADATA:
               You will see the first 3 rows of the dataset.
               For categorical data, you will see all of the unique values.
               You will get a data dictionary.
               You will be informed of the target variable in the machine learning project.
               You will be informed of any data quality problems. 
               You may or may not receive a first pass at generating the engineer_features() function. If you receive it,
               you can improve or add to it. 

               YOUR RESPONSE:
               Your response shall only contain a Python function called engineer_features(). 
               The code should be redundant to errors, with a high likelihood of successfully executing. 
               The function may only rely on Python, pandas, numpy, scikit-learn, xgboost, SciPy, Statsmodels and no other libraries.
               Any libraries your function requires should be imported               

               KEY CONSIDERATIONS: 
               Only reference columns that actually exist in the dataset. 
               Column names must be spelled exactly as they are in the dataset. 
               Your code should be robust to errors.
               Pay close attention to data types when operating on columns!
               Ensure data type compatability! 
               I.e. cast columns to float when using numeric operations on those columns!
               I.e. cast columns to string when using string operations on those columns!   
               Be sure that the final dataframe returned does not contain duplicate column names!
               Do not duplicate feature engineering steps!                      
               No need to one-hot-encode or create dummy features.
               Your entire response must be the Python function and NO OTHER text. 
               Do NOT include an explanation of how the function works!
               Do NOT provide an example of how to use the function!
               Any text that is not Python code MUST be commented!
               The entire response MUST ONLY BE THE PYTHON FUNCTION ITSELF.     

               """
    prompt = prompt + str(geminiFeatureEngCode) + str(anthropicFeatureEngCode) + str(openaiFeatureEngCode)
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f220b5cc4961bfcda48c5b' #anthropic
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code

def getFeatureEngineeringCodeInParallel(prompt, system_prompt = AI_SYSTEM_PROMPT):
    # Create a context manager for managing the thread pool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks to the executor for each function
        future_gemini = executor.submit(createFeatureEngineeringCodeGemini,
                                        prompt, system_prompt)  # Assuming a similar function for Gemini
        future_anthropic = executor.submit(createFeatureEngineeringCodeAnthropic, prompt, system_prompt)
        future_openai = executor.submit(createFeatureEngineeringCodeOpenAI, prompt, system_prompt)

        # Wait for all futures to complete and retrieve results
        try:
            geminiFeatureEngCode = future_gemini.result()
            anthropicFeatureEngCode = future_anthropic.result()
            openaiFeatureEngCode = future_openai.result()
        except Exception as exc:
            print(f'Generated an exception: {exc}')
            return None, None, None

    return geminiFeatureEngCode, anthropicFeatureEngCode, openaiFeatureEngCode

def executeFeatureEngineeringCode(prompt, df, system_prompt = AI_SYSTEM_PROMPT):
    '''
        Executes the Python Code generated by the LLM
    '''
    print("Generating feature engineering code...")
    geminiFeatureEngCode, anthropicFeatureEngCode, openaiFeatureEngCode = getFeatureEngineeringCodeInParallel(prompt, system_prompt)

    ## don't need tought this
    pythonCode = combineFeatureEngineeringCodeResponses(prompt, geminiFeatureEngCode, anthropicFeatureEngCode, openaiFeatureEngCode)
    pythonCode = extract_python_code(pythonCode)
    print(pythonCode)
    print("Executing feature engineering code...")
    function_dict = {}
    exec(pythonCode, function_dict)  # execute the code created by our LLM
    try:
        engineer_features = function_dict['engineer_features']  # get the function that our code created
        results = engineer_features(df)
    except Exception as e:
        results = e
    return pythonCode, results

def createFeatureEngineeringCodeReattempt(prompt):
    '''
    If the attempt to execute the code fails, try again by debugging given the error.
    '''
    system_prompt = """
                   You are a data scientist and feature engineering expert in Python. 
                   You will be provided with a function called engineer_features().
                   For some reason discussed in the error message, the function fails to execute.
                   Your job is to debug and provide a working version of the function while retaining the core 
                   functionality of the function. 
                                      
                   Your final version of the engineer_features() function will take a single parameter as input, a pandas 
                   dataframe, and return the dataset with the engineered features as additional columns.               

                   METADATA:
                   You will see the first 3 rows of the dataset.
                   For categorical data, you will see all of the unique values.
                   You will get a data dictionary.
                   You will be informed of the target variable in the machine learning project.
                   You will be informed of any data quality problems. 
                   You may or may not receive a first pass at generating the engineer_features() function. If you receive it,
                   you can improve or add to it. 

                   YOUR RESPONSE:
                   Your response shall only contain a Python function called engineer_features(). 
                   The code should be redundant to errors, with a high likelihood of successfully executing. 
                   The function may only rely on Python, pandas, numpy, scikit-learn, xgboost, SciPy, Statsmodels and no other libraries.
                   Any libraries your function requires should be imported

                   KEY CONSIDERATIONS: 
                   Only reference columns that actually exist in the dataset. 
                   Column names must be spelled exactly as they are in the dataset. 
                   Your code should be robust to errors.
                   Pay close attention to data types when operating on columns!
                   Ensure data type compatability! 
                   I.e. cast columns to float when using numeric operations on those columns!
                   I.e. cast columns to string when using string operations on those columns!   
                   Be sure that the final dataframe returned does not contain duplicate column names!
                   Do not duplicate feature engineering steps!                      
                   No need to one-hot-encode or create dummy features.
                   Your entire response must be the Python function and NO OTHER text. 
                   Do NOT include an explanation of how the function works!
                   Do NOT provide an example of how to use the function!
                   Any text that is not Python code MUST be commented!
                   The entire response MUST ONLY BE THE PYTHON FUNCTION ITSELF.    

                   """
    #prompt = prompt + str(geminiFeatureEngCode) + str(anthropicFeatureEngCode) + str(openaiFeatureEngCode)
    data = pd.DataFrame([{"promptText": prompt, "systemPrompt": system_prompt}])
    API_URL = 'https://cfds-ccm-prod.orm.datarobot.com/predApi/v1.0/deployments/{deployment_id}/predictions'
    API_KEY = os.environ["DATAROBOT_API_TOKEN"]
    DATAROBOT_KEY = os.environ["DATAROBOT_KEY"]
    deployment_id = '65f22baee48be774cda48a81'  # open ai
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(API_KEY),
        'DataRobot-Key': DATAROBOT_KEY,
    }
    url = API_URL.format(deployment_id=deployment_id)
    predictions_response = requests.post(
        url,
        data=data.to_json(orient='records'),
        headers=headers
    )
    code = predictions_response.json()["data"][0]["prediction"]
    return code

def executeFeatureEngineeringCodeReattempt(prompt, df, system_prompt=AI_SYSTEM_PROMPT):
    '''
        Executes the Python Code generated by the LLM
    '''
    print("Reattempting feature engineering code...")
    geminiFeatureEngCode, anthropicFeatureEngCode, openaiFeatureEngCode = getFeatureEngineeringCodeInParallel(prompt, system_prompt)
    pythonCode = createFeatureEngineeringCodeReattempt(prompt)
    pythonCode = extract_python_code(pythonCode)
    print(pythonCode)
    print("Reattempting to execute feature engineering code...")
    function_dict = {}
    exec(pythonCode, function_dict)  # execute the code created by our LLM
    try:
        engineer_features = function_dict['engineer_features']  # get the function that our code created
        results = engineer_features(df)
    except Exception as e:
        results = e
    return pythonCode, results

def mainPage():
    st.image("datarobotLogo.png", width=200)
    st.title("AI Feature Engineer")
    st.write("This application helps find and address data quality issues using Generative AI. It can read your CSV files, or connect to a database. In addition to cleaning your data it can help you wrangle, modify and create new features for machine learning.")
    tab1, tab2, tab3, tab4 = st.tabs(["Upload and Explore", "Automated Feature Engineering", "Interactive Feature Engineering", "Launch DataRobot Project"])

    with tab1:
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        if uploaded_file is not None:
            # Read the file into a dataframe
            # df = pd.read_csv(r"C:\Users\BrettOlmstead\Downloads\real estate\Ontario Real Estate 2021 No Pictures.csv")
            df = pd.read_csv(uploaded_file)

            # Display the dataframe
            with st.expander(label="First 10 Rows", expanded=False):
                st.dataframe(df.head(10))

            try:
                with st.expander(label="Column Descriptions", expanded=False):
                    st.dataframe(df.describe(include='all'))
            except:
                pass

            try:
                with st.expander(label="Unique and Frequent Values", expanded=False):
                    st.dataframe(get_top_frequent_values(df))
            except Exception as e:
                st.write(e)

            try:
                with st.expander(label="Data Dictionary", expanded=False):
                    prompt = "First 3 Rows: \n" + str(df.head(3)) + "\n Unique and Frequent Values of Categorical Data: \n" + str(get_top_frequent_values(df))
                    with st.spinner("Making dictionary..."):
                        dictionary = getDataDictionary2(prompt, df)
                        st.markdown(dictionary)

            except Exception as e:
                st.write(e)

            try:
                with st.expander(label="Data Quality Analysis Code", expanded=False):
                    prompt = "\n Data Sample: \n" + str(df.head(3)) + "\n Unique and Frequent Values of Categorical Data: \n" + str(get_top_frequent_values(df)) + "\n Data Dictionary: \n" + str(dictionary)
                    with st.spinner("Data quality assessment..."):
                        attempts = 0
                        max_retries = 5
                        while attempts < max_retries:
                            try:
                                dataQualityReportCode, dataQualityReport = executeDataQualityReport(prompt, df)
                                break  # If the function succeeds, exit the loop
                            except Exception as e:
                                attempts += 1
                                print(f"Attempt {attempts} failed with error: {e}")
                                if attempts == max_retries:
                                    print("Max retries reached.")
                                    break

                        st.code(dataQualityReportCode, language="python")
            except:
                pass

            try:
                with st.expander(label="Data Quality Report", expanded=True):
                    with st.spinner("Executing data quality assessment..."):
                        st.write(dataQualityReport)
            except Exception as e:
                print(e)


            with tab2:
                st.subheader("Before we begin, here are some potential data quality issues to be aware of.  We'll consider these when building features.")
                dataQualityReportSummary = interpretDataQualityReport(dataQualityReport)
                st.write(dataQualityReportSummary)
                st.subheader("What is the Target in your machine learning project?")
                targetColumn = st.selectbox(label="Target", options=df.columns)
                prompt = "\n Data Sample: \n" + str(df.head(3)) + "\n Unique and Frequent Values of Categorical Data: \n" + str(get_top_frequent_values(df)) + "\n Data Dictionary: \n" + str(dictionary) + "\n Data Quality Report: \n" + str(dataQualityReport) + "\n Target Feature for ML Project: " + str(targetColumn)
                startButton = st.button(label="Start Feature Engineering")

                if startButton:
                    with st.spinner("Engineering Features... "):
                        # prompt was set above when calling data quality report. Now calling feature engineering
                        attempts = 0
                        max_retries = 5
                        while attempts < max_retries:
                            print("Attempt: " +str(attempts))
                            try:
                                if attempts == 0:
                                    pythonCode, results = executeFeatureEngineeringCode(prompt, df)
                                else:
                                    pythonCode, results = executeFeatureEngineeringCodeReattempt(
                                        "Function to fix: \n" + str(pythonCode) + "\nERROR MESSAGE: \n" + str(results) + "\nOTHER INFO: \n" + user_prompt, df, system_prompt)

                                if isinstance(results, pd.core.frame.DataFrame):
                                    break
                                attempts += 1
                            except Exception as e:
                                attempts += 1
                                print(f"Attempt {attempts} failed with error: {e}")
                                if attempts == max_retries:
                                    print("Max retries reached.")
                                    break


                        with st.expander(label="Feature Engineering Code", expanded=False):
                            st.code(pythonCode, language="python")
                        with st.expander(label="Features", expanded=True):
                            st.write(results)


            with tab3:
                st.subheader("What feature engineering steps would you like me to implement?")
                ## diictionary in score 
                ## df frame in scope 
                ## need a target column string in scope (or ensure) 
                ###                
                # st.write(dataQualityReportSummary)
                st.subheader("What is the Target in your machine learning project?")
                targetColumn = st.selectbox(label="Target Feature", options=df.columns)
                ###

                user_prompt = st.text_input("What would you like to do")
                
                system_prompt = INTERACTIVE_FE_SYSTEM_PROMPT
                system_prompt += "\n Data Sample: \n" + str(df.head(3)) + "\n Unique and Frequent Values of Categorical Data: \n" + str(get_top_frequent_values(df)) + "\n Data Dictionary: \n" + str(dictionary) + "\n Target Feature for ML Project: " + str(targetColumn)
                                
                startButton = st.button(label="Start Interative FeatureFeature Engineering")


                if startButton:
                    with st.spinner("Engineering Features... "):
                        ## user prompt + prompt 
                        # prompt was set above when calling data quality report. Now calling feature engineering
                        attempts = 0
                        max_retries = 5
                        while attempts < max_retries:
                            print("Attempt: " +str(attempts))
                            try:
                                if attempts == 0:
                                    pythonCode, results = executeFeatureEngineeringCode(user_prompt, df, system_prompt)
                                else:
                                    pythonCode, results = executeFeatureEngineeringCodeReattempt(
                                        "Function to fix: \n" + str(pythonCode) + "\nERROR MESSAGE: \n" + str(results) + "\nORIGINAL USER PROMPT: \n" + user_prompt, df, "Fix thee function based on the users expected behavior"
                                        )

                                if isinstance(results, pd.core.frame.DataFrame):
                                    break
                                attempts += 1
                            except Exception as e:
                                attempts += 1
                                print(f"Attempt {attempts} failed with error: {e}")
                                if attempts == max_retries:
                                    print("Max retries reached.")
                                    break


                        with st.expander(label="Feature Engineering Code", expanded=False):
                            st.code(pythonCode, language="python")
                        with st.expander(label="Features", expanded=True):
                            st.write(results)                


            with tab4:
                project_name = st.text_input("Name your DataRobot Project")
                # st.write(df)
                import datarobot as dr
                if st.button(label="Launch DataRobot Project"):
                    with st.spinner("Launch DataRobot Project..."):
                        client = dr.Client()
                        project = dr.Project.create(sourcedata = df, project_name = "LC_TEST")
                        project.set_worker_count(-1)
                    with st.spinner("Setting target and starting modeling"):
                        project.analyze_and_model(target="is_bad")
                        st.markdown(project.get_uri())
                    # project.get_uri()
                    # automl = drx.AutoMLModel(name = project_name)
                    # st.markdown(f"https://app.datarobot.com/projects/{automl.dr_project.id}/models")
                    # with st.spinner("Launching DataRobot Project..."):
                    #     automl.fit(df,targetColumn)
                        
                    

                



# Main app
def _main():
    hide_streamlit_style = """
    <style>
    # MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)  # This lets you hide the Streamlit branding


    mainPage()


if __name__ == "__main__":
    _main()

import requests
import pandas as pd
import os
import streamlit as st
import time
st.set_page_config(page_title="Data Analyst", layout="wide")
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

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
    print(pythonCode.replace("```python", "").replace("```", ""))
    pythonCode = pythonCode.replace("```python", "").replace("```", "")
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
        # Find top 10 most frequent values for the column
        top_values = df[col].value_counts().head(10).index.tolist()

        # Append the column name and its frequent values to the results
        results.append({'Non-numeric column name': col, 'Frequent Values': top_values})

    # Create a new DataFrame for the results
    result_df = pd.DataFrame(results)

    return result_df
def mainPage():
    st.image("datarobotLogo.png", width=200)
    st.title("AI Data Analyst")
    st.write("DataRobot's recommendation system suggests and integrates additional data sources to enhance model accuracy, starting with a user-friendly interface. Users can upload any demo dataset into the app through drag-and-drop or browsing. The app inspects the file, gathering metadata like column names, data samples, and frequent values. Utilizing Generative AI, it builds a descriptive data dictionary. In the Analyze tab, users can query the dataset, as the language model interprets and writes code to extract relevant data, even when column names differ. Results are displayed in tables and visualized with intelligently selected charts. The system also offers insights on aspects like profitability and growth and suggests follow-up questions for deeper analysis using other data in the system, ensuring a thorough and intuitive exploration of datasets.")
    tab1, tab2 = st.tabs(["Upload Data", "Analyze"])

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
            except:
                pass

            try:
                with st.expander(label="Data Dictionary", expanded=False):
                    data = "First 3 Rows: \n" + str(df.head(3)) + "\n Unique and Frequent Values of Categorical Data: \n" + str(get_top_frequent_values(df))
                    with st.spinner("Making dictionary..."):
                        dictionary = getDataDictionary(data)
                        st.markdown(dictionary)
            except:
                pass

            with tab2:
                st.subheader("Ask a question about the data.")
                prompt = st.text_input(label="Question")
                submitQuestion = st.button(label="Ask")

                if submitQuestion:
                    with st.spinner("Analyzing... "):
                        prompt = "Business Question: " +str(prompt) +"\n Data Sample: \n" + str(df.head(3)) + "\n Unique and Frequent Values of Categorical Data: \n" + str(get_top_frequent_values(df)) + str("\n Data Dictionary: \n") + str(dictionary)

                        attempts = 0
                        max_retries = 3
                        while attempts < max_retries:
                            try:
                                pythonCode, results = executePythonCode(prompt, df)
                                break  # If the function succeeds, exit the loop
                            except Exception as e:
                                attempts += 1
                                print(f"Attempt {attempts} failed with error: {e}")
                                if attempts == max_retries:
                                    print("Max retries reached.")
                                    # st.write("I'm having trouble plotting this.")
                                    break

                        try:
                            with st.expander(label="Code", expanded=False):
                                st.code(pythonCode, language="python")
                            with st.expander(label="Result", expanded=True):
                                st.dataframe(results)
                        except:
                            st.write("I tried a few different ways, but couldn't get a working solution. Rephrase the question and try again.")

                    with st.spinner("Visualization in progress..."):
                        with st.expander(label="Charts", expanded=True):

                            attempt_count = 0
                            max_attempts = 2
                            while attempt_count < max_attempts:
                                try:
                                    fig1, fig2 = createCharts(prompt, pythonCode, results)
                                    st.plotly_chart(fig1, theme="streamlit", use_container_width=True)
                                    st.plotly_chart(fig2, theme="streamlit", use_container_width=True)
                                    break  # If operation succeeds, break out of the loop
                                except Exception as e:
                                    attempt_count += 1
                                    print(f"Chart Attempt {attempt_count} failed with error: {e}")
                                if attempt_count >= max_attempts:
                                    print("Max charting attempts reached, handling the failure.")
                                    st.write("I was unable to plot the data.")
                                    # Handle the failure after the final attempt
                                else:
                                    time.sleep(2)
                                    print("Retrying the charts...")


                        with st.expander(label="Business Analysis", expanded=True):
                            with st.spinner("Business analysis..."):
                                try:
                                    analysis = getBusinessAnalysis(prompt + str(results))
                                    st.markdown(analysis.replace("$", "\$"))
                                except:
                                    st.write("I am unable to provide the analysis. Please rephrase the question and try again.")

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

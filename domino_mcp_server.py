# MCP Server functions that wrap the Domino API
# Domino API docs, run a job example: https://docs.dominodatalab.com/en/latest/api_guide/8c929e/rest-api-reference/#_startJob

from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
import requests
import asyncio
import os
from dotenv import load_dotenv
import re
import webbrowser
import urllib.parse

load_dotenv()

# Load API key from environment variable
domino_api_key = os.getenv("DOMINO_API_KEY")
domino_host = os.getenv("DOMINO_HOST")

if not domino_api_key:
    raise ValueError("DOMINO_API_KEY environment variable not set.")

# Initialize the Fast MCP server
mcp = FastMCP("domino_server")

def _validate_url_parameter(param_value: str, param_name: str) -> str:
    """
    Validates and URL-encodes a parameter for safe use in URLs.
    Supports international characters by encoding them properly.
    
    Args:
        param_value (str): The parameter value to validate and encode
        param_name (str): The name of the parameter (for error messages)
        
    Returns:
        str: The URL-encoded parameter value
        
    Raises:
        ValueError: If the parameter contains unsafe URL characters
    """
    # Basic safety check - reject if contains dangerous chars that could break URL structure
    if any(char in param_value for char in ['/', '\\', '?', '#', '&', '=', '%']):
        raise ValueError(f"Invalid {param_name}: '{param_value}' contains unsafe URL characters")
    
    # URL encode to handle international characters safely
    return urllib.parse.quote(param_value, safe='')

def _filter_domino_stdout(stdout_text: str) -> str:
    """
    Filters the stdout text from a Domino job run to extract the relevant output.
    It extracts text between the specified start and end markers.
    """
    start_marker = "### Completed /mnt/artifacts/.domino/configure-spark-defaults.sh ###"
    end_marker = "Evaluating cleanup command on EXIT"

    try:
        start_index = stdout_text.index(start_marker) + len(start_marker)
        # Find the end marker starting from the position after the start marker
        end_index = stdout_text.index(end_marker, start_index)
        # Extract the text between the markers, stripping leading/trailing whitespace
        filtered_text = stdout_text[start_index:end_index].strip()
        return filtered_text
    except ValueError:
        # Handle cases where one or both markers are not found
        # Optionally, return the original text or a specific message
        print("Warning: could not parse domino job output")
        return "Could not find start or end markers in stdout."

def _extract_and_format_mlflow_url(text: str, user_name: str, project_name: str) -> str | None:
    """
    Finds an MLflow URL in the format http://127.0.0.1:8768/#/experiments/.../runs/...
    and reformats it to the Domino Cloud URL format.
    """
    # Regex to find the specific MLflow URL pattern
    pattern = r"http://127\.0\.0\.1:8768/#/experiments/(\d+)/runs/([a-f0-9]+)"
    match = re.search(pattern, text)

    if match:
        experiment_id = match.group(1)
        run_id = match.group(2)
        # Construct the new URL
        new_url = f"{domino_host}/experiments/{user_name}/{project_name}/{experiment_id}/{run_id}"
        return new_url
    else:
        return None # Return None if the pattern is not found

@mcp.tool()
async def check_domino_job_run_results(user_name: str, project_name: str, run_id: str) -> Dict[str, Any]:
    """
    The check_domino_job_run_results function returns the results from the job run from the domino data science platform, these results might contain model training metrics that might help inform a follow-up job run that further optimizes a model.

    Args:
        user_name (str): The user name associated with the Domino Project
        project_name (str): The name of the Domino project.
        run_id (str): The run id of the job run to return the status of
    """
    # Validate and encode input parameters
    encoded_user_name = _validate_url_parameter(user_name, "user_name")
    encoded_project_name = _validate_url_parameter(project_name, "project_name")
    encoded_run_id = _validate_url_parameter(run_id, "run_id")
    
    api_url = f"{domino_host}/v1/projects/{encoded_user_name}/{encoded_project_name}/run/{encoded_run_id}/stdout"
    headers = {
        "X-Domino-Api-Key": domino_api_key
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        raw_stdout = response.json().get('stdout', '') # Use .get for safety
        
        # Initial filtering between markers
        initially_filtered_stdout = _filter_domino_stdout(raw_stdout)
        
        # Attempt to extract and format the MLflow URL
        mlflow_url = _extract_and_format_mlflow_url(initially_filtered_stdout, user_name, project_name)
        
        final_filtered_stdout = initially_filtered_stdout
        # If MLflow URL was found, remove the original URL line(s) from the results
        if mlflow_url:
            # Define the pattern for the original local MLflow URL (run-specific)
            local_mlflow_run_pattern = r"http://127\.0\.0\.1:8768/#/experiments/\d+/runs/[a-f0-9]+"
            # Define the pattern for the experiment link
            local_mlflow_experiment_pattern = r"View experiment at: http://127\.0\.0\.1:8768/#/experiments/\d+"
            
            # Split into lines, filter out lines containing either pattern, and rejoin
            lines = initially_filtered_stdout.splitlines()
            filtered_lines = [line for line in lines if not re.search(local_mlflow_run_pattern, line) and not re.search(local_mlflow_experiment_pattern, line)]
            final_filtered_stdout = "\n".join(filtered_lines).strip()

        # Construct the result dictionary
        result = {"results": final_filtered_stdout}
        if mlflow_url:
             result["mlflow_url"] = mlflow_url # Add the formatted URL if found
             
    except requests.exceptions.RequestException as e:
        result = {"error": f"API request failed: {e}"}
    except Exception as e:
        result = {"error": f"An unexpected error occurred: {e}"}

    return result

@mcp.tool()
async def check_domino_job_run_status(user_name: str, project_name: str, run_id: str) -> Dict[str, Any]:
    """
    The check_domino_job_run_status function checks the status of a job run to determine if its finished or in-progress or had an error. A run can sometimes take 1 or more minutes, so it might be necessary to call this a few times until it's finished before using a different function to read the results.

    Args:
        user_name (str): The user name associated with the Domino Project
        project_name (str): The name of the Domino project.
        run_id (str): The run id of the job run to return the status of
    """
    # Validate and encode input parameters
    encoded_user_name = _validate_url_parameter(user_name, "user_name")
    encoded_project_name = _validate_url_parameter(project_name, "project_name")
    encoded_run_id = _validate_url_parameter(run_id, "run_id")
    
    api_url = f"{domino_host}/v1/projects/{encoded_user_name}/{encoded_project_name}/runs/{encoded_run_id}"
    headers = {
        "X-Domino-Api-Key": domino_api_key
    }
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        result = response.json()
    except requests.exceptions.RequestException as e:
        result = {"error": f"API request failed: {e}"}
    except Exception as e:
        result = {"error": f"An unexpected error occurred: {e}"}

    return result

@mcp.tool()
async def run_domino_job(user_name: str, project_name: str, run_command: str, title: str) -> Dict[str, Any]:
    """
    The run_domino_job function runs a command as a job on the domino data science platform, typically a python script such a 'python my_script.py --arg1 arv1_val --arg2 arv2_val' on the Domino cloud platform.

    Args:
        user_name (str): The user name associated with the Domino project.
        project_name (str): The name of the Domino project.
        run_command (str): The command to run on the domino platform. Example: 'python my_script.py --arg1 arv1_val --arg2 arv2_val'
        title (str): A title of the job that helps later identify the job. Example: 'running training.py script'
    """
    # Validate and encode input parameters
    encoded_user_name = _validate_url_parameter(user_name, "user_name")
    encoded_project_name = _validate_url_parameter(project_name, "project_name")
  
    # Construct the API URL
    # must be in this format: https://domino.host/v1/projects/user_name/project_name/runs
    api_url = f"{domino_host}/v1/projects/{encoded_user_name}/{encoded_project_name}/runs"

    # Prepare the request headers
    headers = {
        "X-Domino-Api-Key": domino_api_key,
        "Content-Type": "application/json",
    }

    # Prepare the request body according to the specified requirements
    # for the /v1/projects/{user_name}/{project_name}/runs endpoint.
    payload = {
        "command": run_command.split(), # Split the command string into a list
        "isDirect": False, # Matching successful curl command
        "title": title,
        "publishApiEndpoint": False,
    }


    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        result = response.json()
    except requests.exceptions.RequestException as e:
        result = {"error": f"API request failed: {e}"}
    except Exception as e:
        result = {"error": f"An unexpected error occurred: {e}"}

    return result

@mcp.tool()
def open_web_browser(url: str) -> bool:
    """Opens the specified URL in the default web browser.

    Args:
        url: The URL to open.

    Returns:
        True if the browser was opened successfully, False otherwise.
    """
    try:
        webbrowser.open_new_tab(url)
        return True
    except webbrowser.Error:
        return False


# async def main():
#     
#     print("making domino API call")
#     #result = await run_domino_job(user_name='etan_lightstone', project_name='diabetes-predict', run_command='python test.py', title='test run')
#     print(result)


if __name__ == "__main__":
    # Initialize and run the server using stdio transport
    mcp.run(transport='stdio') 
    #asyncio.run(main())
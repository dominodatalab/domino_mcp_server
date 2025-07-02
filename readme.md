# Domino MCP Server

This project provides a Model Context Protocol (MCP) server that when combined with AI coding tools like Cursor allows you to build models via agentic code automation, run training jobs, track experiments, optimize models, and perform exploratory data analysis leveraging the Domino Data Lab platform. *Accelerating data science work doesn’t just happen by involving an AI Coding assistant in writing python scripts, but also by involving the AI agent in the full development, validation and optimization lifecycle.*

By using a “vibe modeling” approach combined with Domino’s Enterprise AI Platform, Every iteration an AI co-pilot performs is automatically tracked and is reproducible in Domino. This addresses the core challenge of governance in the AI tools era.

More information about MCP Servers with Cursor can be found here.

## LLM tools of the MCP Server

*   **Run Domino Jobs:** Execute commands (e.g., Python scripts) as jobs within a specified Domino project.
*   **Check Job Status:** Retrieve the status and results of a specific Domino job run.
*   **Check Job Results:** Retrieve the status and results of a specific Domino job run.

## How it Works

The `domino_mcp_server.py` script uses the `fastmcp` library to define an MCP server. It exposes two functions (`run_domino_job` and `check_domino_job_run_result`) as tools that Cursor can call. These functions make authenticated REST API calls to the Domino platform using the `DOMINO_API_KEY` and `DOMINO_HOST` loaded from the `.env` file (local to the mcp server not your cursor project).

The server is configured to run using `stdio` transport, meaning Cursor starts and manages the Python script process locally (using `uv run`) and communicates with it via standard input/output.

## Setup

Step 1.  **Clone the Repository:**
```bash
# If you haven't already, clone the repository containing this server
git clone https://github.com/dominodatalab/domino_mcp_server.git
cd domino_mcp_server
```

Step 2.  **Install Dependencies:**
    This server requires Python and the `fastmcp` and `requests` libraries. Ensure you have `uv` installed ([https://github.com/astral-sh/uv](https://github.com/astral-sh/uv)). Install the dependencies using `uv`:
```bash
uv pip install -e .
```

Step 3.  **Set API Key and Host URL using .env file:**
    The server needs your Domino API key and host URL to authenticate requests and connect to your Domino instance. 
Obtain your API key from your Domino account settings. 
Create a file named `.env` in the root directory of this project (the same directory as `domino_mcp_server.py`) and …
Add the following lines, replacing the values with your actual credentials:
```dotenv
DOMINO_API_KEY='your_api_key_here'
DOMINO_HOST='https://your-domino-instance.com'
```


Step 4.  **Configure Cursor:**
    To make Cursor aware of this MCP server, you need to configure it. 
Create or edit the MCP configuration file for your project or globally:
    *  **Project-specific:** Create a file named `.cursor/mcp.json` in the root of your project directory.
    *   **Global:** Create a file named `~/.cursor/mcp.json` in your home directory.

Add the following JSON configuration to the file, adjusting the `<path_to_directory>` to the actual absolute path of the directory containing the `domino_mcp_server.py` script and your `.env` file:

   ```json
        {
            "mcpServers": {
                "domino_server": {
                "command": "uv",
                "args": [
                    "--directory",
                    "/full/directory/path/to/domino_mcp_server",
                    "run",
                    "domino_mcp_server.py"
                ] 
                }
            }
        }
   ```
Replace `<path_to_directory>` with the correct absolute path to the folder containing `domino_mcp_server.py` and `.env`.*
    *`uv run` will automatically load the `DOMINO_API_KEY` from the `.env` file located in the specified directory.*

Step 5.  **Add Project Cursor Rule:**
    To optimize the agent's behavior with Domino, create a cursor rule file in your datascience project called `.cursor/rules/domino-project-rule.mdc` in your project root and  ** Set this rule to "Always" in Cursor's rule settings to ensure it's consistently applied**

** Rule contents to paste in **
```
You are a Domino Data Lab powered agentic coding tool that helps write code in addition to running tasks on the Domino Data Lab platform on behalf of the user using available tool functions provided by the domino_server MCP server. Including functions like domino_server. Whenever possible run commands as domino jobs rather than on the local terminal. 

The domino project name and user name are required and available in a file called domino_project_settings.md which needs to be used in most tool calls by the agentic assistant.

When running a job, always check its status and results if completed and briefly explain any conclusions from the result of the job run. If a job result ever includes an mflow or experiment run URL, always share that with the user using the open_web_browser tool.

Any requests related to understanding or manipulating project data should assume a dataset file is already part of the domino project and accessible via job runs. Always create scripts to understand and transform data via job runs. The script can assume all project data is accessible under the '/mnt/data/' directory or the '/mnt/imported/data/' directory, be sure to understand the full path to a dataset file before using it by running a job to list all folder contents recursively. Analytical outputs should be in plain text tabular format sent to stdout, this makes it easier to check results from the job run.

Always check if our local project has uncommitted changes, you must commit and push changes before attempting to run any domino jobs otherwise domino can't see the new file changes.
```

<br />

Step 6.  **Create Domino Project Settings:**
    Create a file named `domino_project_settings.md` in your project root with your Domino project details:
```markdown
# Domino project settings to use with the mcp server domino_server and its job runner functions
project_name="your-project-name"
user_name="your_username"
```
    Replace `"your-project-name"` and `"your_username"` with your actual Domino project name and username.

Step 7.  **Restart Cursor:** Restart Cursor completely to load the new MCP configuration.

Step 8.  **Verify:** Go to Cursor Settings -> Context -> Model Context Protocol. You should see "domino_server" listed under Available Tools.

## Usage in Cursor

Once the MCP server is configured and the project files are set up, you can interact with the Domino server directly in the Cursor chat:

[Important: Make sure that the coding assistant has made a git commit before running a job.](#important-warning)

** Quick example prompts to run a job (Cursor must be in 'agent' mode):**
```
Run the script train_my_model.py, Check that the job run executed correctly afterwards and summarize the results from the job.
```

```
Read how the domino_trainer.py is called and run two seperate jobs, one using a larger neural net and the other smaller, both can be 20 epochs.
```

Cursor's agent will understand your request and use the appropriate tool from the `domino_server`. It will ask for confirmation before executing the tool (unless you have auto-run enabled). The results from the Domino API will be displayed in the chat.

## Suggested Prompts to Try

Once your setup is complete, here are some example prompts that demonstrate the full capabilities of the Domino MCP server:

### Data Exploration
```
Explore what datasets are available in this project. List all files in the /mnt/data/ and /mnt/imported/data/ directories and show me the first few rows of any CSV files you find.
```

```
Analyze the diabetes dataset associated with this project and evaluate its usefulness for the purpose of training a diabetes prediction model. Create and run a data transformation script if any data engineering is needed to better adapt it for model training.
```

```
Create a script that analyzes the structure and basic statistics of all datasets in this project, then run it as a Domino job.
```

### Model Training and Experimentation
```
Given the diabetes data we just engineered under '/mnt/data/diabetes_project' in this project, create a PyTorch model architecture in one file for a customizable neural network we can use to predict diabetes that we'll train with the data. Let's keep it at 4 fully connected layers, with customizable hidden dimensions. Create a separate commandline executable script that we can use to run the training for different configurations of the model and training routine. Ensure we use mlflow tracking to track metrics, params, and log the model itself.
```

```
Understand how the <filename> script works and use it to train a small neural network for the diabetes model. Iterate until the model is optimized enough.
```

```
Run a hyperparameter tuning experiment with 3 different configurations and compare the results.
```

### Data Processing
```
Create a data preprocessing script that cleans and transforms the raw data, saves the processed version, then run it as a Domino job.
```

```
Generate a comprehensive data quality report for our main dataset and save the results to a file.
```

### Code Analysis and Execution
```
Analyze my existing training script and run it with different parameter combinations as separate Domino jobs.
```

```
Check if I have any uncommitted changes, commit them if needed, then run my latest model training script.
```

### Experiment Tracking
```
Run an experiment that compares three different algorithms on our dataset, make sure to log all metrics to MLflow, and share the experiment URL with me.
```

```
Create a script that loads our best model and evaluates it on test data, logging the results to MLflow.
```

### Project Management
```
Show me the status of all my recent Domino job runs and summarize what each one accomplished.
```

```
Create a comprehensive analysis report of our project's model performance over time based on previous job runs.
```

These prompts leverage the intelligent cursor rule to automatically handle git commits, run jobs on Domino instead of locally, and provide comprehensive analysis of results.


## Important Warning

**The coding assistant sometimes forgets to run a git commit and push before executing Domino jobs.** Since Domino jobs run on the remote repository state, any uncommitted local changes will not be visible to the job execution environment. 

**Always keep an eye out for this and manually commit and push your changes if the assistant fails to do so before running a job.** You can quickly check for uncommitted changes and commit them with:
```bash
git status
git add .
git commit -m "Update files for domino job"
git push
```


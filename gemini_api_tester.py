import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Retrieves your API key from .env
personal_key = os.getenv("GEMINI_API_KEY")

if not personal_key:
    print("Error: invalid or unset API key")

# Sets up the Gemini client
client = genai.Client(api_key=personal_key)

# Attempts a basic fun fact prompt of the specified Gemini model
try:
    response = client.models.generate_content(
        model = "gemini-3.5-flash-lite",
        contents = "Say '[Virtual environment properly set up and API key authenticated]' and provide a fun, random fact."
    )

    print(response.text)

except Exception as e:
    print(f"Error: API request failed due to {e}")


#   First time running guide (commands may differ depending on OS; for reference, I'm on Windows 11):

#       1. Enter the cloned repository through a CLI and run the command "python -m venv venv" to set up the virtual environment.

#       2. Then, run the virtual environment with the following script "venv\Scripts\activate.bat".

#       3. You should be within the virtual environment and the CLI should reflect this. 
#          Next, run the command "pip install -r dependencies.txt" to install the required libraries for the virutal environment.

#       4. Now, copy .env.template as simply ".env" and reassign "GEMINI_API_KEY" to your API key. 
#          If you only modify the template, the program will be unable to retrieve your API key as it strictly looks for ".env"

#       5. Finally, run this program using the command "python gemini_api_tester.py" and behold some fun, random fact! 
#          Feel free to mess around with this file to experiment with using the Gemini API as we work on this project!

#       6. To terminate the virtual environment, simply run the command "deactivate".

#       7. Once all of this is done, the venv folder will retain the installed libraries from dependencies.txt so the general workflow for this
#          project from here on out is as follows:

#               - Enter the cloned repository in a CLI.

#               - Run the "venv\Scripts\activate.bat" script.

#               - Work on the project (You can modify the .py files in an editor and run any new changes while the virtual environment is running).

#       Note: your .env file and venv/ folder (as well as this file once everyone has pulled it) are in .gitignore so they will not be present in commits.

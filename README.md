# Coding & Testing Assistant!

This repository contains the implementation of an AI-driven (Open AI GPT) code snippet generation application. The application aims to generate code snippets in multiple programming and communication languages based on user input and feedback. The application also supports test case generation and verification based on code and user feedback.

## Project Overview

The project is designed to meet the following key requirements:

- Generate code snippets in Python and Javascript. It also has other programming language support if needed.
- Supports feedback and improvement of generated code snippets.
- Provide functionality for generating and improving test cases.
- Enable running tests and improving code based on test results.
- Ensure proper handling of prompt injection for security.

## Getting Started

To set up the project locally, follow these steps:

1. Clone this repository to your local machine.
2. Create a `.env` file based on the provided `.env.example` and add the required environment variables. The docker file handles the requirements.txt.
3. Run the provided script `./start-docker-server.sh` to start the server locally. Make this an executable with chmod. sudo privileges not required.
4. Access the application at `http://localhost:8000` in your browser.

## Project Structure

The project structure is organized as follows:

- `app.py`: Contains the backend APIs implemented using FastAPI.
- `templates/`: Directory containing HTML templates for frontend rendering.
- `snippet.db`: SQLite database for storing generated code snippets.
- `requirements.txt`: File listing project dependencies.
- `.env.example`: Example environment variables file. The .env file needs to be created and populated accordingly.

## Usage

Once the application is running, follow these steps to use it:

1. Access the application in your browser and navigate to the provided URL.
2. Use the interface to generate, view, and manage code snippets.
3. Provide feedback to improve the generated code snippets.
4. Generate and improve test cases for the code snippets.
5. Run tests to validate the code and improve it based on test results.

## Notes
1. The ./start-docker-server.sh file is slightly modified from the original and contains an extra line of code to source variables from .env file. In case of any errors please check and/or comment this.
2. The .env.example file containes the existing environmental variables used, so please create a copy and rename it and add the respective values.

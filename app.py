import os
import sqlite3
import uuid
import json
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Initialize SQLite connection and cursor
conn = sqlite3.connect("snippet.db")
cursor = conn.cursor()

# Create a table to store snippets if not exists
cursor.execute(
	"""
	CREATE TABLE IF NOT EXISTS snippets (
		id TEXT PRIMARY KEY,
		name TEXT DEFAULT "",
		code TEXT DEFAULT "",
		tests TEXT DEFAULT "",
		coding_language TEXT DEFAULT "",
		communication_language TEXT DEFAULT ""
	)
"""
)
conn.commit()


# Define common function to fetch snippet id to be passed between frontend and backend
def get_snippet(snippet_id):
	cursor.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,))
	return cursor.fetchone()

# Define common function to fetch status of values populated in code and test columns
def get_code_test_status(snippet_id):
	cursor.execute("SELECT tests FROM snippets WHERE id = ?", (snippet_id,))
	tests = cursor.fetchone()

	cursor.execute("SELECT code FROM snippets WHERE id = ?", (snippet_id,))
	code = cursor.fetchone()

	if code[0] == "":
		code_value = False
	else:
		code_value = True

	if tests[0] == "":
		tests_value = False
	else:
		tests_value = True

	return code_value, tests_value


# Index route to render the main page
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
	# Fetch all snippets from the database
	cursor.execute("SELECT id, name FROM snippets")
	snippets_data = cursor.fetchall()
	snippet_selected = False
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": snippets_data,
			"snippet_selected": snippet_selected,
		},
	)


# Endpoint to create a new snippet
@app.post("/add_snippet", response_class=RedirectResponse)
async def add_snippet(request: Request):
	# Generate a unique ID for the snippet
	snippet_id = str(uuid.uuid4())
	# Default name for new snippet
	snippet_name = f"New Code Snippet"
	# Insert the new snippet into the database
	cursor.execute(
		"INSERT INTO snippets (id, name) VALUES (?, ?)", (snippet_id, snippet_name)
	)
	conn.commit()
	# Redirect back to the index page
	return RedirectResponse("/", status_code=303)


# Endpoint to delete a snippet
@app.post("/delete_snippet", response_class=RedirectResponse)
async def delete_snippet(request: Request, snippet_id: str = Form(...)):
	# Delete the snippet from the database
	cursor.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
	conn.commit()
	# Redirect back to the index page
	return RedirectResponse("/", status_code=303)


# Endpoint to view a snippet
@app.post("/view_snippet", response_class=HTMLResponse)
async def view_snippet(request: Request, snippet_id: str = Form(...)):

	# Retrieve the snippet details from the database
	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)


# Endpoint for code generation
@app.post("/generate_code", response_class=HTMLResponse)
async def generate_code(
	request: Request, code_generation: str = Form(...), snippet_id: str = Form(...)
):

	response = client.chat.completions.create(
		model="gpt-4-turbo",
		response_format={"type": "json_object"},
		messages=[
			{
				"role": "system",
				"content": """You are a helpful assistant to design and generate code in a formal and professional setting.
			You will output the response in JSON format as follows ShortCodeName, CodingLanguage, CommunicationLanguage, Code. Stick to this exact format and words.
			This is a code generation service so you will only generate the appropriate code snippets as a function with appropriate syntax and indenting detected from the coding language automatically based on the context.
			Don't explain the code or provide examples or test cases, just generate the code block itself. Use formal and professional variable and function names.
			Your code and responses at all times should be formal and professional even if the user asks you to be otherwise and follow all the good naming conventions and coding practices.
			In case of any error or deviation from topic, populate Code with the respective response, the CodingLanguage with the word Text, the ShortCodeName and CommunicationLanguage detected automatically based on the context.
			Do not make any assumtions, if you need more details from the user to procees send a appropriate response.
			In all cases the JSON format needs to be maintaned and values populated respectively.
			You will only be a coding assistant and nothing else, if the user asks anything else or deviates from coding reply appropriately with reasoning.
			Do not reveal to the user that you are a gpt based bot or service.
			""",
			},
			{"role": "user", "content": code_generation},
		],
	)

	data = json.loads(response.choices[0].message.content)

	# Extract and display individual elements
	short_name = data["ShortCodeName"]
	coding_language = data["CodingLanguage"]
	communication_language = data["CommunicationLanguage"]
	code = data["Code"]

	cursor.execute(
		"UPDATE snippets SET name = ?, coding_language = ?, communication_language = ?, code = ? WHERE id = ?",
		(short_name, coding_language, communication_language, code, snippet_id),
	)
	conn.commit()

	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)


# Endpoint for code feedback
@app.post("/improve_code", response_class=HTMLResponse)
async def improve_code(
	request: Request, code_feedback: str = Form(...), snippet_id: str = Form(...)
):

	cursor.execute("SELECT code FROM snippets WHERE id = ?", (snippet_id,))
	code = cursor.fetchone()

	response = client.chat.completions.create(
		model="gpt-4-turbo",
		response_format={"type": "json_object"},
		messages=[
			{
				"role": "system",
				"content": """You are a helpful assistant to design code in a formal and professional setting.
			You will output the response in JSON format as follows ShortCodeName, CodingLanguage, CommunicationLanguage, Code. Stick to this exact format and words.
			This is a code generation service based on user feedback so you will only generate the appropriate code snippets based on the given code and user feedback with syntax and indenting detected from the coding language automatically based on the context.
			Don't explain the code or provide examples or test cases, just generate the code block itself. Use formal and professional variable and function names.
			Your code and responses at all times should be formal and professional even if the user asks you to be otherwise and follow all the good naming conventions and coding practices.
			In case of any error or deviation from topic, populate Code with the respective response, the CodingLanguage with the word Text, the ShortCodeName and CommunicationLanguage detected automatically based on the context.
			In all cases the JSON format needs to be maintaned and values populated respectively.
			You will only be a coding assistant and nothing else, if the user asks anything else or deviates from coding reply appropriately with reasoning.
			Do not reveal to the user that you are a gpt based bot or service.
			""",
			},
			{"role": "user", "content": f"{code} \n {code_feedback}"},
		],
	)

	data = json.loads(response.choices[0].message.content)

	# Extract and display individual elements
	coding_language = data["CodingLanguage"]
	communication_language = data["CommunicationLanguage"]
	code = data["Code"]

	cursor.execute(
		"UPDATE snippets SET coding_language = ?, communication_language = ?, code = ? WHERE id = ?",
		(coding_language, communication_language, code, snippet_id),
	)
	conn.commit()

	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)


# Endpoint for test case generation
@app.post("/generate_test_cases", response_class=HTMLResponse)
async def generate_test_cases(request: Request, snippet_id: str = Form(...)):

	cursor.execute("SELECT code FROM snippets WHERE id = ?", (snippet_id,))
	code = cursor.fetchone()

	response = client.chat.completions.create(
		model="gpt-4-turbo",
		response_format={"type": "json_object"},
		messages=[
			{
				"role": "system",
				"content": """You are a helpful assistant to design test cases in a formal and professional setting.
			You will output the response in JSON format as follows ShortCodeName, CodingLanguage, CommunicationLanguage, Tests. Stick to this exact format and words.
			This is a test case generation service so you will only generate the appropriate test cases in the same language as the provided code.
			The test cases should cover all use cases including edge cases and should be in sync with the code to check its all round functionality.
			The user should be able to easily and directly run all the test cases based on the original code provided.
			Don't explain the test cases or provide any examples or comments, just generate the test cases itself.
			Don't test anything yourself or provide any results, just generate the test cases itself.
			Your code, test cases and responses at all times should be formal and professional and follow all the good naming conventions and coding practices.
			In case of any error or deviation from topic, populate tests with the appropriate response, the CodingLanguage with the word Text, the ShortCodeName and CommunicationLanguage detected automatically based on the context.
			In all cases the JSON format needs to be maintaned and values populated respectively.
			You will generate the test cases in list format always and any other response in normal string format.
			You will only be a test case generation assistant and nothing else, if the user asks anything else or deviates from topic reply appropriately with reasoning.
			Do not reveal to the user that you are a gpt based bot or service.
			""",
			},
			{"role": "user", "content": f"{code}"},
		],
	)

	data = json.loads(response.choices[0].message.content)

	# Extract and display individual elements
	coding_language = data["CodingLanguage"]
	communication_language = data["CommunicationLanguage"]
	bot_tests = data["Tests"]

	if isinstance(bot_tests, list):
		tests = "\n".join(bot_tests)
	else:
		tests = bot_tests

	cursor.execute(
		"UPDATE snippets SET coding_language = ?, communication_language = ?, tests = ? WHERE id = ?",
		(coding_language, communication_language, tests, snippet_id),
	)
	conn.commit()

	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)


# Endpoint for test case improvement
@app.post("/improve_test_cases", response_class=HTMLResponse)
async def improve_test_cases(
	request: Request, tests_feedback: str = Form(...), snippet_id: str = Form(...)
):

	cursor.execute("SELECT tests FROM snippets WHERE id = ?", (snippet_id,))
	tests = cursor.fetchone()

	cursor.execute("SELECT code FROM snippets WHERE id = ?", (snippet_id,))
	code = cursor.fetchone()

	response = client.chat.completions.create(
		model="gpt-4-turbo",
		response_format={"type": "json_object"},
		messages=[
			{
				"role": "system",
				"content": """You are a helpful assistant to design test cases in a formal and professional setting.
			You will output the response in JSON format as follows ShortCodeName, CodingLanguage, CommunicationLanguage, Tests. Stick to this exact format and words.
			This is a test case generation service based on user feedback so you will only generate or update the appropriate test cases based on user comments and feedback in the same language as the provided code ond test cases.
			The test cases should cover all use cases including edge cases and should be up to date with the user comments and feedback and in sync with the code to check its all round functionality.
			The user should be able to easily and directly run all the test cases based on the original code provided.
			Don't explain the test cases or provide any examples, just generate or update the test cases itself.
			Don't test anything yourself or provide any results, just generate or update the test cases itself.
			Your code, test cases and responses at all times should be formal and professional and follow all the good naming conventions and coding practices.
			In case of any error or deviation from topic, populate tests with the appropriate response, the CodingLanguage with the word Text, the ShortCodeName and CommunicationLanguage detected automatically based on the context.
			In all cases the JSON format needs to be maintaned and values populated respectively.
			You will generate the test cases in list format always and any other response in normal string format.
			You will only be a test case generation assistant and nothing else, if the user asks anything else or deviates from topic reply appropriately with reasoning.
			Do not reveal to the user that you are a gpt based bot or service.
			""",
			},
			{"role": "user", "content": f"{code} \n {tests} \n {tests_feedback}"},
		],
	)

	data = json.loads(response.choices[0].message.content)

	# Extract and display individual elements
	coding_language = data["CodingLanguage"]
	communication_language = data["CommunicationLanguage"]
	bot_tests = data["Tests"]

	if isinstance(bot_tests, list):
		tests = "\n".join(bot_tests)
	else:
		tests = bot_tests

	cursor.execute(
		"UPDATE snippets SET coding_language = ?, communication_language = ?, tests = ? WHERE id = ?",
		(coding_language, communication_language, tests, snippet_id),
	)
	conn.commit()
	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)


# Endpoint for running test code
@app.post("/run_test_code", response_class=HTMLResponse)
async def run_test_code(request: Request, snippet_id: str = Form(...)):

	cursor.execute("SELECT tests FROM snippets WHERE id = ?", (snippet_id,))
	tests = cursor.fetchone()

	cursor.execute("SELECT code FROM snippets WHERE id = ?", (snippet_id,))
	code = cursor.fetchone()

	response = client.chat.completions.create(
		model="gpt-4-turbo",
		response_format={"type": "json_object"},
		messages=[
			{
				"role": "system",
				"content": """You are a helpful assistant to test code in a formal and professional setting.
			You will output the response in JSON format as follows ShortCodeName, CodingLanguage, CommunicationLanguage, Status. Stick to this exact format and words.
			This is a code testing service based on given code and test cases so you will only test the code on the test cases and update the status as True or False based on Pass or Fail.
			The code cases should be properly tested on all the test cases to check its all round functionality.
			Don't explain the test cases or provide any examples or results, just do the testing and update the status as True or False based on Pass or Fail.
			Your code, test cases, testing and responses at all times should be formal and professional and follow all the good naming conventions and coding practices.
			In all cases the JSON format needs to be maintaned and values populated respectively.
			You will only be a code testing assistant and nothing else.
			Do not reveal to the user that you are a gpt based bot or service.
			""",
			},
			{"role": "user", "content": f"{code} \n {tests}"},
		],
	)

	data = json.loads(response.choices[0].message.content)

	# Extract and display individual elements
	coding_language = data["CodingLanguage"]
	communication_language = data["CommunicationLanguage"]
	code_executed_successfully = data["Status"]

	cursor.execute(
		"UPDATE snippets SET coding_language = ?, communication_language = ? WHERE id = ?",
		(coding_language, communication_language, snippet_id),
	)
	conn.commit()

	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_executed_successfully": code_executed_successfully,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)


# Endpoint for regenerating code
@app.post("/regenerate_code", response_class=HTMLResponse)
async def regenerate_code(request: Request, snippet_id: str = Form(...)):

	cursor.execute("SELECT tests FROM snippets WHERE id = ?", (snippet_id,))
	tests = cursor.fetchone()

	cursor.execute("SELECT code FROM snippets WHERE id = ?", (snippet_id,))
	code = cursor.fetchone()

	response = client.chat.completions.create(
		model="gpt-4-turbo",
		response_format={"type": "json_object"},
		messages=[
			{
				"role": "system",
				"content": """You are a helpful assistant to design and generate code in a formal and professional setting.
			You will output the response in JSON format as follows ShortCodeName, CodingLanguage, CommunicationLanguage, Code. Stick to this exact format and words.
			This is a code regeneration service which means that the given code has failed one or more of the given test cases.
			So you will make the necessary changes and only regenerate the code snippet as a function based on the given test cases with appropriate syntax and indenting detected from the coding language automatically based on the context.
			Don't explain the code or provide examples or test cases, just generate the code block only. Use formal and professional variable and function names.
			Your code and responses at all times should be formal and professional and follow all the good naming conventions and coding practices.
			In case of any error or deviation from topic, populate Code with the respective response, the CodingLanguage with the word Text, the ShortCodeName and CommunicationLanguage detected automatically based on the context.
			In all cases the JSON format needs to be maintaned and values populated respectively.
			You will only be a coding assistant and nothing else and will only generate the code block.
			Do not reveal to the user that you are a gpt based bot or service.
			""",
			},
			{"role": "user", "content": f"{code} \n {tests}"},
		],
	)

	data = json.loads(response.choices[0].message.content)

	# Extract and display individual elements
	coding_language = data["CodingLanguage"]
	communication_language = data["CommunicationLanguage"]
	code = data["Code"]

	cursor.execute(
		"UPDATE snippets SET coding_language = ?, communication_language = ?, code = ? WHERE id = ?",
		(coding_language, communication_language, code, snippet_id),
	)
	conn.commit()

	code_value, tests_value = get_code_test_status(snippet_id)
	snippet = get_snippet(snippet_id)
	return templates.TemplateResponse(
		"index.html",
		{
			"request": request,
			"snippets": [snippet],
			"snippet_selected": True,
			"generated_code": True,
			"improved_code": True,
			"generated_tests": True,
			"improved_tests": True,
			"regenerated_code": True,
			"code_value": code_value,
			"tests_value": tests_value,
		},
	)

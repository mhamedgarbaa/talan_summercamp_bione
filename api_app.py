from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List
import uvicorn
from pprint import pprint
from rag.rag import app
from selenium.webdriver.edge.options import Options
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import os
import tempfile
from pydantic import BaseModel
import re
from langchain_nomic.embeddings import NomicEmbeddings
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os, shutil, tarfile, subprocess


# Initialize FastAPI app
api_app = FastAPI()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = "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"

local_directory = r"C:\Users\mhame\OneDrive\Bureau\TalanSummerCamp-main\chromaDb"

# Define request model
class QueryRequest(BaseModel):
    question: str

# Define response model
class QueryResponse(BaseModel):
    question: str
    generation: str

# Define your workflow application (as shown in your workflow)


#input JSON : { "question":"what is biology?" }
@api_app.post("/query", response_model=QueryResponse)
async def query_rag_model(request: QueryRequest):
    try:
        inputs = {"question": request.question}
        for output in app.stream(inputs):
            for key, value in output.items():
                pprint(f"Finished running: {key}:")
        response = value["generation"]  
        return QueryResponse(question=request.question, generation=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def preprocess_content(text):
    text = text.replace('\n', ' ')
    return text

#input body form-data pdf_file then upload
@api_app.post("/process_pdf")
async def process_pdf(pdf_file: UploadFile = File(...)):
    if not pdf_file:
        raise HTTPException(status_code=400, detail="No file part")
    
    if pdf_file.filename == '':
        raise HTTPException(status_code=400, detail="No selected file")

    # Save the file temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, pdf_file.filename)
    
    with open(temp_path, 'wb') as f:
        f.write(await pdf_file.read())

    try:
        # Load and process the PDF
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        # Apply preprocessing
        for doc in docs:
            doc.page_content = preprocess_content(doc.page_content)
        
        # Initialize text splitter
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=500, chunk_overlap=50
        )
        
        # Split documents into chunks
        doc_splits = text_splitter.split_documents(docs)

        # Clean up the temporary file
        os.remove(temp_path)
        
        return JSONResponse(content={"success": True, "message": "PDF processed successfully"})

    except Exception as e:
        os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))


# Function to preprocess content
def preprocess_content(text):
    text = re.sub(r"[\n\s]+", " ", text)
    text = re.sub(r"(?i)(Email|Subscribe|Privacy|Donate|Feedback).*?[\n]", "", text)
    text = re.sub(r"(?i)more information.*", "", text)
    return text

class DocumentRequest(BaseModel):
    urls: List[str]

#input 
@api_app.post("/process_urls")
async def process_documents(request: DocumentRequest):
    urls = request.urls
    if not urls:
        raise HTTPException(status_code=400, detail='No URLs provided')

    try:
        # Load and preprocess documents
        docs = [WebBaseLoader(url).load() for url in urls]
        docs_list = [item for sublist in docs for item in sublist]
        for doc in docs_list:
            doc.page_content = preprocess_content(doc.page_content)

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=500, chunk_overlap=50
        )
        doc_splits = text_splitter.split_documents(docs_list)

        # Add to vectorDB
        vectorstore = Chroma.from_documents(
            documents=doc_splits,
            collection_name="rag-chroma",
            embedding=NomicEmbeddings(model="nomic-embed-text-v1.5", inference_mode="local"),
            persist_directory=local_directory
        )
        return {"message": "Documents processed and stored successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

driver_path = r"C:\Users\mhame\Downloads\edgedriver_win64\msedgedriver.exe"

# Define download path
DOWNLOAD_PATH = os.path.join(os.getcwd(), "Download")

# Initialize Edge options
edge_options = Options()
edge_options.add_argument("--start-maximized")  # Optional: start Edge maximized

# Add download preferences to Edge options
edge_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_PATH,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# Define input model for FastAPI
class DNASequence(BaseModel):
    sequence: str


#input JSON : { "sequence":"AGTC" }
@api_app.post("/process_dna/")
def process_dna(dna: DNASequence):
    # Initialize the Service object
    service = Service(driver_path)

    # Create a new instance of the Edge driver using the Service object and options
    driver = webdriver.Edge(service=service, options=edge_options)

    # Go to the desired webpage
    driver.get("http://localhost:80")

    def dna_seq(seq):
        try:
            input_field = driver.find_element(By.NAME, "2.sequence")
            input_field.clear()  # Clear the input field if there's existing text
            input_field.send_keys(seq)  # Fill the input field with the DNA sequence
        finally:
            time.sleep(1)  # Adjust sleep time if necessary

    def click_submit_button():
        try:
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "NAcustombuild.xml"))
            )
            submit_button.click()  # Click the submit button
        finally:
            time.sleep(1)  # Adjust sleep time if necessary

    def download_result():
        try:
            download_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Download Job"))
            )
            download_link.click()  # Click the download link
        except Exception as e:
            driver.quit()
            raise HTTPException(status_code=500, detail=f"Error clicking download link: {e}")
        finally:
            time.sleep(1)  # Adjust sleep time if necessary

    def extract_and_rename_tgz_file(download_folder, new_folder_name):
        # List all files in the download folder
        files = os.listdir(download_folder)

        # Filter out non-tgz files
        tgz_files = [f for f in files if f.endswith('.tgz')]

        if len(tgz_files) != 1:
            raise Exception(f"Expected exactly one tgz file in {download_folder}, but found {len(tgz_files)}")

        tgz_file_path = os.path.join(download_folder, tgz_files[0])

        # Extract the tgz file
        with tarfile.open(tgz_file_path, 'r:gz') as tar_ref:
            tar_ref.extractall(download_folder)

        # Find the extracted folder (assuming it is the only new folder created)
        extracted_folders = [f for f in os.listdir(download_folder) if os.path.isdir(os.path.join(download_folder, f))]

        # Exclude the folder that already existed before extraction
        new_folders = list(set(extracted_folders) - set(files))

        if len(new_folders) != 1:
            raise Exception(f"Expected exactly one new folder in {download_folder} after extraction, but found {len(new_folders)}")

        extracted_folder_path = os.path.join(download_folder, new_folders[0])
        new_folder_path = os.path.join(download_folder, new_folder_name)

        # Rename the extracted folder
        os.rename(extracted_folder_path, new_folder_path)

        return new_folder_path

    try:
        # Clean the download directory before starting
        if os.path.exists(DOWNLOAD_PATH):
            shutil.rmtree(DOWNLOAD_PATH)
        os.makedirs(DOWNLOAD_PATH)

        # Execute functions
        dna_seq(dna.sequence)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        click_submit_button()
        time.sleep(1)  # Ensure the result is available
        download_result()

        # Wait until the file is downloaded
        time.sleep(10)  # Adjust this according to your needs

        # Find the downloaded file
        downloaded_files = os.listdir(DOWNLOAD_PATH)
        if not downloaded_files:
            raise HTTPException(status_code=500, detail="No file downloaded")
        downloaded_file_path = os.path.join(DOWNLOAD_PATH, downloaded_files[0])

        # Extract and rename the tgz file
        new_folder_path = extract_and_rename_tgz_file(DOWNLOAD_PATH, "extracted_dna")

        # Path to the specific file
        specific_file_path = os.path.join(new_folder_path, "jobnr8-PDBeditor", "dna1_fixed.pdb")
        if not os.path.exists(specific_file_path):
            raise HTTPException(status_code=500, detail="The file dna1_fixed.pdb was not found in the extracted folder")

    finally:
        # Close the browser
        driver.quit()

    return FileResponse(specific_file_path, filename="dna1_fixed.pdb")

driver_path = r"C:\Users\mhame\Downloads\edgedriver_win64\msedgedriver.exe"

# Define download path
DOWNLOAD_PATH = os.path.join(os.getcwd(), "Download")

# Initialize Edge options
edge_options = Options()
edge_options.add_argument("--start-maximized")  # Optional: start Edge maximized

# Add download preferences to Edge options
edge_options.add_experimental_option("prefs", {
    "download.default_directory": DOWNLOAD_PATH,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# Define input model for FastAPI
class DNASequence(BaseModel):
    sequence: str

#input JSON: { "sequence" : "AGCTAGCCCCTTT" }
@api_app.post("/process_dna/")
def process_dna(dna: DNASequence):
    # Initialize the Service object
    service = Service(driver_path)

    # Create a new instance of the Edge driver using the Service object and options
    driver = webdriver.Edge(service=service, options=edge_options)

    # Go to the desired webpage
    driver.get("http://localhost:80")

    def dna_seq(seq):
        try:
            input_field = driver.find_element(By.NAME, "2.sequence")
            input_field.clear()  # Clear the input field if there's existing text
            input_field.send_keys(seq)  # Fill the input field with the DNA sequence
        finally:
            time.sleep(1)  # Adjust sleep time if necessary

    def click_submit_button():
        try:
            submit_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "NAcustombuild.xml"))
            )
            submit_button.click()  # Click the submit button
        finally:
            time.sleep(1)  # Adjust sleep time if necessary

    def download_result():
        try:
            download_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Download Job"))
            )
            download_link.click()  # Click the download link
        except Exception as e:
            driver.quit()
            raise HTTPException(status_code=500, detail=f"Error clicking download link: {e}")
        finally:
            time.sleep(1)  # Adjust sleep time if necessary

    def extract_and_rename_tgz_file(download_folder, new_folder_name):
        # List all files in the download folder
        files = os.listdir(download_folder)

        # Filter out non-tgz files
        tgz_files = [f for f in files if f.endswith('.tgz')]

        if len(tgz_files) != 1:
            raise Exception(f"Expected exactly one tgz file in {download_folder}, but found {len(tgz_files)}")

        tgz_file_path = os.path.join(download_folder, tgz_files[0])

        # Extract the tgz file
        with tarfile.open(tgz_file_path, 'r:gz') as tar_ref:
            tar_ref.extractall(download_folder)

        # Find the extracted folder (assuming it is the only new folder created)
        extracted_folders = [f for f in os.listdir(download_folder) if os.path.isdir(os.path.join(download_folder, f))]

        # Exclude the folder that already existed before extraction
        new_folders = list(set(extracted_folders) - set(files))

        if len(new_folders) != 1:
            raise Exception(f"Expected exactly one new folder in {download_folder} after extraction, but found {len(new_folders)}")

        extracted_folder_path = os.path.join(download_folder, new_folders[0])
        new_folder_path = os.path.join(download_folder, new_folder_name)

        # Rename the extracted folder
        os.rename(extracted_folder_path, new_folder_path)

        return new_folder_path

    try:
        # Clean the download directory before starting
        if os.path.exists(DOWNLOAD_PATH):
            shutil.rmtree(DOWNLOAD_PATH)
        os.makedirs(DOWNLOAD_PATH)

        # Execute functions
        dna_seq(dna.sequence)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        click_submit_button()
        time.sleep(1)  # Ensure the result is available
        download_result()

        # Wait until the file is downloaded
        time.sleep(10)  # Adjust this according to your needs

        # Find the downloaded file
        downloaded_files = os.listdir(DOWNLOAD_PATH)
        if not downloaded_files:
            raise HTTPException(status_code=500, detail="No file downloaded")
        downloaded_file_path = os.path.join(DOWNLOAD_PATH, downloaded_files[0])

        # Extract and rename the tgz file
        new_folder_path = extract_and_rename_tgz_file(DOWNLOAD_PATH, "extracted_dna")

        # Path to the specific file
        specific_file_path = os.path.join(new_folder_path, "jobnr8-PDBeditor", "dna1_fixed.pdb")
        if not os.path.exists(specific_file_path):
            raise HTTPException(status_code=500, detail="The file dna1_fixed.pdb was not found in the extracted folder")

    finally:
        # Close the browser
        driver.quit()

    return FileResponse(specific_file_path, filename="dna1_fixed.pdb")

class SequenceData(BaseModel):
    sequence: str


#input : { "sequence" : "GENGEIPLEIRATTGAEVDTRAVTAVEMTEGTLGIFRLPEEDYTALENFRYNRVAGENWKPASTVIYVGGTYARLCAYAPYNSVEFKNSSLKTEAGLTMQTYAAEKDMRFAVSGGDEVWKKTPTANFELKRAYARLVLSVVRDATYPNTCKITKAKIEAFTGNIITANTVDISTGTEGSGTQTPQYIHTVTTGLKDGFAIGLPQQTFSGGVVLTLTVDGMEYSVTIPANKLSTFVRGTKYIVSLAVKGGKLTLMSDKILIDKDWAEVQTGTGGSGDDYDTSFN" }
@api_app.post("/esm")
async def fold_sequence(data: SequenceData):
    # Define the curl command
    curl_command = [
        'curl', '-X', 'POST',
        '--data', data.sequence,
        'https://api.esmatlas.com/foldSequence/v1/pdb/'
    ]

    # Run the command and save the output to a file
    try:
        result = subprocess.run(curl_command, capture_output=True, text=True, check=True)
        
        # Define the file path
        file_path = "result.pdb"
        
        # Save the result to a file
        with open(file_path, "w") as file:
            file.write(result.stdout)
        
        return {"message": "File saved successfully", "file_path": file_path}
    
    except subprocess.CalledProcessError as e:
        # Handle errors
        raise HTTPException(status_code=500, detail=f"Error occurred: {e.stderr}")


# Main function to run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api_app, host="localhost", port=8000)
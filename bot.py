import logging
import requests
import json
import os
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import re
from requests.exceptions import ConnectionError, Timeout, RequestException

# Load environment variables from .env file
load_dotenv()

# Get API keys and tokens from environment variables
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# OpenAI API Client
client = OpenAI(api_key=OPENAI_API_KEY)

# Define states for the conversation
ADDING_RECEIPT, MORE_RECEIPTS = range(2)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize a global list to store receipt data
receipt_data = []

# Start command
def start(update, context):
    logger.info("Bot started by user.")
    update.message.reply_text('Welcome to the Receipt Processing Bot!\n\n'
                              'Please send me a picture of your receipt, and I will help you process it.')
    return ADDING_RECEIPT

# Handle image sent by user
def handle_image(update, context):
    try:
        photo = update.message.photo[-1].get_file()
        photo.download('receipt.jpg')
        logger.info("Image received and downloaded successfully.")
        
        # Extract full text from the receipt using OCR.space
        extracted_text = extract_text_with_retry('receipt.jpg')

        # Log the extracted text
        logger.info(f"Extracted Text: {extracted_text}")

        # If no text is extracted, notify the user
        if not extracted_text:
            update.message.reply_text("No text was extracted from the image. Please try again.")
            logger.info("No text extracted from the image.")
            return ConversationHandler.END

        # Send full extracted text to OpenAI to interpret the receipt and extract key information
        processed_data = ask_openai_to_analyze_receipt(extracted_text)

        # Log the response from OpenAI
        logger.info(f"OpenAI Processed Data: {processed_data}")

        # If no data was extracted, notify the user
        if not processed_data:
            update.message.reply_text("OpenAI could not extract the requested information. Please try again.")
            logger.info("OpenAI could not extract information.")
            return ConversationHandler.END

        # Generate the order number
        order_number = len(receipt_data) + 1

        # Add the extracted data to the global list
        receipt_data.append({
            "Name": f"Order {order_number}",
            "Product Purchased": processed_data.get("products", ""),
            "Store Name": processed_data.get("store_name", ""),
            "Price": processed_data.get("total_cost", "")
        })

        update.message.reply_text("Receipt data has been extracted. Do you have another receipt to process? (yes/no)")
        logger.info(f"Receipt data extracted for Order {order_number}.")
        return MORE_RECEIPTS

    except Exception as e:
        logger.error(f"Error handling image: {e}")
        update.message.reply_text("An error occurred while processing the image. Please try again.")
        return ConversationHandler.END

# Use OCR.space API to extract full text from the image with retry mechanism
def extract_text_with_retry(image_path, retries=3, delay=5, timeout_duration=30):
    for attempt in range(retries):
        try:
            with open(image_path, 'rb') as image_file:
                response = requests.post(
                    'https://api.ocr.space/parse/image',
                    files={image_path: image_file},
                    data={'apikey': OCR_SPACE_API_KEY, 'language': 'eng'},
                    timeout=timeout_duration  # Set custom timeout
                )
            response.raise_for_status()  # Check if the request was successful
            result = response.json()

            # Log the entire OCR result
            logger.info(f"OCR API Raw Response: {result}")

            # Check if 'ParsedResults' exists and is non-empty
            if 'ParsedResults' in result and len(result['ParsedResults']) > 0:
                return result['ParsedResults'][0].get('ParsedText', '')
            else:
                logger.warning("No ParsedResults found in OCR response.")
                return ''

        except requests.exceptions.Timeout:
            logger.error(f"Request timed out. Retrying in {delay} seconds... (Attempt {attempt+1}/{retries})")
            time.sleep(delay)
        except ConnectionError:
            logger.error(f"Connection error, retrying in {delay} seconds... (Attempt {attempt+1}/{retries})")
            time.sleep(delay)
        except Timeout:
            logger.error(f"Request timeout, retrying in {delay} seconds... (Attempt {attempt+1}/{retries})")
            time.sleep(delay)
        except RequestException as e:
            logger.error(f"Error: {e}")
            break
    return None

# Use OpenAI to analyze the extracted full text from the receipt
def ask_openai_to_analyze_receipt(extracted_text, timeout_duration=30):
    prompt = f"Here is the full text of a receipt: \n\n'{extracted_text}'\n\n" \
             "Please analyze this receipt and return the following information in JSON format: " \
             "store_name (name of the store), products (list of purchased products), and total_cost (total price)."

    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            timeout=timeout_duration  # Set custom timeout
        )

        # Strip backticks and the "json" code block if it exists
        response_content = completion.choices[0].message.content
        stripped_response = re.sub(r'```json|```', '', response_content).strip()

        # Try parsing the cleaned response as JSON
        try:
            return json.loads(stripped_response)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return {}  # Return an empty dict in case of an error

    except requests.exceptions.Timeout:
        logger.error(f"OpenAI request timed out.")
        return {}

    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return {}
    
# Create the final Excel file with all receipt data
def create_final_excel(receipts):
    # Create a list of dictionaries, each representing one row in the Excel file
    rows = []
    
    for index, receipt in enumerate(receipts):
        store_name = receipt.get("Store Name", "")
        order_number = f"{index + 1:06d}"  # Generates a 6-digit number, e.g., 000001, 000002
        total_cost = receipt.get("Price", "")
        products = receipt.get("Product Purchased", [])
        
        # Ensure that 'products' is a list; if it's not, treat it as a single product
        if isinstance(products, list):
            for product in products:
                if isinstance(product, dict):
                    rows.append({
                        "Order Number": order_number,
                        "Store Name": store_name,
                        "Product Name": product.get("name", ""),
                        "Price": product.get("price", ""),
                        "Total Cost": total_cost  # Optional if you want the total in each row
                    })
                else:
                    # If the product is not a dictionary, treat it as a single product string
                    rows.append({
                        "Order Number": order_number,
                        "Store Name": store_name,
                        "Product Name": product,
                        "Price": "",  # No price in this case
                        "Total Cost": total_cost
                    })
        else:
            # Handle the case where 'products' is not a list (e.g., just a string)
            rows.append({
                "Order Number": order_number,
                "Store Name": store_name,
                "Product Name": products,
                "Price": "",  # No price in this case
                "Total Cost": total_cost
            })
    
    # Convert the rows into a DataFrame and write to an Excel file
    df = pd.DataFrame(rows)
    df.to_excel("final_receipts.xlsx", index=False)

# Ask the user if they want to process more receipts
def more_receipts(update, context):
    user_input = update.message.text.lower()
    
    if user_input == 'yes':
        update.message.reply_text("Please send the next receipt.")
        return ADDING_RECEIPT
    elif user_input == 'no':
        # Compile all data into a single Excel file and send to the user
        create_final_excel(receipt_data)
        update.message.reply_document(open('final_receipts.xlsx', 'rb'))
        update.message.reply_text("Here is your final Excel file with all receipt data.")
        logger.info("Final Excel file sent to the user.")
        return ConversationHandler.END
    else:
        update.message.reply_text("Please respond with 'yes' or 'no'.")
        return MORE_RECEIPTS

# Cancel the conversation
def cancel(update, context):
    update.message.reply_text("Process canceled. You can start again by sending a receipt.")
    return ConversationHandler.END

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ADDING_RECEIPT: [MessageHandler(Filters.photo, handle_image)],
            MORE_RECEIPTS: [MessageHandler(Filters.text, more_receipts)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

# Receipt Processing Telegram Bot

This is a Python-based Telegram bot that allows users to send pictures of receipts. The bot uses OCR (Optical Character Recognition) to extract the text from the receipt and processes it using OpenAI's GPT-3.5 model to identify the store name, products, and prices. The final output is compiled into an Excel file, which is sent back to the user after processing multiple receipts.

## Features

- **Receipt Image Upload**: Users can send pictures of receipts, and the bot extracts the relevant information.
- **OCR Integration**: Uses the OCR.space API to extract text from the images.
- **OpenAI Integration**: Sends the extracted text to OpenAI GPT-3.5 for analysis and structuring of the data.
- **Excel File Generation**: After processing multiple receipts, the bot generates an Excel file containing the store name, product names, and prices.
- **Multiple Receipt Handling**: Users can send multiple receipts, and all data will be compiled into one Excel file.

---

## Requirements

- Python 3.8+
- `python-telegram-bot==13.15`
- `requests==2.28.1`
- `pandas==1.5.0`
- `openpyxl==3.0.10`
- `openai==0.27.0`
- `python-dotenv==0.21.0`

### Installation Instructions

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/receipt-bot.git
   cd receipt-bot

2. **Set up Python Virtual Environment:**
    '''bash
    python -m venv venv
    source venv/Scripts/activate  # On Windows
    # OR
    source venv/bin/activate      # On Linux/Mac

3. **Install the required dependencies:**
    '''bash
    pip install -r requirements.txt

4. **Set up the environment variables:**
- Create a .env file in the root directory of your project with the following contents: 
    '''bash 
    TELEGRAM_BOT_TOKEN=your-telegram-bot-token
    OCR_SPACE_API_KEY=your-ocr-space-api-key
    OPENAI_API_KEY=your-openai-api-key
- Replace your-telegram-bot-token, your-ocr-space-api-key, and your-openai-api-key with the actual API keys and tokens from the respective services.

5. **Run the bot:** 
    '''bash
    python bot.py

6. **Interacting with the bot**:
   - Send the `/start` command to begin interacting with the bot.
   - Upload a picture of your receipt.
   - After the bot processes the image, you can choose whether to upload another receipt or receive the final Excel file.
   - Once all receipts are processed, the bot will compile the information into a downloadable Excel file and send it to you.

## How It Works

1. **User Uploads Receipt**:
   - After the user sends a picture of a receipt, the bot downloads the image and uses OCR.space API to extract the text from it.

2. **Text Sent to OpenAI**:
   - The extracted text is sent to OpenAI's GPT-3.5 to parse the receipt, identifying the store name, product names, and prices.

3. **Excel File Creation**:
   - The bot compiles the extracted data into an Excel file with the following columns: `Order Number`, `Store Name`, `Product Name`, and `Price`.

4. **Multiple Receipts**:
   - The bot allows the user to process multiple receipts, which are all compiled into a single Excel file that the user can download.

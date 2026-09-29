# C-Test Creator Bot

A Telegram bot for creating and practicing C-Tests. The bot can convert user-provided texts into C-Tests or generate new texts according to the user's language level and preferences.

## Contents

* [Usage](#usage)
* [Functionality](#functionality)
* [Technical Details](#technical-details)

## Usage

To try the project in action, open the Telegram bot:@cTest_creator_bot

The bot provides two main functions:

* **Text to C-Test** – convert your own text into a C-Test.
* **Generate** – generate a new text and automatically convert it into a C-Test.

## Functionality

A C-Test is a language assessment format in which a text is modified by removing the second half of every second word, except for very short words. The test taker has to reconstruct the missing parts using the context of the text, grammar, and vocabulary.

### Text to C-Test

The bot accepts a text from the user and automatically transforms it into a C-Test.

The transformation is performed locally by the bot. The text is tokenized, and every second eligible word is shortened by removing its second half and replacing it with a placeholder.

The bot can also display the original text with the missing parts highlighted, allowing the user to check their answers.

### Text Generation

The bot can generate a new text using the OpenAI API and AsyncOpenAI library. The user specifies:

* target language
* level from A1 to C2
* additional preferences for the text

The generated text is then automatically converted into a C-Test. The C-Test conversion itself does not require an external AI model. The original text can be requested afterwards to check the answers.

### Interface Localization

The bot interface is available in four languages: English, German, Russian, Farsi.

The interface translations are stored separately and selected according to the user's language setting.

### User Accounts and Subscriptions

The bot stores user information and usage limits in a SQLite database. It supports free usage limits, paid subscriptions, and an administrator-controlled VIP status.

## Technical Details

### Database

User data and usage limits are stored in a SQLite database. The database contains information such as the user's Telegram ID, language, registration date, subscription status, remaining C-Test conversions, and remaining text generations.

### Deployment

The bot is currently deployed on a VPS running Ubuntu. Configuration such as the Telegram bot token, OpenAI API key, database path, and administrator password is provided through environment variables loaded from a .env file.

# AWS-Cloud-Dining-Concierge-Chatbot

AWS Cloud Dining Concierge Chatbot is a fully serverless, microservice-driven web application designed to provide personalized restaurant suggestions based on user preferences. The system leverages multiple AWS services such as **Lex**, **Lambda**, **SQS**, **DynamoDB**, **ElasticSearch**, **SES**, and **API Gateway** to deliver scalable, event-driven, and automated functionality.

You can interact with the live chatbot here:  
👉 [**Dining Concierge Chatbot (Hosted on S3)**](https://diningconciergechatbot2025.s3.us-east-1.amazonaws.com/index.html)

---

## About

The Dining Concierge Chatbot interacts with users to gather their dining preferences — including **location**, **cuisine type**, **dining time**, **party size**, and **email address** — and then returns curated restaurant suggestions via email.  

The application integrates **Amazon Lex** for conversational interaction, **Yelp API** for restaurant data collection, and a pipeline of AWS services to process and deliver restaurant recommendations.

---


## Architecture Overview

The system follows a **serverless architecture** using the following key components:

1. **Frontend (S3):**
   - A static web application hosted on **Amazon S3**, built from a starter React app.
   - Interfaces with the backend API to send user messages and display chatbot responses.

2. **API Gateway (LF0):**
   - Acts as the REST API layer for the frontend to communicate with the backend.
   - Routes incoming chat messages to the Lambda function that interacts with the Lex chatbot.

3. **Amazon Lex Chatbot:**
   - Handles natural language understanding with three trained intents:
     - **GreetingIntent:** Responds to greetings (e.g., “Hello” → “Hi there, how can I help?”)
     - **ThankYouIntent:** Acknowledges gratitude (e.g., “Thanks” → “You’re welcome”)
     - **DiningSuggestionsIntent:** Collects user preferences and initiates restaurant search workflow.

4. **Lambda Functions:**
   - **LF0:** Manages API requests and responses between the frontend and Lex.
   - **LF1:** Lex code hook to process intents, validate inputs, and push dining requests into an **SQS Queue (Q1)**.
   - **LF2:** A queue worker triggered periodically by **CloudWatch Events**, fetching messages from SQS, querying **ElasticSearch** and **DynamoDB**, and sending formatted restaurant suggestions via **SES** email.

5. **Data Storage:**
   - **DynamoDB:** Stores 1,200+ restaurant entries scraped using the Yelp API, including metadata like business ID, name, address, coordinates, ratings, and timestamps.
   - **ElasticSearch:** Maintains indexed records of restaurant cuisines for fast random selection and querying.

6. **Notifications:**
   - **SES (Simple Email Service):** Sends formatted restaurant recommendations directly to users via email.

---

## Data Flow Summary

1. **User Input:** User interacts with the chatbot through the web interface.  
2. **Lex Processing:** Lex identifies the intent and triggers the appropriate Lambda function.  
3. **Queue Storage:** The request is pushed into **Amazon SQS**.  
4. **Recommendation Retrieval:** Worker Lambda (**LF2**) pulls messages, queries **ElasticSearch** for random cuisine matches, and fetches full restaurant details from **DynamoDB**.  
5. **Email Notification:** The system composes and sends restaurant suggestions using **SES**.

---

## AWS Services Used

- **Amazon Lex** – Conversational interface  
- **AWS Lambda** – Serverless compute functions (LF0, LF1, LF2)  
- **Amazon SQS** – Message queue for decoupled processing  
- **Amazon DynamoDB** – NoSQL storage for restaurant data  
- **Amazon ElasticSearch Service (OpenSearch)** – Fast restaurant ID lookup by cuisine  
- **Amazon SES** – Email delivery service  
- **Amazon API Gateway** – REST API management  
- **Amazon S3** – Static website hosting  
- **Amazon CloudWatch / EventBridge** – Scheduled triggers for Lambda  


## Example Conversation

**User:** Hello  
**Bot:** Hi there, how can I help?  
**User:** I need some restaurant suggestions.  
**Bot:** Great! What city or area are you looking to dine in?  
**User:** Manhattan  
**Bot:** Got it! What cuisine would you like to try?  
**User:** Indian  
**Bot:** How many people are in your party?  
**User:** Two  
**Bot:** What time would you like to dine?  
**User:** 7 pm  
**Bot:** Great! Please share your email.  
**User:** user@example.com  
**Bot:** You’re all set! Expect my suggestions shortly.  

**(Email arrives later via SES)**  
> “Hello! Here are my Indian restaurant suggestions for 2 people today at 7 pm:  
> 1. Bombay Chowk, located at 1378 1st Ave, New York, NY 10021
> 2. Rowdy Rooster, located at 149 1st Ave, New York, NY 10003  
> 3. Saravanaa Bhavan, located at 413 Amsterdam Ave, New York, NY 10024
> Enjoy your meal!”

---

## Credits

Developed as part of **Cloud Computing and Big Data – Fall 2024** at **New York University**.

---

## Architecture Diagram

```plaintext
[Frontend: S3 + React]
          │
          ▼
 [API Gateway] ───▶ [Lambda LF0]
          │
          ▼
       [Lex Chatbot]
          │
          ▼
       [Lambda LF1]
          │
          ▼
        [SQS Queue]
          │
          ▼
       [Lambda LF2]
          ├──▶ [ElasticSearch]
          ├──▶ [DynamoDB]
          └──▶ [SES Email Delivery]

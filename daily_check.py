import feedparser
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime
from groq import Groq

# 1. CONFIGURATION
rss_url = "https://news.google.com/rss/search?q=(Boston+OR+DC)+AND+(airport+OR+flight+OR+storm+OR+FAA)+when:1d&hl=en-US&gl=US&ceid=US:en"

def get_groq_summary(news_items):
    """
    Sends the list of news to Groq to get a human-readable summary.
    """
    try:
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )

        # Prepare the list of news for the AI
        news_text = "\n".join(news_items)
        
        prompt = f"""
        You are a flight tracking assistant. 
        Analyze the following news headlines and links regarding Boston (BOS) and Washington DC (DCA/IAD) flights. Highlight if the news articles are confident, or in a wait-and-see mode, with regard to whether delays will happen.
        
        NEWS DATA:
        {news_text}
        
        INSTRUCTIONS:
        1. Summarize any potential disruptions (storms, strikes, FAA outages).
        2. Be specific about which city is affected.
        3. Precise whether it is confirmed delays and disruptions, or only potential issues.
        4. Keep it short (under 500 words).
        5. Format it as a clean briefing.
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama-4-maverick-17b-128e-instruct", # Fast and efficient model
        )

        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Error getting summary from Groq: {e}")
        return "Could not generate summary. Here is the raw data:\n" + "\n".join(news_items)

def send_email(subject, body):
    sender = os.environ['EMAIL_USER']
    password = os.environ['EMAIL_PASSWORD']
    receiver = os.environ['EMAIL_TO']

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

def check_news():
    print("Fetching news...")
    feed = feedparser.parse(rss_url)
    
    hits = []
    keywords = ["delay", "cancel", "flights","ground stop", "storm", "snow", "outage", "FAA"]
    
    for entry in feed.entries:
        title = entry.title.lower()
        if any(word in title for word in keywords):
            # Limit to 15 items to avoid hitting token limits
            if len(hits) < 15:
                hits.append(f"- {entry.title} ({entry.link})")

    if hits:
        print(f"Found {len(hits)} articles. Asking Groq to summarize...")
        
        # Call Groq API
        summary = get_groq_summary(hits)
        
        today = datetime.now().strftime("%Y-%m-%d")
        email_body = f"Flight Intelligence Report for {today}:\n\n{summary}\n\n---\n(Source Data: {len(hits)} articles processed)"
        
        send_email(f"✈️ Flight Briefing: {today}", email_body)
    else:
        print("No significant issues found today.")

if __name__ == "__main__":
    check_news()

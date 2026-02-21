import streamlit as st
import re
import emoji
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from googleapiclient.discovery import build 
import smtplib
from PIL import Image
# Install dependencies
nltk.download('vader_lexicon')


def generate_ai_insight(positive_percent, negative_percent, neutral_percent, total_comments):

    insight = ""

    if positive_percent >= 70:

        insight += "🎉 Excellent response! Most viewers loved this video.\n\n"

    elif positive_percent >= 50:

        insight += "🙂 Good response. Audience sentiment is mostly positive.\n\n"

    elif negative_percent >= 50:

        insight += "⚠️ The video received strong negative feedback.\n\n"

    else:

        insight += "😐 The video received mixed reactions.\n\n"


    if total_comments >= 500:

        insight += "🔥 Very High Engagement: This video is attracting strong audience attention."

    elif total_comments >= 200:

        insight += "📈 Good Engagement: Audience interaction is good."

    else:

        insight += "📊 Low Engagement: Audience interaction is limited."


    if neutral_percent >= 40:

        insight += "\n\n💡 Many viewers are neutral, indicating average emotional impact."


    if negative_percent > positive_percent:

        insight += "\n\n🎯 Recommendation: Improve content quality, audio, or presentation."


    return insight


# Function to fetch comments from YouTube
def fetch_comments(video_id, uploader_channel_id, youtube):
    comments = []
    nextPageToken = None
    while len(comments) < 600:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,  # You can fetch up to 100 comments per request
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            # Check if the comment is not from the video uploader
            if comment['authorChannelId']['value'] != uploader_channel_id:
                comments.append(comment['textDisplay'])
        nextPageToken = response.get('nextPageToken')

        if not nextPageToken:
            break

    return comments

# Function to analyze sentiment
def sentiment_scores(comment, polarity):
    # Creating a SentimentIntensityAnalyzer object
    sentiment_object = SentimentIntensityAnalyzer()

    sentiment_dict = sentiment_object.polarity_scores(comment)
    polarity.append(sentiment_dict['compound'])

    return polarity

# Function to process comments and analyze sentiment
def process_comments(video_url):
    api_key = 'AIzaSyCrXfmjr5keE6Lg0MuZD_KTfs0b_ptMKTk'
    youtube = build('youtube', 'v3', developerKey=api_key)

    video_id_match = re.search(
        r'(?:youtu\.be\/|youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=))([^"&?\/\s]{11})',
        video_url)
    if video_id_match:
        video_id = video_id_match.group(1)

        video_response = youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()

        if 'items' in video_response and video_response['items']:
            video_snippet = video_response['items'][0]['snippet']
            uploader_channel_id = video_snippet['channelId']

            comments = fetch_comments(video_id, uploader_channel_id, youtube)

            # Process comments
            relevant_comments = []
            hyperlink_pattern = re.compile(
                r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            threshold_ratio = 0.65

            for comment_text in comments:
                comment_text = comment_text.lower().strip()

                emojis = emoji.emoji_count(comment_text)

                text_characters = len(re.sub(r'\s', '', comment_text))

                if (any(char.isalnum() for char in comment_text)) and not hyperlink_pattern.search(
                        comment_text):
                    if emojis == 0 or (text_characters / (text_characters + emojis)) > threshold_ratio:
                        relevant_comments.append(comment_text)

            # Analyze sentiment
            polarity = []
            positive_comments = []
            negative_comments = []
            neutral_comments = []

            for comment in relevant_comments:
                polarity = sentiment_scores(comment, polarity)

                if polarity[-1] > 0.05:
                    positive_comments.append(comment)
                elif polarity[-1] < -0.05:
                    negative_comments.append(comment)
                else:
                    neutral_comments.append(comment)

                if len(polarity) > 0:
                    avg_polarity = sum(polarity) / len(polarity)
                else:
                    avg_polarity = 0
            # Calculate percentages
            total_comments = len(positive_comments) + len(negative_comments) + len(neutral_comments)
            positive_percent = (len(positive_comments) / total_comments * 100) if total_comments > 0 else 0
            negative_percent = (len(negative_comments) / total_comments * 100) if total_comments > 0 else 0
            neutral_percent = (len(neutral_comments) / total_comments) * 100

            return positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent
        else:
            return None
    else:
        return None



# Add a menu for navigation
menu = ['Home', 'Dashboard', 'Comment Explorer', 'Compare Videos', 'Download Report', 'About', 'Contact']
choice = st.sidebar.selectbox('Menu', menu)

if choice == 'Home':
    st.title('Welcome to YouTube Comment Sentiment Analysis')
    st.subheader('Enter a YouTube Video URL to analyze comments:')
    video_url = st.text_input('Video URL:')
    if st.button('Analyze'):
        if video_url:
            positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent = process_comments(video_url)

            if positive_comments is not None:
                st.write(f'Average Polarity: {avg_polarity}')

                # Display positive, negative, and neutral comments with percentages
                st.write(f'Positive Comments: {len(positive_comments)} ({positive_percent:.2f}%)')
                st.write(f'Negative Comments: {len(negative_comments)} ({negative_percent:.2f}%)')
                st.write(f'Neutral Comments: {len(neutral_comments)} ({neutral_percent:.2f}%)')

                # Display positive comments in a table
                st.markdown('<h2 style="color: green;">Positive Comments</h2>', unsafe_allow_html=True)
                st.table(positive_comments)

                # Display negative comments in a table
                st.markdown('<h2 style="color: red;">Negative Comments</h2>', unsafe_allow_html=True)
                st.table(negative_comments)

                # Display neutral comments in a table
                st.markdown('<h2 style="color: grey;">Neutral Comments</h2>', unsafe_allow_html=True)
                st.table(neutral_comments)

                # Plotting sentiment distribution
                import matplotlib.pyplot as plt

                labels = ['Positive', 'Negative', 'Neutral']
                comment_counts = [len(positive_comments), len(negative_comments), len(neutral_comments)]

                fig, ax = plt.subplots()
                bars = ax.bar(labels, comment_counts, color=['green', 'red', 'yellow'])
                ax.set_xlabel('Sentiment')
                ax.set_ylabel('Comment Count')
                ax.set_title('Sentiment Analysis of Comments')

                # Add numbers inside bars
                for bar, count in zip(bars, comment_counts):
                    yval = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width() / 2, yval, count, va='bottom', ha='center')

                st.pyplot(fig)


            else:
                st.write('No comments found or error processing comments.')
        else:
            st.write('Please enter a valid YouTube Video URL.')

        


elif choice == 'Dashboard':

    st.title("📊 YouTube Sentiment Dashboard")

    st.write("Analyze YouTube video comments with advanced dashboard view")

    video_url = st.text_input("Enter YouTube Video URL")

    if st.button("Generate Dashboard"):

        if video_url:

            result = process_comments(video_url)

            if result is not None:

                positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent = result

                total_comments = len(positive_comments) + len(negative_comments) + len(neutral_comments)

                st.markdown("## 📈 Overview")

                col1, col2, col3, col4 = st.columns(4)

                col1.metric("Total Comments", total_comments)

                col2.metric("Positive 😊", f"{positive_percent:.2f}%")

                col3.metric("Negative 😡", f"{negative_percent:.2f}%")

                col4.metric("Neutral 😐", f"{neutral_percent:.2f}%")

                st.markdown("---")


                # PIE CHART

                st.subheader("🥧 Sentiment Distribution")

                import matplotlib.pyplot as plt

                labels = ['Positive', 'Negative', 'Neutral']

                sizes = [positive_percent, negative_percent, neutral_percent]

                fig1, ax1 = plt.subplots()

                ax1.pie(sizes, labels=labels, autopct='%1.1f%%')

                ax1.axis('equal')

                st.pyplot(fig1)


                # BAR CHART

                st.subheader("📊 Comment Count")

                counts = [len(positive_comments), len(negative_comments), len(neutral_comments)]

                fig2, ax2 = plt.subplots()

                bars = ax2.bar(labels, counts)

                ax2.set_xlabel("Sentiment")

                ax2.set_ylabel("Number of Comments")

                ax2.set_title("Sentiment Count")


                for bar in bars:

                    height = bar.get_height()

                    ax2.text(bar.get_x() + bar.get_width()/2,

                             height,

                             int(height),

                             ha='center',

                             va='bottom')


                st.pyplot(fig2)


                # INSIGHT

                # AI INSIGHT

                st.subheader("🧠 AI Insight")

                insight = generate_ai_insight(

                    positive_percent,
                    negative_percent,
                    neutral_percent,
                    total_comments

                )

                st.info(insight)


                # SAMPLE COMMENTS

                st.subheader("💬 Sample Positive Comments")

                st.write(positive_comments[:5])


                st.subheader("💬 Sample Negative Comments")

                st.write(negative_comments[:5])


            else:

                st.error("Error processing video")

        else:

            st.warning("Please enter YouTube URL")

elif choice == 'Comment Explorer':

    st.title("🔎 Comment Explorer")

    st.write("Search and filter YouTube comments")

    video_url = st.text_input("Enter YouTube Video URL")

    # Load comments button
    if st.button("Load Comments"):

        result = process_comments(video_url)

        if result:

            positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent = result

            # Save in session state
            st.session_state.all_comments = []

            for c in positive_comments:
                st.session_state.all_comments.append(("Positive", c))

            for c in negative_comments:
                st.session_state.all_comments.append(("Negative", c))

            for c in neutral_comments:
                st.session_state.all_comments.append(("Neutral", c))

        else:
            st.error("Error loading comments")


    # Only show filter if comments loaded
    if "all_comments" in st.session_state:


        # FILTER
        filter_option = st.selectbox(

            "Filter by Sentiment",

            ["All", "Positive", "Negative", "Neutral"]

        )


        # SEARCH
        search = st.text_input("Search Comments")


        # APPLY FILTER
        filtered_comments = []

        for sentiment, comment in st.session_state.all_comments:


            sentiment_match = (filter_option == "All" or sentiment == filter_option)

            search_match = (search.lower() in comment.lower()) if search else True


            if sentiment_match and search_match:

                filtered_comments.append((sentiment, comment))


        # SHOW COUNT
        st.write(f"Total Results: {len(filtered_comments)}")


        # DISPLAY COMMENTS
        for sentiment, comment in filtered_comments:

            if sentiment == "Positive":
                st.success(comment)

            elif sentiment == "Negative":
                st.error(comment)

            else:
                st.warning(comment)

elif choice == 'Compare Videos':

    st.title("⚔ Compare Two YouTube Videos")

    st.write("Compare audience sentiment between two videos")

    col1, col2 = st.columns(2)

    with col1:
        video_url1 = st.text_input("Enter First Video URL")

    with col2:
        video_url2 = st.text_input("Enter Second Video URL")


    if st.button("Compare Now"):


        result1 = process_comments(video_url1)
        result2 = process_comments(video_url2)


        if result1 and result2:


            pos1, neg1, neu1, avg1, pos_per1, neg_per1, neu_per1 = result1
            pos2, neg2, neu2, avg2, pos_per2, neg_per2, neu_per2 = result2


            total1 = len(pos1) + len(neg1) + len(neu1)
            total2 = len(pos2) + len(neg2) + len(neu2)


            st.markdown("## 📊 Comparison Overview")


            col1, col2 = st.columns(2)


            with col1:

                st.subheader("Video 1")

                st.metric("Total Comments", total1)
                st.metric("Positive %", f"{pos_per1:.2f}%")
                st.metric("Negative %", f"{neg_per1:.2f}%")


            with col2:

                st.subheader("Video 2")

                st.metric("Total Comments", total2)
                st.metric("Positive %", f"{pos_per2:.2f}%")
                st.metric("Negative %", f"{neg_per2:.2f}%")


            # Chart Compare


            import matplotlib.pyplot as plt


            labels = ['Positive', 'Negative', 'Neutral']


            video1_scores = [pos_per1, neg_per1, neu_per1]
            video2_scores = [pos_per2, neg_per2, neu_per2]


            x = range(len(labels))


            fig, ax = plt.subplots()


            ax.bar(x, video1_scores, width=0.4)
            ax.bar([i + 0.4 for i in x], video2_scores, width=0.4)


            ax.set_xticks([i + 0.2 for i in x])
            ax.set_xticklabels(labels)

            ax.set_title("Sentiment Comparison")

            ax.set_ylabel("Percentage")


            st.pyplot(fig)



            # Winner


            st.markdown("## 🏆 Result")


            if pos_per1 > pos_per2:

                st.success("Video 1 has better audience response")

            elif pos_per2 > pos_per1:

                st.success("Video 2 has better audience response")

            else:

                st.info("Both videos have similar response")



        else:

            st.error("Error processing videos")

elif choice == 'Download Report':

    st.title("📥 Download Professional Sentiment Report")

    video_url = st.text_input("Enter YouTube Video URL")

    if st.button("Generate PDF Report"):

        if video_url:

            result = process_comments(video_url)

            if result:

                positive_comments, negative_comments, neutral_comments, avg_polarity, positive_percent, negative_percent, neutral_percent = result

                total_comments = len(positive_comments) + len(negative_comments) + len(neutral_comments)


                # -------------------------
                # GET VIDEO DETAILS
                # -------------------------

                api_key = 'AIzaSyCrXfmjr5keE6Lg0MuZD_KTfs0b_ptMKTk'

                youtube = build('youtube', 'v3', developerKey=api_key)

                video_id_match = re.search(
    r'(?:youtu\.be\/|youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=))([^"&?\/\s]{11})',
    video_url
)

                if video_id_match:
                    video_id = video_id_match.group(1)
                else:
                    st.error("Invalid YouTube URL")
                    st.stop()
                video_data = youtube.videos().list(

                    part="snippet,statistics",

                    id=video_id

                ).execute()


                snippet = video_data['items'][0]['snippet']

                stats = video_data['items'][0]['statistics']


                video_title = snippet['title']

                channel = snippet['channelTitle']

                publish_date = snippet['publishedAt']

                views = stats.get('viewCount', 'N/A')

                likes = stats.get('likeCount', 'N/A')


                # -------------------------
                # CREATE CHARTS
                # -------------------------

                import matplotlib.pyplot as plt


                labels = ['Positive', 'Negative', 'Neutral']

                counts = [len(positive_comments), len(negative_comments), len(neutral_comments)]


                pie_chart = "pie_chart.png"

                bar_chart = "bar_chart.png"


                plt.figure()

                plt.pie(counts, labels=labels, autopct='%1.1f%%')

                plt.title("Sentiment Distribution")

                plt.savefig(pie_chart)

                plt.close()


                plt.figure()

                plt.bar(labels, counts)

                plt.title("Sentiment Count")

                plt.savefig(bar_chart)

                plt.close()


                # -------------------------
                # AI INSIGHT
                # -------------------------

                if positive_percent > 70:

                    insight = "Excellent audience response. Highly successful video."

                    recommendation = "Continue making similar content."

                elif positive_percent > negative_percent:

                    insight = "Overall audience response is positive."

                    recommendation = "Minor improvements can increase engagement."

                else:

                    insight = "Audience response is negative."

                    recommendation = "Improve content quality and presentation."


                # -------------------------
                # CREATE PDF
                # -------------------------

                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image

                from reportlab.lib.styles import getSampleStyleSheet

                from datetime import datetime


                pdf_file = "YouTube_Sentiment_Report.pdf"


                styles = getSampleStyleSheet()

                doc = SimpleDocTemplate(pdf_file)


                elements = []


                # TITLE

                elements.append(Paragraph("YouTube Sentiment Analysis Report", styles['Heading1']))

                elements.append(Spacer(1,20))


                # VIDEO INFO

                elements.append(Paragraph("Video Information", styles['Heading2']))

                elements.append(Paragraph(f"Title: {video_title}", styles['Normal']))

                elements.append(Paragraph(f"Channel: {channel}", styles['Normal']))

                elements.append(Paragraph(f"Publish Date: {publish_date}", styles['Normal']))

                elements.append(Paragraph(f"Views: {views}", styles['Normal']))

                elements.append(Paragraph(f"Likes: {likes}", styles['Normal']))

                elements.append(Spacer(1,20))


                # SUMMARY

                elements.append(Paragraph("Sentiment Summary", styles['Heading2']))

                elements.append(Paragraph(f"Total Comments: {total_comments}", styles['Normal']))

                elements.append(Paragraph(f"Positive: {positive_percent:.2f}%", styles['Normal']))

                elements.append(Paragraph(f"Negative: {negative_percent:.2f}%", styles['Normal']))

                elements.append(Paragraph(f"Neutral: {neutral_percent:.2f}%", styles['Normal']))

                elements.append(Paragraph(f"Sentiment Score: {avg_polarity:.2f}", styles['Normal']))

                elements.append(Spacer(1,20))


                # AI INSIGHT

                elements.append(Paragraph("AI Insight", styles['Heading2']))

                elements.append(Paragraph(insight, styles['Normal']))

                elements.append(Spacer(1,20))


                # RECOMMENDATION

                elements.append(Paragraph("Recommendation", styles['Heading2']))

                elements.append(Paragraph(recommendation, styles['Normal']))

                elements.append(Spacer(1,20))


                # CHARTS

                elements.append(Paragraph("Pie Chart", styles['Heading2']))

                elements.append(Image(pie_chart, width=400, height=300))

                elements.append(Spacer(1,20))


                elements.append(Paragraph("Bar Chart", styles['Heading2']))

                elements.append(Image(bar_chart, width=400, height=300))

                elements.append(Spacer(1,20))


                # DATE

                elements.append(Paragraph(

                    f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",

                    styles['Normal']

                ))


                doc.build(elements)


                # DOWNLOAD BUTTON

                with open(pdf_file, "rb") as f:

                    st.download_button(

                        "⬇ Download Professional PDF",

                        f,

                        file_name=pdf_file,

                        mime="application/pdf"

                    )


                st.success("Professional Report Ready!")


            else:

                st.error("Error processing video")


        else:

            st.warning("Enter video URL")

elif choice == 'About':

    st.title("About This Project")

    st.markdown("""
## 🎯 YouTube Comment Sentiment Analysis with AI Insights

This project is an advanced AI-powered web application designed to analyze and understand audience sentiment on YouTube videos.

It helps **content creators, businesses, and researchers** gain meaningful insights from viewer comments using **Natural Language Processing (NLP)** and **Artificial Intelligence**.

---

## 🚀 Key Features

### 📊 Sentiment Dashboard
Visualize audience sentiment with interactive charts including:

• Positive, Negative, Neutral distribution  
• Engagement metrics  
• AI-generated insights  

---

### 🧠 AI Insight Engine

Our intelligent insight system automatically:

• Evaluates audience reaction  
• Detects engagement level  
• Provides recommendations  
• Identifies content performance  

---

### 🔎 Comment Explorer

Advanced comment analysis tool that allows you to:

• Search comments  
• Filter by sentiment  
• Explore audience opinions  

---

### ⚔ Video Comparison

Compare two YouTube videos to:

• Identify better performing content  
• Compare audience sentiment  
• Analyze engagement differences  

---

### 📥 Professional Report Generator

Generate downloadable PDF reports containing:

• Sentiment analysis summary  
• Charts and visualizations  
• AI insights and recommendations  
• Video statistics  

Perfect for:

• Content creators  
• Marketing teams  
• Research work  

---

## 🧠 Technologies Used

• Python  
• Streamlit  
• Natural Language Processing (NLTK)  
• YouTube Data API  
• Machine Learning Concepts  
• ReportLab (PDF generation)  
• Matplotlib (Data Visualization)

---

## 🎯 Project Goal

The goal of this project is to build an intelligent system that transforms raw YouTube comments into meaningful insights to help improve content strategy and understand audience behavior.

---

## 👨‍💻 Developer

**Rudra Khadela**  
AI & Machine Learning Developer  

Passionate about building real-world AI applications using:

• Artificial Intelligence  
• Generative AI  
• Large Language Models  
• NLP Systems  

---

⭐ This project demonstrates practical implementation of AI in real-world applications.
""")
    st.write('-Rudra Khadela')

elif choice == "Contact":

    st.title("📬 Contact Me")

    # -------------------------
    # CUSTOM CSS
    # -------------------------

    st.markdown("""
    <style>

    .intro-text{
        font-size:18px;
        line-height:1.6;
    }

    .name{
        font-size:32px;
        font-weight:bold;
    }

    .role{
        font-size:20px;
        color:gray;
        margin-bottom:15px;
    }

    .social-btn{
        display:inline-block;
        padding:10px 18px;
        margin:5px;
        border-radius:8px;
        text-decoration:none;
        color:white;
        font-weight:bold;
    }

    .linkedin{background:#0077b5;}
    .github{background:#333;}
    .email{background:#D44638;}

    </style>
    """, unsafe_allow_html=True)


    # -------------------------
    # LEFT RIGHT LAYOUT
    # -------------------------

    col1, col2 = st.columns([1,2])


    # LEFT SIDE → IMAGE

    with col1:

        image = Image.open("templates/Rudraa.jpeg")

        st.image(image, width=250)



    # RIGHT SIDE → INTRO

    with col2:

        st.markdown('<div class="name">Rudra Khadela</div>', unsafe_allow_html=True)

        st.markdown('<div class="role">AI & Machine Learning Developer</div>', unsafe_allow_html=True)


        st.markdown("""
        <div class="intro-text">

        I am an AI Developer passionate about building real-world AI applications 
        that solve meaningful problems.

        I specialize in:

        • Machine Learning  
        • Natural Language Processing  
        • Generative AI  
        • LLM Applications  
        • Streamlit AI Dashboards  


        This YouTube Sentiment Analysis project helps creators understand audience
        emotions, compare videos, and generate detailed insight reports.

        </div>

        """, unsafe_allow_html=True)



        # SOCIAL LINKS

        st.markdown("""

        <a href="https://www.linkedin.com/in/rudra-khadela-49427a253" target="_blank" class="social-btn linkedin">LinkedIn</a>

        <a href="https://github.com/Rudrakhadela" target="_blank" class="social-btn github">GitHub</a>

        <a href="mailto:rudrakhadela@gmail.com" target="_blank" class="social-btn email">Email</a>

        """, unsafe_allow_html=True)



    # -------------------------
    # SEND MESSAGE FORM
    # -------------------------

    st.write("")
    st.write("")

    st.subheader("📝 Send Message")

    name = st.text_input("Your Name")

    email = st.text_input("Your Email")

    message = st.text_area("Your Message")


    if st.button("Send Message"):

        if name and email and message:

            st.success("✅ Message Sent Successfully!")

        else:

            st.warning("Please fill all fields")



    # -------------------------
    # RESUME DOWNLOAD
    # -------------------------

    st.write("")
    st.subheader("📄 Download Resume")

    with open("templates/Rudraa Khadela Resume photo (1).pdf", "rb") as file:

        st.download_button(

            "Download Resume",

            file,

            file_name="Rudra_Khadela_Resume.pdf"

        )


# Streamlit UI
st.markdown("""
    <style>
        .big-title {
            animation: scale-in-center 1.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) both;
        }

        @keyframes scale-in-center {
            0% {
                transform: scale(0);
                opacity: 0;
            }
            100% {
                transform: scale(1);
                opacity: 1;
            }
        }

        h1, h2, h3, h4, h5, h6 {
            animation: slide-in-left 0.5s ease-out both;
        }


        @keyframes slide-in-left {
            0% {
                transform: translateX(-100%);
                opacity: 0;
            }
            100% {
                transform: translateX(0);
                opacity: 1;
            }
        }
    </style>
""", unsafe_allow_html=True)
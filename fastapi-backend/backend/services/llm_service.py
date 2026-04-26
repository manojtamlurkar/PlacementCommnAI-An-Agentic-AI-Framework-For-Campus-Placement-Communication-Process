import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY is not set. Falling back to default message templates.")
        return None
    return Groq(api_key=api_key)

def generate_email(company_name: str, poc_name: str = None) -> str:
    """
    Returns the official CDC NITK Surathkal campus placement invitation email.
    Only the company name is substituted dynamically.
    """
    greeting = f"Dear {poc_name} Team," if poc_name else f"Dear {company_name} Team,"
    return f"""{greeting}

Greetings from NITK Surathkal.

NITK has been at the forefront of imparting high-quality technical education since 1960. State-of-the-art infrastructure, brightest student minds, highly motivated and qualified faculty, and a lush green beach campus are the hallmarks of this institution, all of which are reflected in many National & International rankings like NIRF, QS World Rankings where we have been reigning consistently in the top positions.

As a part of the campus placement drive for the Students graduating in May 2026 (UG) and July 2026 (PG and Ph.D.), National Institute of Technology Karnataka, Surathkal cordially invites your organization to visit the campus for the placement and Internship process. On behalf of all our Students, Staff, Faculty, Director, and myself, I extend a warm welcome to you to visit our campus and conduct the recruitment process. We assure you the best of the talent at NITK.

Our diverse programs, including B.Tech., M.Tech., Ph.D., MCA, MSc. and MBA produce talented professionals equipped with practical skills. The B.Tech. curriculum has an additional 'Minors' course option where the students are offered a wide variety of courses from different branches to choose from. For example, a Mechanical student may be doing a minor in CSE or ECE and by the end have a detailed knowledge about the same.

Key highlights of our Institute:
●  Large talent pool with diverse skills.
●  Pre-placement training to enhance technical and soft skills.
●  Dedicated placement cell for seamless recruitment.
●  Excellent campus facilities fostering innovation.

Please find attachments of the following documents:
1. CDC policy for companies                 2. Program details
3. Placement form                               4. Internship form

To view our Institute Brochure, you can visit our website https://cdc.nitk.ac.in/ & click on the "Download Brochure".

We request that you kindly mail the filled Placement & Internship form as applicable along with Job Description (JD) as soon as possible (Preferably before 21 July, 2025), and while replying, please use the "Reply All" feature so that the placement team can take you forward with the process.

Feel free to contact me or our Student Head PC's: Mr. Pradham Eswar (Mobile: 798-100-1389) or Mr. Piyush Patel (Mobile: 969-178-2915) for any clarification.

Looking forward to your cooperation and a win-win situation for all of us.

With Best regards,

Prof. Anish
Professor Incharge - Student Placements, CDC,
Professor, Dept. of Mechanical Engineering
National Institute of Technology Karnataka, Surathkal
PO Srinivasnagar - 575025
Email: cdcentre@nitk.edu.in || anish@nitk.edu.in
Ph: 0824-2474061, 2473053, 2473401 || Mobile: 9036317552
https://cdc.nitk.ac.in/

#############################################
The details contained in this communication are considered confidential.
If you are not the intended recipient, please delete this message and inform the sender immediately.
Any unauthorized use is strictly prohibited.
###########################################
"""

def generate_followup_email(company_name: str, poc_name: str, email_history: list) -> str:
    """
    Generates a context-aware follow-up email using Groq LLM.
    email_history: [{direction, subject, body, timestamp}, ...] ordered oldest → newest
    """
    greeting = f"Dear {poc_name}," if poc_name else f"Dear {company_name} Team,"
    default_followup = (
        f"{greeting}\n\n"
        f"Greetings from the Career Development Centre (CDC), NITK Surathkal.\n\n"
        f"We are following up regarding our earlier communication about the Campus Placement Drive at NITK Surathkal "
        f"for the graduating batch of 2026. We sincerely hope {company_name} will consider participating.\n\n"
        f"We would be happy to provide any additional information or address any queries at your earliest convenience.\n\n"
        f"Looking forward to your positive response.\n\n"
        f"With Best regards,\n"
        f"Career Development Centre (CDC)\n"
        f"National Institute of Technology Karnataka, Surathkal\n"
        f"Email: cdcentre@nitk.edu.in\n"
        f"Ph: 0824-2474061 || Mobile: 9036317552\n"
        f"https://cdc.nitk.ac.in/"
    )
    try:
        client = get_groq_client()
        if not client:
            return default_followup

        # --- Build a smart thread summary ---
        # SENT (CDC) emails: condense to one-liner — their full body is the template and confuses the LLM
        # RECEIVED (company) emails: show full text — this is the key signal for the LLM
        thread_parts = []
        last_company_reply = None

        for e in email_history:  # already oldest → newest from DB
            if e["direction"] == "SENT":
                thread_parts.append(
                    f"[CDC → {company_name}] Subject: \"{e['subject']}\"\n"
                    f"(CDC sent the campus placement drive invitation for the 2026 batch.)"
                )
            else:
                body_preview = e["body"].strip()
                thread_parts.append(
                    f"[{company_name} → CDC] Subject: \"{e['subject']}\"\n"
                    f"Company's message: {body_preview}"
                )
                last_company_reply = body_preview  # track most recent reply

        thread_summary = "\n\n---\n\n".join(thread_parts)

        # Build focused instructions based on thread state
        if last_company_reply:
            reply_instruction = (
                f"The company's most recent reply was:\n\"{last_company_reply}\"\n\n"
                f"Write a follow-up email that:\n"
                f"- Warmly acknowledges and specifically responds to what {company_name} said\n"
                f"- Answers any questions or concerns they raised\n"
                f"- Moves the conversation forward (next steps, confirming details, sharing forms etc.)\n"
            )
        else:
            reply_instruction = (
                f"{company_name} has NOT replied yet.\n\n"
                f"Write a polite follow-up that:\n"
                f"- References the previous email sent and notes no response was received\n"
                f"- Gently reiterates the placement drive invitation\n"
                f"- Asks them to please respond at their earliest convenience\n"
            )

        prompt = (
            f"You are the Career Development Centre (CDC) at the National Institute of Technology Karnataka (NITK), Surathkal.\n"
            f"You are writing a professional follow-up email to {poc_name or 'the HR team'} at {company_name} "
            f"regarding the campus placement drive.\n\n"
            f"=== Email Thread (oldest to newest) ===\n\n"
            f"{thread_summary}\n\n"
            f"=== Your Task ===\n\n"
            f"{reply_instruction}"
            f"- Maintain a warm, formal, and professional CDC tone throughout\n"
            f"- Keep the email under 200 words\n"
            f"- Do NOT use placeholders like [Date], [Name], or [Insert here]\n"
            f"- Close with this exact CDC signature:\n\n"
            f"With Best regards,\n"
            f"Prof. Anish\n"
            f"Professor Incharge - Student Placements, CDC\n"
            f"National Institute of Technology Karnataka, Surathkal\n"
            f"Email: cdcentre@nitk.edu.in || anish@nitk.edu.in\n"
            f"Ph: 0824-2474061 || Mobile: 9036317552\n"
            f"https://cdc.nitk.ac.in/"
        )

        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        result = completion.choices[0].message.content
        logger.info(
            f"Generated follow-up for {company_name} | "
            f"thread_depth={len(email_history)} | has_reply={'yes' if last_company_reply else 'no'}"
        )
        return result
    except Exception as e:
        logger.error(f"Groq follow-up email generation failed: {e}")
        return default_followup


def generate_telegram_message(company_name: str) -> str:
    default_text = f"Recruitment update for {company_name}:\nSchedule confirmed. Please check details."
    try:
        client = get_groq_client()
        if not client:
            return default_text
            
        prompt = f"Write a short professional message for students announcing recruitment update for {company_name}."
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        generated_msg = completion.choices[0].message.content
        logger.info(f"Successfully generated Telegram message using Groq LLM for {company_name}")
        return generated_msg
    except Exception as e:
        logger.error(f"Groq LLM telegram generation failed: {e}")
        return default_text

def parse_email_content(text: str) -> dict:
    default_json = {"intent": "UNKNOWN", "time": None}
    try:
        client = get_groq_client()
        if not client:
            return default_json
            
        prompt = f"""Analyze the following email excerpt and extract the intent (must be exactly SCHEDULE_CONFIRM, CHANGE, QUERY, or UNKNOWN) and a proposed time if present.
Format the response strictly as a JSON object: {{"intent": "...", "time": "..."}}
Email Text:
{text}
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        
        result_content = completion.choices[0].message.content
        logger.info("Successfully parsed email intent using Groq LLM")
        return json.loads(result_content)
    except Exception as e:
        logger.error(f"Groq LLM email parsing failed: {e}")
        return default_json

def generate_telegram_drive_message(company_name: str, drive_date: str, classroom_name: str, registration_link: str, followup_questions: list) -> str:
    default_text = f"**{company_name} - Campus Drive Update**\n\nDate: {drive_date}\nVenue: {classroom_name}\nRegistration Link: {registration_link or 'TBA'}\n\nNote: We are clarifying a few details with {company_name}."
    try:
        client = get_groq_client()
        if not client:
            return default_text
        
        clarifications = ""
        if followup_questions:
            clarifications = "We are currently seeking clarification from the company on the following points:\n" + "\n".join([f"- {q}" for q in followup_questions])
            
        prompt = (
            f"Write a Telegram announcement to NITK Surathkal students regarding the upcoming campus drive for {company_name}.\n"
            f"Include the following details clearly:\n"
            f"- Date: {drive_date}\n"
            f"- Venue: {classroom_name}\n"
            f"- Registration Link: {registration_link or 'Will be shared soon'}\n\n"
            f"{clarifications}\n"
            f"Keep the tone encouraging, professional, and clear. Format the message for a Telegram channel (you can use basic markdown but keep it clean). Do not include any placeholder text."
        )
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        result = completion.choices[0].message.content
        logger.info(f"Generated Telegram drive message for {company_name}")
        return result
    except Exception as e:
        logger.error(f"Groq Telegram drive message gen failed: {e}")
        return default_text

def generate_followup_questions_email(company_name: str, poc_name: str, questions: list, email_history: list, spoc_name: str = None) -> str:
    greeting = f"Dear {poc_name}," if poc_name else f"Dear {company_name} Team,"
    qs_bullets = "\n".join([f"- {q}" for q in questions])
    
    sender_name = spoc_name if spoc_name else "CDC NITK Surathkal"
    default_text = f"{greeting}\n\nGreetings from CDC, NITK Surathkal.\n\nThank you for confirming the drive schedule. We have a few questions before we proceed:\n\n{qs_bullets}\n\nPlease let us know.\n\nRegards,\n{sender_name}"
    
    try:
        client = get_groq_client()
        if not client:
            return default_text
            
        # Build thread summary
        thread_parts = []
        for e in email_history:
            sender = "CDC" if e["direction"] == "SENT" else company_name
            thread_parts.append(f"[{sender}] Subject: {e['subject']}\n{e['body'][:300]}")
        thread_summary = "\n\n---\n\n".join(thread_parts)
        
        prompt = (
            f"You are the Career Development Centre (CDC) at NITK Surathkal.\n"
            f"You need to write a follow-up email to {company_name} ({poc_name or 'HR Team'}).\n"
            f"They recently replied or there is an ongoing conversation. Based on the thread summary below, write a response that acknowledges their previous message and formally asks the following clarification questions:\n\n"
            f"Questions to ask:\n{qs_bullets}\n\n"
            f"Email Thread:\n{thread_summary}\n\n"
            f"Keep it professional, warm, under 200 words, and close with the Signature: {sender_name}."
        )
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        result = completion.choices[0].message.content
        logger.info(f"Generated follow-up questions email for {company_name}")
        return result
    except Exception as e:
        logger.error(f"Groq follow-up questions email failed: {e}")
        return default_text

def generate_spoc_assignment_email(spoc_name: str, company_name: str, hr_email: str) -> str:
    default_text = f"Dear {spoc_name},\n\nYou have been officially assigned as the Single Point of Contact (SPOC) for the upcoming {company_name} placement drive.\n\nPlease take over communications with the HR team at {hr_email} and coordinate the logistics.\n\nRegards,\nCDC NITK Surathkal Workflow Orchestrator"
    
    try:
        client = get_groq_client()
        if not client:
            return default_text
            
        prompt = (
            f"You are the CDC NITK Surathkal Workflow Orchestrator AI.\n"
            f"Write an internal automated notification email to '{spoc_name}', who has just been assigned as the Single Point of Contact (SPOC) for the upcoming '{company_name}' recruitment drive.\n"
            f"Their job is to take over the pipeline, handle queries, broadcast updates to students via Telegram, and communicate with the HR ({hr_email}).\n"
            f"Keep the tone encouraging, structured, instructional, and brief (under 150 words). Format it clearly without placeholders."
        )
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        result = completion.choices[0].message.content
        logger.info(f"Generated SPOC assignment overview for {spoc_name}")
        return result
    except Exception as e:
        logger.error(f"Groq SPOC Assignment draft failed: {e}")
        return default_text

def answer_student_question(question: str, company_name: str, company_description: str, email_history: list) -> dict:
    """
    Given a student's question, attempts to answer it using the company's JD/Description and previous email communications.
    Returns: {"can_answer": bool, "answer": "The answer or reasoning", "confidence": float}
    """
    default_resp = {"can_answer": False, "answer": "I don't have enough context to answer this. I will escalate this to the SPOC.", "confidence": 0.0}
    
    try:
        client = get_groq_client()
        if not client:
            return default_resp
            
        thread_parts = []
        for e in email_history:
            sender = "CDC" if e["direction"] == "SENT" else company_name
            thread_parts.append(f"[{sender}] Subject: {e['subject']}\n{e['body']}")
        thread_summary = "\n\n---\n\n".join(thread_parts)

        prompt = f"""You are the 'Company Agent', an AI assistant helping students in the {company_name} recruitment Telegram group.
A student asked: "{question}"

Here is the context available to you:
Company Description/JD:
{company_description or 'Not provided.'}

Recent Email History between CDC and HR:
{thread_summary or 'No emails.'}

Determine if you can confidently and accurately answer the student's question based ONLY on the provided context.
If the answer is explicitly stated or can be strongly inferred, respond with can_answer=true and provide the answer.
If the answer is NOT in the context, respond with can_answer=false and state that it will be forwarded to the HR.

Format your response strictly as a JSON object:
{{"can_answer": true/false, "answer": "Your detailed response to the student", "confidence": 0.0-1.0}}
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        
        result_content = completion.choices[0].message.content
        logger.info(f"Groq processed student question for {company_name}")
        return json.loads(result_content)
    except Exception as e:
        logger.error(f"Groq auto-answer failed: {e}")
        return default_resp

def draft_questions_to_hr(questions_list: list, company_name: str, poc_name: str, spoc_name: str) -> str:
    """
    Drafts an email to HR containing a list of escalated student questions.
    """
    greeting = f"Dear {poc_name}," if poc_name else f"Dear {company_name} HR Team,"
    qs_bullets = "\n".join([f"- {q}" for q in questions_list])
    
    default_text = f"{greeting}\n\nGreetings from CDC NITK Surathkal.\n\nOur students have a few queries regarding the upcoming drive. Could you please clarify the following:\n\n{qs_bullets}\n\nLooking forward to your response.\n\nRegards,\n{spoc_name}\nStudent SPOC, CDC NITK Surathkal"
    
    try:
        client = get_groq_client()
        if not client:
            return default_text
            
        prompt = f"""You are {spoc_name}, the Student SPOC for the {company_name} placement drive at NITK Surathkal.
Write a professional email to {company_name}'s HR team ({poc_name or 'HR Team'}) to ask the following questions raised by students:

{qs_bullets}

Keep the email polite, clear, and professional. It should be under 150 words.
Do not use placeholders. 
End with this signature:
Regards,
{spoc_name}
Student SPOC, CDC NITK Surathkal
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        result = completion.choices[0].message.content
        logger.info(f"Generated HR questions draft for {company_name}")
        return result
    except Exception as e:
        logger.error(f"Groq HR questions draft failed: {e}")
        return default_text

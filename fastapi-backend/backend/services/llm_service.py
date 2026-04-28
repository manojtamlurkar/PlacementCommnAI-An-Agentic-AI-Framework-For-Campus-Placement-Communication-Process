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
                body_preview = e["body"].strip()
                thread_parts.append(
                    f"[CDC → {company_name}] Subject: \"{e['subject']}\"\n"
                    f"CDC's message: {body_preview}"
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

def analyze_hr_response_intent(email_body: str, email_subject: str = "") -> dict:
    """
    Enhanced intent analysis for the autonomous agent.
    Classifies HR email into actionable categories for automated decision-making.
    Returns: {intent, confirmed_date, summary, requires_reply}
    """
    default_result = {
        "intent": "UNKNOWN",
        "confirmed_date": None,
        "summary": "Could not analyze the email.",
        "requires_reply": False
    }
    try:
        client = get_groq_client()
        if not client:
            return default_result

        prompt = f"""You are an AI recruitment coordinator analyzing an HR email response.

Subject: {email_subject}
Email Body:
{email_body[:6000]}

Classify this email into EXACTLY ONE of these intents:
- DRIVE_CONFIRMED: HR has confirmed participation in the campus drive, possibly with dates or JD attached.
- QUERY: HR is asking clarifying questions or requesting more info before confirming.
- REJECTION: HR has declined or expressed inability to participate.
- INFO_SHARED: HR shared JD, compensation, or other details but has NOT yet confirmed dates or participation.
- UNKNOWN: Cannot determine the intent clearly.

Also extract:
- confirmed_date: If the HR mentioned any specific drive date, extract it as a string (e.g., "2026-05-15"). If no date mentioned, set to null.
- summary: A 1-2 sentence summary of what the HR said.
- requires_reply: true if the email asks questions or needs a response from CDC, false otherwise.

Respond STRICTLY as a JSON object:
{{"intent": "...", "confirmed_date": "..." or null, "summary": "...", "requires_reply": true/false}}
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )

        result = json.loads(completion.choices[0].message.content)
        logger.info(f"HR intent analysis: {result.get('intent')} | summary: {result.get('summary', '')[:80]}")
        return result
    except Exception as e:
        logger.error(f"HR response intent analysis failed: {e}")
        return default_result

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

def extract_knowledge_entries(company_name: str, new_email_content: str) -> list:
    """
    Reads a new HR email and extracts distinct factual statements or answers into a JSON list.
    """
    try:
        client = get_groq_client()
        if not client:
            return []

        prompt = f"""You are the CDC NITK Surathkal Knowledge Extraction Engine.
Your job is to read an incoming HR email for {company_name} and extract ALL distinct factual rules, requirements, answers, or data points.

New Incoming Email from HR:
{new_email_content}

Instructions:
1. Break down the email into independent, self-contained factual entries.
2. Group them by "category" (e.g., "Eligibility", "Logistics", "Compensation", "General").
3. Give each entry a short "topic" (e.g., "Minimum CGPA", "Interview Date", "Bond Period").
4. Provide the extracted fact in the "content" field.
5. Return strictly a JSON object with a single key "entries" containing the array of facts.

Expected Output Format:
{
  "entries": [
    {"category": "Eligibility", "topic": "Minimum CGPA", "content": "7.0 CGPA and above with no active backlogs."},
    {"category": "Compensation", "topic": "Stipend", "content": "50,000 INR per month for 6 months."}
  ]
}
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
        )
        
        # Note: Groq with response_format={"type": "json_object"} sometimes expects the root to be an object.
        # To be safe, we wrap the array in a root object if needed, but since we asked for an array, 
        # let's parse it defensively.
        import json
        result_text = completion.choices[0].message.content.strip()
        data = json.loads(result_text)
        
        # Handle cases where LLM returns {"entries": [...]} instead of just [...]
        if isinstance(data, dict):
            for key in data.keys():
                if isinstance(data[key], list):
                    return data[key]
            return []
        elif isinstance(data, list):
            return data
            
        return []
    except Exception as e:
        logger.error(f"Groq KB extraction failed: {e}")
        return []

def answer_student_question(question: str, company_name: str, company_kb: str) -> dict:
    """
    Given a student's question, attempts to answer it using ONLY the company's Knowledge Base.
    Returns: {"can_answer": bool, "answer": "The answer or reasoning", "confidence": float}
    """
    default_resp = {"can_answer": False, "answer": "I don't have enough context to answer this. I will escalate this to the SPOC.", "confidence": 0.0}
    
    try:
        client = get_groq_client()
        if not client:
            return default_resp
            
        kb_text = company_kb or "No knowledge base available yet."

        prompt = f"""You are the 'Company Agent', an AI assistant helping students in the {company_name} recruitment Telegram group.
A student asked: "{question}"

Here is the official Company Knowledge Base:
{kb_text}

Instructions:
1. Determine if you can confidently and accurately answer the student's question based ONLY on the provided Knowledge Base.
2. If the answer is explicitly stated or can be strongly inferred from the KB, respond with can_answer=true and provide the answer.
3. If the answer is NOT in the KB, respond with can_answer=false and state that it will be forwarded to the HR. Do NOT guess or make up information.
4. Keep the tone friendly and professional.

Format your response strictly as a JSON object:
{{"can_answer": true/false, "answer": "Your detailed response to the student", "confidence": 0.0-1.0}}
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
        )
        
        import json
        result_text = completion.choices[0].message.content
        data = json.loads(result_text)
        logger.info(f"Answered Q based on KB for {company_name}: {data.get('can_answer')}")
        return data
    except Exception as e:
        logger.error(f"Groq question answering failed: {e}")
        return default_resp

def draft_questions_to_hr(questions_list: list, company_name: str, poc_name: str, spoc_name: str) -> str:
    """
    Drafts an email to HR containing a list of escalated student questions.
    Uses LLM to deduplicate and professionally format the raw queries before inserting into a template.
    """
    greeting = f"Dear {poc_name}," if poc_name else f"Dear {company_name} HR Team,"
    raw_qs = "\n".join([f"- {q}" for q in questions_list])
    
    default_text = f"{greeting}\n\nGreetings from CDC NITK Surathkal.\n\nOur students have a few queries regarding the upcoming drive. Could you please clarify the following:\n\n{raw_qs}\n\nLooking forward to your response.\n\nRegards,\n{spoc_name}\nStudent SPOC, CDC NITK Surathkal"
    
    try:
        client = get_groq_client()
        if not client:
            return default_text
            
        prompt = f"""You are an assistant responsible for transforming raw student queries into a structured, professional format suitable for communication with a company HR.

Your task is to process a list of student questions and produce a clean, deduplicated, and well-organized set of formal inquiries.

Instructions:
1. Analyze all input questions carefully.
2. Identify and merge duplicate or semantically similar questions.
3. Group related questions under common themes.
4. Rewrite them into clear, professional, and concise bullet points.
5. Remove informal language, repetitions, and irrelevant details.
6. Do NOT lose the original intent of any question.
7. Do NOT introduce new information or assumptions.
8. Keep the output suitable for an official academic communication.

Raw Student Questions:
{raw_qs}

Output format:
- Start with a short header:
  "We would appreciate clarification on the following:"
- Then provide grouped bullet points (no more than necessary, keep it concise).
- Do NOT include student names, timestamps, or chat-style text.
- Do NOT explain your reasoning.
- Do NOT include raw questions.

Goal:
Transform unstructured student queries into a minimal, professional, and non-redundant set of HR-facing questions."""

        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        
        structured_qs = completion.choices[0].message.content.strip()
        
        # Assemble final email
        result = f"{greeting}\n\nGreetings from CDC NITK Surathkal.\n\n{structured_qs}\n\nLooking forward to your response.\n\nRegards,\n{spoc_name}\nStudent SPOC, CDC NITK Surathkal"
        
        logger.info(f"Generated HR questions draft for {company_name}")
        return result
    except Exception as e:
        logger.error(f"Groq HR questions draft failed: {e}")
        return default_text

def generate_telegram_broadcast_draft(company_name: str, company_description: str, email_history: list, invite_link: str) -> str:
    """
    Drafts a DETAILED announcement for the MAIN student channel.
    Purpose: Announce the drive, provide full JD/eligibility details, and give the group invite link.
    """
    default_text = (
        f"📢 **New Campus Drive: {company_name}**\n\n"
        f"We are excited to announce that **{company_name}** is visiting NITK Surathkal for campus recruitment!\n\n"
        f"🔗 Join the dedicated group for full updates and logistics:\n"
        f"👉 {invite_link}\n\n"
        f"_(Posted by CDC NITK Surathkal)_"
    )
    try:
        client = get_groq_client()
        if not client:
            return default_text

        latest_received = None
        for e in reversed(email_history):
            if e["direction"] == "RECEIVED":
                latest_received = e
                break

        if latest_received:
            email_context = f"Subject: {latest_received['subject']}\nBody: {latest_received['body']}"
        else:
            email_context = "No recent emails received from the company."

        prompt = f"""You are the CDC NITK Surathkal Recruitment System.
Write a COMPREHENSIVE announcement for the MAIN student announcement channel to inform students about the {company_name} campus placement drive.

Latest Email from HR (may contain JD/compensation details):
{email_context[-8000:]}

Invite Link to the company-specific group: {invite_link}

Instructions:
1. Start with a warm announcement of the company name.
2. Include the FULL details under CLEAR HEADINGS (include only sections where data is available):
   📌 **Role**: [role name]
   🎓 **Eligible Branches**: [list all branches and degree types]
   📝 **Job Description**: [description of responsibilities]
   ✅ **Minimum Qualifications**: [required skills/qualifications]
   💰 **Compensation Breakdown**: [full CTC details]
   📅 **Application Deadline**: [date and time]
3. Strongly encourage interested students to join the dedicated Telegram group using the invite link.
4. Use Markdown formatting (bold for company name and key terms).
5. Do NOT omit any compensation or eligibility details — include everything from the HR email.
6. Total length can be up to 350 words.

Sign off with:
_(Posted by CDC NITK Surathkal)_
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        result = completion.choices[0].message.content
        logger.info(f"Generated main-channel announcement for {company_name}")
        return result
    except Exception as e:
        logger.error(f"Main channel broadcast drafting failed: {e}")
        return default_text


def generate_company_group_jd_post(company_name: str, email_history: list) -> str:
    """
    Drafts a DETAILED JD post for the company-specific Telegram group.
    Includes: Role Name, Job Description, Eligibility Criteria, CTC/Compensation breakdown,
              Application Deadline, and any other relevant details from the HR email/attachments.
    """
    default_text = (
        f"📋 **{company_name} — Full Drive Details**\n\n"
        f"Details from HR will be updated here shortly. Stay tuned!\n\n"
        f"_(Posted by CDC NITK Surathkal)_"
    )
    try:
        client = get_groq_client()
        if not client:
            return default_text

        latest_received = None
        for e in reversed(email_history):
            if e["direction"] == "RECEIVED":
                latest_received = e
                break

        if not latest_received:
            return default_text

        email_context = f"Subject: {latest_received['subject']}\nBody: {latest_received['body']}"

        prompt = f"""You are the CDC NITK Surathkal Recruitment System.
Create a COMPREHENSIVE and well-structured Telegram post for the **{company_name}** company-specific placement group.
This message will be pinned in the group and should serve as the single source of truth for all drive details.

HR Email (includes text from attached PDFs like JD and Compensation documents):
{email_context[-8000:]}

Instructions:
1. Start with a welcome message to the group.
2. Organize the information under CLEAR HEADINGS using these sections (include only sections where data is available):
   📌 **Role**: [role name]
   🎓 **Eligible Branches**: [list all branches and degree types]
   📝 **Job Description**: [brief description of responsibilities]
   ✅ **Minimum Qualifications**: [required skills/qualifications]
   ⭐ **Preferred Qualifications**: [preferred skills]
   💰 **Compensation Breakdown**: [full CTC details per degree type]
   📅 **Application Deadline**: [date and time]
3. End with a note encouraging students to ask questions in this group.
4. Use Markdown formatting with bold headings and bullet points.
5. Do NOT omit any compensation or eligibility details — include everything from the HR email.
6. Total length can be up to 400 words.

Sign off with:
_(Posted by CDC NITK Surathkal · {company_name} Drive 2026)_
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        result = completion.choices[0].message.content
        logger.info(f"Generated detailed JD post for {company_name} company group")
        return result
    except Exception as e:
        logger.error(f"Company group JD post generation failed: {e}")
        return default_text


def extract_answers_from_hr_email(email_body: str, questions_list: list) -> dict:
    """
    Given an HR's reply email and a list of questions that were asked, 
    extracts the answers to those questions.
    Returns a dict mapping the question text to the HR's answer.
    """
    if not questions_list:
        return {}
        
    try:
        client = get_groq_client()
        if not client:
            return {}
            
        qs_bullets = "\n".join([f"- {q}" for q in questions_list])
        
        prompt = f"""You are an AI assistant analyzing an HR email reply.
We previously asked HR the following questions:
{qs_bullets}

Here is the HR's reply:
"{email_body}"

Extract the answers HR provided for each question. 
Return the result STRICTLY as a JSON object where the keys are the exact question strings, and the values are the extracted answers.
If a question was not answered in the email, do not include it in the JSON object, or set its value to null.

Format:
{{
  "question text 1": "HR's answer",
  "question text 2": "HR's answer"
}}
"""
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        
        result_content = completion.choices[0].message.content
        logger.info(f"Successfully extracted HR answers via LLM")
        return json.loads(result_content)
    except Exception as e:
        logger.error(f"Groq LLM answer extraction failed: {e}")
        return {}

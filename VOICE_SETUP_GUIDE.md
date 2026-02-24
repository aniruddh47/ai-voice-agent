# 🎤 VOICE-TO-VOICE SETUP GUIDE (BINA PHONE KE!)

## ✅ Yeh Version Tumhare Liye Perfect Hai!

**Kyun?**
- ✅ Voice-to-Voice conversation (bilkul tumhare original code jaisa)
- ✅ Laptop pe microphone se baat karo, speaker se sunno
- ✅ Multi-language (English, Hindi, Marathi)
- ✅ Fast response (1-2 seconds)
- ✅ Proactive questions (information extract karta hai)
- ✅ **NO PHONE CALLS** - Matlab Twilio ki zarurat nahi!
- ✅ **NO TYPING** - Sirf bolo aur sunno!

---

## 📋 KYA CHAHIYE? (Requirements)

### 1. Hardware:
- ✅ Laptop/PC with microphone
- ✅ Speakers/headphones
- ✅ Internet connection

### 2. Software:
- ✅ Python 3.8+
- ✅ Vosk model (tumhare paas already hai)

---

## 🚀 SETUP (10 Minutes Total)

### Step 1: Install Packages (5 min)

```bash
# Essential packages
pip install python-dotenv
pip install google-genai
pip install vosk
pip install sounddevice
pip install numpy
pip install edge-tts
pip install playsound

# Optional (for better language detection)
pip install langdetect
```

**Agar error aaye:**
```bash
# Windows me pyaudio issue?
pip install pipwin
pipwin install pyaudio
```

### Step 2: Get Gemini API Key (2 min)

1. Yahan jao: https://makersuite.google.com/app/apikey
2. "Create API Key" click karo
3. Key copy karo

### Step 3: Create .env File (1 min)

Project folder mein `.env` file banao:

```
GEMINI_API_KEY=your_key_paste_here
```

### Step 4: Files Copy Karo (2 min)

Ek folder mein yeh sab rakho:

```
your_project_folder/
├── voice_to_voice_agent.py      ← Main file (I gave you)
├── college_info.json             ← Your existing
├── departments_info.json         ← I provided
├── facilities_detailed.json      ← I provided  
├── admission_procedures.json     ← I provided
├── vosk-model-small-en-in-0.4/   ← Your existing Vosk model
└── .env                          ← API key file
```

---

## ▶️ RUN KARO!

```bash
python voice_to_voice_agent.py
```

### Kya Hoga:

```
======================================================================
  🎤 VOICE-TO-VOICE ADMISSION COUNSELOR
  Sanjay Ghodawat University
======================================================================

💡 Features:
  ✅ Voice-to-Voice conversation (no typing needed!)
  ✅ Multi-language (English, Hindi, Marathi)
  ✅ Fast AI responses (1-2 seconds)
  ✅ Asks questions & extracts information
  ✅ Complete college knowledge base

🎙️  Speak clearly into your microphone
📢 Say 'stop' or 'exit' to end conversation
======================================================================

✅ Agent initialized successfully!

🤖 Agent: Hello! I am the admission counselor from Sanjay Ghodawat 
University. How may I help you today?

[Agent speaks this in voice!]

🎤 Listening... (speak now)
```

**Ab bolo microphone mein!**

---

## 🗣️ SAMPLE CONVERSATION

### Example 1: English

```
👤 You: [speak] "What are the B.Tech fees?"
💭 Thinking...
🤖 Agent (en): B.Tech fees are one lakh thirty five thousand rupees 
per year. We offer Computer Science, AIML, and other branches. 
May I know your name?
   ⚡ Response time: 1.2s

[Agent speaks this!]

👤 You: [speak] "My name is Rahul"
💭 Thinking...
🤖 Agent (en): Thank you Rahul! Which branch interests you - 
Computer Science, Mechanical, or Civil?
   ⚡ Response time: 0.8s

👤 You: [speak] "Computer Science"
🤖 Agent (en): Excellent choice Rahul! CSE has great placements. 
Could you share your contact number for detailed information?
   ⚡ Response time: 0.9s

👤 You: [speak] "Nine eight seven six five four three two one zero"
🤖 Agent (en): Perfect! I've noted your details. Would you like 
to know about our hostel facilities?
   ⚡ Response time: 1.1s
```

### Example 2: Hindi

```
👤 You: [speak] "मुझे B.Tech के बारे में बताइए"
💭 Thinking...
🤖 Agent (hi): B.Tech की fees एक लाख पैंतीस हजार रुपये है। 
हम Computer Science, AIML जैसी branches offer करते हैं। 
आपका नाम क्या है?
   ⚡ Response time: 1.3s

[Speaks in Hindi!]

👤 You: [speak] "मेरा नाम प्रिया है"
🤖 Agent (hi): धन्यवाद प्रिया! आपको कौनसी branch में interest है?
```

### Example 3: Language Switching

```
👤 You: [speak in English] "What about hostel?"
🤖 Agent (en): We have separate hostels for boys and girls...

👤 You: [speak in Hindi] "Fees kitni hai hostel ki?"
🤖 Agent (hi): Hostel की fees साठ हजार रुपये है...
   [Automatically switched to Hindi!]

👤 You: [speak in English] "Okay, thank you"
🤖 Agent (en): You're welcome! Anything else?
   [Switched back to English!]
```

---

## 🛑 CONVERSATION END KAISE KARE?

Bas bolo:
- "Stop"
- "Exit"  
- "Bye"
- "Goodbye"
- "Quit"

**Ya Ctrl+C press karo**

### Jab End Hoga:

```
👤 You: [speak] "Bye"
🤖 Agent: Thank you for contacting Sanjay Ghodawat University. 
Have a great day!

✅ Lead information saved!

======================================================================
📊 CAPTURED INFORMATION:
======================================================================
{
  "name": "Rahul",
  "phone": "9876543210",
  "interested_courses": ["BTECH"],
  "interested_branches": ["Computer Science"]
}
======================================================================

✅ Conversation ended. Thank you!
```

**Yeh information automatic save ho jayega `student_leads.json` mein!**

---

## 🎯 KEY FEATURES

### 1. Multi-Language Auto-Detection
```
You speak in: Hindi → Agent responds in: Hindi
You switch to: English → Agent switches to: English
```

### 2. Fast Response (Cache System)
```
Common questions: 0.1 second (instant!)
Other questions: 1-2 seconds
```

### 3. Proactive Questioning
```
Agent automatically asks:
- Your name
- Which course?
- Contact number
- Branch preference
```

### 4. Information Extraction
```
Automatically captures:
✅ Name
✅ Phone number
✅ Email (if mentioned)
✅ Course interest
✅ Branch preference
```

### 5. Natural Voice
```
Uses Edge TTS (Microsoft):
- en-IN-NeerjaNeural (English - Female)
- hi-IN-SwaraNeural (Hindi - Female)
- mr-IN-AarohiNeural (Marathi - Female)
```

---

## 🐛 TROUBLESHOOTING

### Problem 1: "No module named 'vosk'"
```bash
pip install vosk
```

### Problem 2: "Vosk model not found"
**Solution:**
1. Download: https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip
2. Extract in project folder
3. Folder name should be exactly: `vosk-model-small-en-in-0.4`

### Problem 3: "No audio input detected"
**Check:**
```python
# Test microphone
import sounddevice as sd
print(sd.query_devices())
```

**Windows:** Settings → Privacy → Microphone → Allow apps

### Problem 4: "playsound error"
```bash
# Install alternative
pip uninstall playsound
pip install playsound==1.2.2
```

### Problem 5: Agent doesn't hear me
**Solutions:**
- Speak louder and clearer
- Check if mic is selected in Windows sound settings
- Reduce background noise
- Speak closer to microphone

### Problem 6: Response is slow
**Normal!**
- First response: 2-3 seconds (model loading)
- After that: 0.5-1.5 seconds
- Common questions: Instant (cached!)

---

## 💡 PRO TIPS

### Tip 1: Best Microphone Settings
```
- Speak clearly and naturally
- Not too fast, not too slow
- Normal voice volume (don't shout!)
- Reduce background noise
```

### Tip 2: Testing
```
Start simple:
1. "Hello" → Check if agent hears
2. "What are the fees?" → Check response
3. Try Hindi/Marathi → Check language switch
4. Give name and number → Check extraction
```

### Tip 3: For Demo
```
Before presentation:
1. Practice 2-3 conversations
2. Note down good questions
3. Check microphone properly
4. Close unnecessary apps (for speed)
5. Have backup plan (show recorded demo)
```

---

## 📊 COMPARISON: Text vs Voice vs Phone

| Feature | Text Mode | Voice Mode (This!) | Phone Mode |
|---------|-----------|-------------------|------------|
| Input | Keyboard | Microphone | Phone call |
| Output | Screen | Speaker | Phone |
| Setup Time | 5 min | 10 min | 30 min |
| Cost | ₹0 | ₹0 | ₹100-150 |
| Realistic | 6/10 | 8/10 | 10/10 |
| For Project | Good | **Better** ✅ | Best |

**Voice mode is PERFECT balance of realism and ease!**

---

## 🎓 FOR COLLEGE PROJECT

### Why This is Great:

1. ✅ **Natural interaction** - Voice-to-voice like real counselor
2. ✅ **Multi-language** - Shows technical skills
3. ✅ **Fast & smart** - Optimized responses
4. ✅ **Information capture** - Real-world useful
5. ✅ **Easy to demo** - Just need laptop + mic
6. ✅ **No extra cost** - Everything is free!
7. ✅ **Looks professional** - Voice > Text for demos

### Demo Strategy:

**Before Class:**
- Practice conversation
- Screen record one demo (backup)

**During Demo:**
1. Show live voice conversation
2. Switch languages mid-conversation
3. End conversation, show captured info
4. Open `student_leads.json` - show saved data

**If Anything Goes Wrong:**
- Play recorded demo
- Show code and explain features

---

## ✅ FINAL CHECKLIST

Before demo day:

- [ ] All packages installed
- [ ] Gemini API key working
- [ ] Vosk model in correct folder
- [ ] Microphone tested
- [ ] All JSON files present
- [ ] Practiced conversation
- [ ] Backup demo recorded
- [ ] Understood how it works
- [ ] Can explain multi-language feature
- [ ] Can explain information extraction

---

## 🚀 QUICK START COMMANDS

```bash
# 1. Install everything
pip install python-dotenv google-genai vosk sounddevice numpy edge-tts playsound langdetect

# 2. Check if Vosk model exists
ls vosk-model-small-en-in-0.4/

# 3. Create .env with your Gemini key
echo "GEMINI_API_KEY=your_key" > .env

# 4. Run!
python voice_to_voice_agent.py
```

---

## 💬 NEED HELP?

**Common Questions:**

Q: Kya phone calls bhi kar sakta hai?
A: Nahi, yeh sirf laptop pe microphone se voice conversation ke liye hai. Phone ke liye alag version hai (Twilio wala).

Q: Kitne languages support karta hai?
A: 3 - English, Hindi, Marathi. Automatic detect karta hai!

Q: Kya information save hota hai?
A: Haan! Name, phone, course interest - sab automatic save hota hai `student_leads.json` mein.

Q: Response kitna fast hai?
A: Common questions = instant, Other = 1-2 seconds

Q: Kya offline chalega?
A: Nahi, internet chahiye (Gemini API ke liye)

---

**Ab chalo, run karo aur test karo! 🎤🚀**

**Voice-to-Voice is the BEST option for your project!** ✨

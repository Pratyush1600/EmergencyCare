"""EmergencyCare 360 AI Voice & Health Assistant Knowledge Engine.

Provides warm, human conversational explanations and first-aid cure recommendations
for patient questions about:
1. Common & acute health issues (fever, headache, stomach ache, acidity, cough, cuts, burns, sprains, etc.)
2. Hospital services (emergency registration, triage priority, status tracking, departments, wait times)
3. Spoken aloud via ElevenLabs voice synthesis in English and Hindi.
"""
import os
import re
import requests

def _match_keyword(keyword, text):
    """Accurately match word/phrase to avoid false positive substring overlaps."""
    k = keyword.strip().lower()
    t = text.lower()
    if re.search(r"[\u0900-\u097F]", k):
        return k in t
    # For ASCII, ensure word boundaries
    pattern = r"(?<![a-zA-Z0-9])" + re.escape(k) + r"(?![a-zA-Z0-9])"
    return bool(re.search(pattern, t))


EMERGENCY_RED_FLAGS = [
    "chest pain", "heart attack", "can't breathe", "cannot breathe", "breathless",
    "heavy bleeding", "severe bleeding", "unconscious", "stroke", "seizure",
    "collapsed", "poisoning", "anaphylaxis",
    "सीने में दर्द", "सांस नहीं आ रही", "भारी खून", "बेहोश", "दौरा", "आपातकाल", "जहर"
]

HOSPITAL_REGISTRATION_KEYWORDS = [
    "register", "registration", "how to register", "form", "signup", "sign up", "sign in",
    "document", "report", "upload", "पंजीकरण", "रजिस्टर", "फॉर्म", "रिपोर्ट"
]

HOSPITAL_PRIORITY_KEYWORDS = [
    "priority", "triage", "who decides", "urgency", "how long", "doctor decides",
    "wait", "waiting time", "queue", "प्राथमिकता", "ट्राइएज", "डॉक्टर", "इंतजार", "समय"
]

HOSPITAL_STATUS_KEYWORDS = [
    "my status", "meaning of status", "timeline", "update", "assessment",
    "treatment", "discharged", "स्थिति", "अपडेट", "जांच", "इलाज", "छुट्टी"
]

HOSPITAL_FAMILY_KEYWORDS = [
    "family", "relative", "kin", "share", "sharing", "consent", "privacy",
    "परिवार", "रिश्तेदार", "साझा", "गोपनीयता"
]

HOSPITAL_DEPARTMENT_KEYWORDS = [
    "department", "ward", "bed", "cardiology", "pediatrics", "surgery", "neurology",
    "icu", "room", "विभाग", "वार्ड", "बिस्तर", "कमरा"
]

# Comprehensive Health Issues & Cures Database
HEALTH_CURES = [
    {
        "id": "fever",
        "keywords": [
            "fever", "temperature", "chills", "shivering", "viral fever", "typhoid", "dengue",
            "bukhar", "tapman", "बुखार", "तापमान", "ठंड लगना"
        ],
        "en": (
            "For fever: 1. Rest in a well-ventilated room and drink plenty of fluids like water, coconut water, or ORS. "
            "2. Apply a lukewarm damp cloth or cold sponge to your forehead and wrists. "
            "3. Over-the-counter Paracetamol (500mg-650mg) can help lower body temperature every 6 to 8 hours if you have no contraindications. "
            "4. Warning: Seek emergency medical care if fever exceeds 103°F (39.4°C), persists for more than 3 days, or is accompanied by stiff neck, rash, or breathing difficulty."
        ),
        "hi": (
            "बुखार के लिए उपचार: 1. हवादार कमरे में आराम करें और पर्याप्त पानी, ओआरएस (ORS) या नारियल पानी पिएं। "
            "2. माथे और गर्दन पर सामान्य पानी की ठंडी पट्टी रखें। "
            "3. बुखार कम करने के लिए पैरासिटामोल (500mg) ली जा सकती है (एलर्जी न होने पर)। "
            "4. चेतावनी: यदि बुखार 103°F से अधिक हो, 3 दिन से ज्यादा रहे, या गर्दन में अकड़न व सांस की तकलीफ हो, तो तुरंत आपातकालीन डॉक्टर को दिखाएं।"
        )
    },
    {
        "id": "headache",
        "keywords": [
            "headache", "head ache", "migraine", "head pain", "tension headache", "sinus headache",
            "sirdard", "sir dard", "sar dard", "सिरदर्द", "सिर दर्द", "माइग्रेन"
        ],
        "en": (
            "For headache and migraine: 1. Rest in a quiet, darkened room and avoid screen glare. "
            "2. Drink 1-2 large glasses of water, as dehydration is a very common trigger. "
            "3. Apply a cold gel pack to your forehead or temples for throbbing pain, or a warm compress to the back of your neck. "
            "4. Mild pain relievers such as Paracetamol or Ibuprofen may provide relief. "
            "5. Warning: If the headache is sudden and explosively severe ('thunderclap'), or accompanied by vision loss, weakness, or vomiting, go to emergency immediately."
        ),
        "hi": (
            "सिरदर्द और माइग्रेन के उपाय: 1. शांत व अंधेरे कमरे में आराम करें और मोबाइल-टीवी स्क्रीन से दूर रहें। "
            "2. भरपूर पानी पिएं क्योंकि पानी की कमी अक्सर सिरदर्द की वजह बनती है। "
            "3. माथे पर ठंडी सिकाई या गर्दन के पीछे हल्की गर्म सिकाई करें। "
            "4. आवश्यकता पड़ने पर पैरासिटामोल ले सकते हैं। "
            "5. चेतावनी: यदि अचानक अत्यधिक तेज सिरदर्द हो, चक्कर आए, दृष्टि धुंधली हो या उल्टी हो, तो तुरंत अस्पताल पहुंचें।"
        )
    },
    {
        "id": "stomach_pain",
        "keywords": [
            "stomach pain", "stomach ache", "belly pain", "abdominal pain", "cramp", "cramps",
            "pet dard", "pet me dard", "pet dukh raha", "पेट दर्द", "मरोड़", "पेट में दर्द"
        ],
        "en": (
            "For stomach pain: 1. Rest in a comfortable position and place a warm heating pad or hot water bottle on your abdomen. "
            "2. Sip warm ginger, chamomile, or peppermint tea; avoid solid food for 2 hours. "
            "3. Steer clear of oily, fried, spicy foods, caffeine, and dairy products. "
            "4. For spasmodic cramping, mild antispasmodics or carminative fluids can help. "
            "5. Warning: If the pain is sharp and localized in the lower right abdomen (possible appendicitis), or accompanied by vomiting blood, high fever, or inability to pass gas, seek immediate emergency care."
        ),
        "hi": (
            "पेट दर्द के उपचार: 1. आरामदायक स्थिति में लेटें और पेट पर गर्म पानी की थैली से सिकाई करें। 2. गुनगुना अदरक का पानी या सौंफ का पानी पिएं। 3. तला-भुना, मसालेदार भोजन और दूध से कुछ समय परहेज करें। 4. चेतावनी: यदि पेट के निचले दाहिने हिस्से में तेज चुभने वाला दर्द हो, उल्टी में खून आए या पेट बहुत सख्त लगे, तो बिना देर किए इमरजेंसी में जाएं।"
        )
    },
    {
        "id": "acidity",
        "keywords": [
            "acidity", "heartburn", "acid reflux", "gerd", "gas", "bloating", "indigestion", "gastric", "sour burp",
            "khatti dakar", "seene me jalan", "pet me gas", "एसिडिटी", "गैस", "सीने में जलन", "खट्टी डकार", "अपच"
        ],
        "en": (
            "For acidity, heartburn, and gas: 1. Drink a glass of cold milk, coconut water, or warm fennel (saunf) water to neutralize stomach acid. "
            "2. Take an over-the-counter antacid suspension (such as Gelusil or Digene) or an H2 blocker/PPI for rapid relief. "
            "3. Avoid lying flat immediately after eating; elevate your head with a pillow and take a gentle 10-minute walk. "
            "4. Cut out citrus, tomatoes, garlic, chili, carbonated drinks, and smoking. "
            "5. Warning: If severe chest burning radiates to your left arm or jaw with cold sweats, treat it as a cardiac emergency and call 112."
        ),
        "hi": (
            "एसिडिटी और गैस के उपाय: 1. ठंडा दूध, नारियल पानी या सौंफ का गुनगुना पानी पिएं, यह एसिड को शांत करता है। 2. राहत के लिए कोई एंटासिड सिरप या गोली ले सकते हैं। 3. खाने के तुरंत बाद न लेटें, सिर ऊंचा रखें। 4. मिर्च-मसाले, चाय-कॉफ़ी और कोल्ड ड्रिंक्स से बचें। 5. चेतावनी: यदि सीने की जलन बाएं हाथ या जबड़े तक फैले और पसीना आए, तो तुरंत इमरजेंसी जांच कराएं।"
        )
    },
    {
        "id": "cough_cold",
        "keywords": [
            "cough", "sore throat", "cold", "runny nose", "congestion", "sneezing", "phlegm", "flu",
            "khansi", "kharash", "gale me kharash", "jukam", "sardi", "gala dard", "खांसी", "जुकाम", "सर्दी", "गले में खराश", "कफ", "छींक"
        ],
        "en": (
            "For cough, cold, and sore throat: 1. Gargle with warm salt water (1/2 tsp salt in warm water) 3 to 4 times daily to reduce throat inflammation. "
            "2. Drink warm honey with ginger juice or warm turmeric milk to coat and soothe the throat (avoid honey for infants under 1 year). "
            "3. Do steam inhalation twice a day to loosen chest mucus and open blocked nasal passages. "
            "4. Use saline nasal sprays for congestion and OTC throat lozenges for irritation. "
            "5. Warning: Consult a doctor if cough lasts more than 2 weeks, brings up blood, or causes shortness of breath or high fever."
        ),
        "hi": (
            "खांसी, सर्दी और गले की खराश के उपाय: 1. गुनगुने नमक के पानी से दिन में 3-4 बार गरारे करें। 2. अदरक का रस शहद के साथ या गर्म हल्दी वाला दूध पिएं। 3. दिन में दो बार भाप (Steam) लें जिससे बंद नाक और बलगम साफ होगा। 4. गले की खराश के लिए कफ ड्रॉप्स लें। 5. चेतावनी: यदि खांसी 2 हफ्ते से ज्यादा रहे, खून आए या सांस फूले, तो तुरंत डॉक्टर से संपर्क करें।"
        )
    },
    {
        "id": "vomiting_nausea",
        "keywords": [
            "vomit", "vomiting", "nausea", "motion sickness", "food poisoning", "feeling sick",
            "ulti", "mitli", "ji michlana", "उल्टी", "मतली", "जी मिचलाना"
        ],
        "en": (
            "For vomiting and nausea: 1. Let your stomach rest for 30 minutes after vomiting; do not drink or eat right away. "
            "2. Sip small quantities of oral rehydration solution (ORS), clear electrolyte water, or lemon-ginger water very slowly. "
            "3. Once nausea subsides, stick to the bland BRAT diet: bananas, white rice, applesauce, and toast. "
            "4. Smell fresh lemon or chew a small piece of ginger to naturally calm stomach nerves. "
            "5. Warning: Visit the emergency room if you cannot retain fluids for more than 12 hours, feel severe dizziness, or vomit dark blood."
        ),
        "hi": (
            "उल्टी और जी मिचलाने के उपाय: 1. उल्टी के तुरंत बाद कुछ न खाएं-पिएं, पेट को 30 मिनट आराम दें। 2. उसके बाद ORS का घोल, नींबू पानी या इलेक्ट्रोलाइट घूंट-घूंट करके पिएं। 3. उल्टी रुकने पर हल्का भोजन जैसे केला, खिचड़ी या टोस्ट खाएं। 4. नींबू सूंघना या अदरक चबाना राहत देता है। 5. चेतावनी: यदि 12 घंटे से उल्टी न रुके या चक्कर व अत्यधिक कमजोरी हो, तो तुरंत अस्पताल आएं।"
        )
    },
    {
        "id": "diarrhea",
        "keywords": [
            "diarrhea", "loose motion", "loose motions", "watery stool", "stomach upset",
            "dast", "pet kharab", "दस्त", "लूज मोशन", "पेट खराब"
        ],
        "en": (
            "For diarrhea and loose motions: 1. Prevention of dehydration is critical: Drink one glass of WHO-formula ORS solution, tender coconut water, or salted buttermilk after every loose stool. "
            "2. Eat binding, easily digestible foods like curd rice (probiotics), boiled potatoes, oats, and bananas. "
            "3. Avoid dairy milk, sugary drinks, alcohol, greasy foods, and caffeine. "
            "4. Zinc supplementation and probiotics help restore gut barrier function. "
            "5. Warning: Seek emergency care if there is blood in your stool, high fever, sunken eyes, dry mouth, or severe abdominal cramping."
        ),
        "hi": (
            "दस्त (लूज मोशन) के उपाय: 1. सबसे जरूरी है डिहाइड्रेशन रोकना: हर बार दस्त के बाद एक गिलास ORS घोल, नारियल पानी या मट्ठा पिएं। 2. दही-चावल, केला और उबले आलू जैसे हल्के सुपाच्य भोजन लें। 3. दूध, मीठे पेय और तले-भुने खाने से बचें। 4. प्रोबायोटिक्स आंतों को जल्दी ठीक करते हैं। 5. चेतावनी: यदि दस्त में खून आए, तेज बुखार हो या अत्यधिक कमजोरी लगे, तो तुरंत डॉक्टर को दिखाएं।"
        )
    },
    {
        "id": "burns",
        "keywords": [
            "burn", "burns", "burned", "hot oil", "scald", "steam burn",
            "jalna", "jalan", "jala", "जलना", "जलन", "जल गया", "फफोला"
        ],
        "en": (
            "For minor superficial burns: 1. Immediately hold the burned area under cool running tap water for 10-15 minutes. Never apply ice, butter, flour, or toothpaste as they damage delicate tissue. "
            "2. Gently apply pure aloe vera gel or a sterile antibiotic burn ointment. "
            "3. Protect the area with a sterile, non-stick gauze bandage loosely wrapped. "
            "4. Take Paracetamol or Ibuprofen for pain relief. Do not pop any blisters. "
            "5. Warning: If the burn covers a large area, looks white or charred, is caused by chemicals/electricity, or affects the face or hands, visit emergency immediately."
        ),
        "hi": (
            "जलने और जलन के प्राथमिक उपचार: 1. जले हुए स्थान पर तुरंत 10-15 मिनट तक नल का बहता सामान्य ठंडा पानी डालें। बर्फ, टूथपेस्ट, मक्खन या आटा बिल्कुल न लगाएं। 2. एलोवेरा जेल या एंटीसेप्टिक बर्न क्रीम लगाएं। 3. साफ सूखी पट्टी से ढीला ढकें। फफोले न फोड़ें। 4. दर्द के लिए पैरासिटामोल ले सकते हैं। 5. चेतावनी: यदि जलन बड़ी हो, त्वचा सफेद या काली पड़ गई हो, या चेहरा व हाथ जले हों, तो तुरंत अस्पताल आएं।"
        )
    },
    {
        "id": "cuts_wounds",
        "keywords": [
            "cut", "cuts", "wound", "scrape", "minor bleeding", "injury",
            "chot", "ghav", "katna", "चोट", "घाव", "कटना", "खून बहना"
        ],
        "en": (
            "For minor cuts, scrapes, and bleeding: 1. Wash your hands, then apply firm, continuous pressure with a sterile gauze or clean cloth for 5 minutes without peeking. "
            "2. Gently rinse the wound under clean running tap water and mild soap around the edge to clear dirt. "
            "3. Apply an antibacterial ointment and protect with a sterile bandage. "
            "4. Verify your Tetanus vaccine status; get a booster within 48 hours if your last shot was over 5-10 years ago. "
            "5. Warning: If bleeding does not stop after 10 minutes of direct pressure, or the wound is gaping wide, deep, or caused by an animal bite, seek emergency medical care."
        ),
        "hi": (
            "चोट और कटने के उपाय: 1. साफ कपड़े या गॉज से घाव पर 5 मिनट लगातार दबाव बनाएं ताकि खून रुक सके। 2. साफ पानी से घाव को धोएं। 3. एंटीसेप्टिक क्रीम लगाएं और साफ पट्टी बांधें। 4. यदि 5 साल से टिटनेस (Tetanus) का टीका नहीं लगा है, तो टीका जरूर लगवाएं। 5. चेतावनी: यदि 10 मिनट दबाने पर भी खून न रुके या घाव बहुत गहरा हो, तो तुरंत टांके लगाने हेतु अस्पताल आएं।"
        )
    },
    {
        "id": "sprain_joint_pain",
        "keywords": [
            "sprain", "strain", "twist", "ankle sprain", "swelling", "joint pain", "knee pain", "muscle cramp",
            "moch", "khinchav", "sujan", "ghutne ka dard", "मोच", "खिंचाव", "जोड़ों का दर्द", "घुटने का दर्द", "सूजन"
        ],
        "en": (
            "For sprains, muscle strains, and joint swelling, follow the R.I.C.E protocol: 1. Rest: Avoid bearing weight on the affected limb. "
            "2. Ice: Apply an ice pack wrapped in a towel for 15-20 minutes every 2 to 3 hours to bring down swelling. "
            "3. Compress: Wrap with a snug elastic crepe bandage (not too tight to restrict blood flow). "
            "4. Elevate: Prop the limb above heart level on pillows while resting. "
            "5. Over-the-counter pain relievers or topical pain gels can reduce discomfort. "
            "6. Warning: If you heard a loud snap, cannot bear any weight at all, or suspect a bone fracture, come to emergency for an X-ray."
        ),
        "hi": (
            "मोच, खिंचाव और जोड़ों के दर्द का उपचार (RICE नियम): 1. आराम (Rest): प्रभावित पैर या हाथ पर जोर न डालें। 2. बर्फ (Ice): कपड़े में लपेटकर 15-20 मिनट बर्फ से सिकाई करें। 3. पट्टी (Compress): क्रेप बैंडेज बांधें (ज्यादा कसकर नहीं)। 4. ऊंचाई (Elevate): अंग को तकिए के सहारे थोड़ा ऊपर रखें। 5. दर्द निवारक जेल लगा सकते हैं। 6. चेतावनी: यदि हड्डी टूटने की आवाज आई हो या पैर बिल्कुल न रखा जा रहा हो, तो तुरंत एक्स-रे हेतु अस्पताल आएं।"
        )
    },
    {
        "id": "back_pain",
        "keywords": [
            "back pain", "lower back pain", "spine", "lumbago",
            "kamar dard", "peeth dard", "कमर दर्द", "पीठ दर्द"
        ],
        "en": (
            "For back pain: 1. Stay gently active; avoid bed rest for longer than 24 hours as light walking speeds recovery. "
            "2. Apply a cold pack for the first 48 hours to minimize acute inflammation, then switch to a warm heating pad. "
            "3. Sleep on a firm mattress on your side with a pillow between your knees, or on your back with a pillow under your knees. "
            "4. Practice gentle pelvic tilts and hamstring stretches. "
            "5. Warning: Seek emergency evaluation if back pain is paired with loss of bowel or bladder control, numbness in the groin, or numbness down both legs."
        ),
        "hi": (
            "कमर और पीठ दर्द के उपाय: 1. ज्यादा देर तक बिस्तर पर न रहें, हल्की चाल-चलन जारी रखें। 2. पहले 48 घंटे ठंडी सिकाई करें, फिर गर्म पानी की थैली से सिकाई करें। 3. सोते समय घुटनों के बीच तकिया रखें जिससे रीढ़ की हड्डी पर दबाव कम हो। 4. दर्द निवारक मलहम लगा सकते हैं। 5. चेतावनी: यदि कमर दर्द के साथ पेशाब पर नियंत्रण खो जाए या पैरों में सुन्नपन आए, तो तुरंत आपातकालीन डॉक्टर को दिखाएं।"
        )
    },
    {
        "id": "toothache",
        "keywords": [
            "toothache", "tooth pain", "teeth pain", "gum pain", "cavity", "swollen gum",
            "dant dard", "dant me dard", "दांत दर्द", "दांत में दर्द", "मसूड़ों में सूजन"
        ],
        "en": (
            "For toothache and gum pain: 1. Rinse your mouth thoroughly with warm salt water (1/2 tsp salt in warm water) to dislodge debris and soothe gums. "
            "2. Apply a drop of clove oil (laung) on a small cotton ball directly to the painful tooth for natural numbing relief. "
            "3. Hold an ice pack wrapped in a cloth against the outside of your cheek for 15 minutes. "
            "4. Over-the-counter Paracetamol or Ibuprofen helps ease the ache. Never place aspirin directly on the gums as it causes chemical burns. "
            "5. Warning: See a dentist promptly, and seek emergency care if you have facial swelling, difficulty swallowing, or fever."
        ),
        "hi": (
            "दांत दर्द के उपाय: 1. गुनगुने नमक के पानी से अच्छी तरह कुल्ला करें। 2. दर्द वाले दांत पर लौंग का तेल या एक लौंग दबाकर रखें, यह प्राकृतिक दर्द निवारक है। 3. गाल के बाहर से बर्फ की सिकाई करें। 4. पैरासिटामोल या दर्द निवारक दवा ले सकते हैं (गोली को दांत पर चिपकाएं नहीं)। 5. चेतावनी: यदि चेहरे पर सूजन आ जाए, तेज बुखार हो या निगलने में परेशानी हो, तो तुरंत डॉक्टर को दिखाएं।"
        )
    },
    {
        "id": "skin_allergy",
        "keywords": [
            "allergy", "rash", "rashes", "itching", "hives", "itchy skin", "insect bite", "bee sting",
            "khujli", "dane", "chhilka", "खुजली", "एलर्जी", "दाने", "कीड़ा काटना"
        ],
        "en": (
            "For skin allergies, rashes, and insect bites: 1. Apply a cool damp compress or calamine lotion to calm itching. "
            "2. An over-the-counter antihistamine (such as Cetirizine 10mg) relieves allergic reactions and hives. "
            "3. Wash the area with mild unscented soap and cool water. Avoid scratching to prevent secondary bacterial infection. "
            "4. Wear loose, 100% cotton clothing. "
            "5. Warning: If the allergy causes swelling of the lips, tongue, or throat, or dizziness and difficulty breathing (anaphylaxis), seek emergency medical care immediately."
        ),
        "hi": (
            "त्वचा एलर्जी, खुजली और कीड़े के काटने के उपाय: 1. प्रभावित जगह पर कैलामाइन लोशन या नारियल तेल लगाएं और ठंडे पानी की पट्टी रखें। 2. खुजली रोकने के लिए डॉक्टर या फार्मासिस्ट की सलाह से एंटीहिस्टामाइन (जैसे सिट्रीज़ीन) ले सकते हैं। 3. खुजलाने से बचें और ढीले सूती कपड़े पहनें। 4. चेतावनी: यदि होंठ, जीभ या गले में सूजन आ जाए या सांस लेने में परेशानी हो, तो तुरंत 112 या आपातकालीन केंद्र पहुंचे।"
        )
    },
    {
        "id": "blood_pressure",
        "keywords": [
            "blood pressure", "high bp", "hypertension", "low bp",
            "bp badhna", "bp ghatna", "बीपी", "ब्लड प्रेशर", "हाई बीपी"
        ],
        "en": (
            "For high blood pressure symptoms: 1. Sit or recline in a quiet, cool room and take slow, deep diaphragmatic breaths for 10 minutes. "
            "2. Drink a glass of water. Strictly avoid salt, pickles, tea, coffee, energy drinks, and tobacco. "
            "3. Check your BP after resting. If you missed your prescribed BP dose, take it as directed by your physician. "
            "4. Warning: If your systolic BP is 180 or higher, or diastolic is 120 or higher, or if you feel chest heaviness, blurry vision, or numbness, this is a hypertensive crisis—go to emergency immediately."
        ),
        "hi": (
            "हाई ब्लड प्रेशर के उपाय: 1. शांत व ठंडे कमरे में आराम से बैठें, 10 मिनट तक गहरी और धीमी सांसें लें। 2. एक गिलास पानी पिएं। नमक, चाय, कॉफ़ी और धूम्रपान से तुरंत बचें। 3. यदि डॉक्टर द्वारा दी गई बीपी की दवा छूट गई हो तो उसे लें। 4. चेतावनी: यदि बीपी 180/120 से ज्यादा हो, या सीने में दर्द, आंखों के आगे धुंधलापन या कमजोरी लगे, तो तुरंत इमरजेंसी में जाएं।"
        )
    },
    {
        "id": "diabetes_sugar",
        "keywords": [
            "sugar", "diabetes", "low sugar", "high sugar", "hypoglycemia",
            "madhumeh", "मधुमेह", "शुगर", "डायबिटीज"
        ],
        "en": (
            "For diabetes and blood sugar issues: 1. Low sugar (hypoglycemia: shakiness, sweating, anxiety): Follow the 15-15 rule—take 15 grams of fast-acting sugar (half glass fruit juice, 3 teaspoons sugar/honey, or 4 glucose sweets). Recheck sugar after 15 minutes. "
            "2. High sugar: Drink plenty of plain water to help flush excess glucose and avoid all carbs and sugary food. "
            "3. Warning: If a person with diabetes becomes drowsy, confused, or loses consciousness, do not force oral food; call emergency immediately."
        ),
        "hi": (
            "डायबिटीज और शुगर की समस्या के उपाय: 1. लो शुगर (कंपकंपी, पसीना, घबराहट): तुरंत 15 ग्राम तेजी से असर करने वाला मीठा लें (आधा गिलास जूस, 3 चम्मच चीनी या शहद)। 15 मिनट बाद दोबारा जांचें। 2. हाई शुगर: पर्याप्त पानी पिएं और मीठा बिल्कुल न खाएं। 3. चेतावनी: यदि मरीज सुस्त होने लगे, बेहोश हो या बात न समझ पा रहा हो, तो तुरंत अस्पताल ले जाएं।"
        )
    },
    {
        "id": "constipation",
        "keywords": [
            "constipation", "constipated", "hard stool", "piles", "hemorrhoids",
            "kabz", "bawasir", "कब्ज", "बवासीर"
        ],
        "en": (
            "For constipation: 1. Drink 8-10 glasses of water daily and have a cup of warm water or prune juice in the morning. "
            "2. Increase dietary fiber with whole grains, papaya, apples, flaxseeds, and leafy greens. "
            "3. Isabgol (psyllium husk) mixed in warm water or milk at bedtime is a gentle natural laxative. "
            "4. Walk for 20-30 minutes daily to stimulate natural bowel movement. "
            "5. Warning: If constipation is accompanied by severe abdominal pain, vomiting, or rectal bleeding, consult an emergency clinician."
        ),
        "hi": (
            "कब्ज के उपाय: 1. दिन में 8-10 गिलास पानी पिएं और सुबह खाली पेट गुनगुना पानी पिएं। 2. फाइबर युक्त आहार लें जैसे पपीता, सेब, हरी सब्जियां और दलिया। 3. रात को सोने से पहले गुनगुने दूध या पानी में ईसबगोल की भूसी लें। 4. रोजाना 20-30 मिनट टहलें। 5. चेतावनी: यदि कब्ज के साथ बहुत तेज पेट दर्द, उल्टी या शौच में खून आए, तो तुरंत डॉक्टर से सलाह लें।"
        )
    },
    {
        "id": "eye_strain",
        "keywords": [
            "eye pain", "eye strain", "red eye", "red eyes", "conjunctivitis", "pink eye", "dry eyes",
            "aankh me dard", "aankh lal", "आंख में दर्द", "आंख लाल", "आंख आना"
        ],
        "en": (
            "For eye strain, redness, and conjunctivitis: 1. Follow the 20-20-20 rule: every 20 minutes of screen time, look 20 feet away for 20 seconds. "
            "2. Place a clean, cool compress over closed eyes for 10 minutes to soothe inflammation. "
            "3. Use preservative-free lubricating artificial tear drops. "
            "4. Never rub your eyes and wash hands frequently to stop infections from spreading. "
            "5. Warning: If you experience sharp eye pain, light sensitivity, changes in vision, or chemical contact, seek emergency eye care immediately."
        ),
        "hi": (
            "आंखों में दर्द, लाली और थकान के उपाय: 1. स्क्रीन से ब्रेक लें और 20-20-20 नियम अपनाएं। 2. बंद आंखों पर साफ ठंडे पानी की पट्टी रखें। 3. लूब्रिकेटिंग आई ड्रॉप्स डालें। 4. आंखों को हाथ से न मलें और बार-बार हाथ धोएं। 5. चेतावनी: यदि नजर में धुंधलापन आए, असहनीय दर्द हो या आंख में केमिकल चला गया हो, तो तुरंत इमरजेंसी डॉक्टर को दिखाएं।"
        )
    },
    {
        "id": "dehydration_heat",
        "keywords": [
            "dehydration", "heat stroke", "heat exhaustion", "sun stroke", "thirst",
            "lu lagna", "pani ki kami", "garmi lagna", "लू लगना", "पानी की कमी", "गर्मी"
        ],
        "en": (
            "For dehydration and heat exhaustion: 1. Move to a cool, shaded or air-conditioned area immediately. "
            "2. Sip cool water, coconut water, or ORS electrolyte drink slowly. "
            "3. Loosen tight clothing and apply cool, damp cloths to your neck, armpits, and groin. "
            "4. Rest and avoid physical exertion. "
            "5. Warning: If body temperature exceeds 104°F, skin is dry without sweating, or confusion occurs (Heat Stroke), call 112 immediately—this is life-threatening."
        ),
        "hi": (
            "लू और डिहाइड्रेशन के उपाय: 1. तुरंत किसी ठंडी या छायादार जगह पर जाएं। 2. धीरे-धीरे ORS घोल, नारियल पानी या नींबू पानी पिएं। 3. कपड़े ढीले करें और गर्दन व माथे पर गीले कपड़े से सिकाई करें। 4. आराम करें। 5. चेतावनी: यदि शरीर का तापमान बहुत बढ़ जाए, पसीना आना बंद हो जाए या चक्कर व बेहोशी हो, तो तुरंत 112 या अस्पताल पहुंचें।"
        )
    },
    {
        "id": "dizziness",
        "keywords": [
            "dizzy", "dizziness", "vertigo", "lightheaded", "feeling faint",
            "chakkar", "chakkar aana", "behoshi", "चक्कर", "चक्कर आना", "घूमना"
        ],
        "en": (
            "For dizziness and feeling faint: 1. Sit or lie down immediately to prevent falls and injury. "
            "2. If lying down, elevate your feet slightly to restore blood flow to your brain. "
            "3. Drink a glass of water or electrolyte solution, as low hydration or low blood sugar is often responsible. "
            "4. Stand up slowly from sitting or lying positions. "
            "5. Warning: If dizziness is accompanied by chest pain, difficulty speaking, facial drooping, or weakness on one side of your body, call 112 for stroke evaluation."
        ),
        "hi": (
            "चक्कर आने और कमजोरी के उपाय: 1. गिरने से बचने के लिए तुरंत बैठ या लेट जाएं। 2. पैरों को थोड़ा ऊपर उठाकर रखें ताकि मस्तिष्क में रक्त संचार बढ़े। 3. एक गिलास पानी या ओआरएस (ORS) पिएं। 4. धीरे-धीरे उठें, झटके से खड़े न हों। 5. चेतावनी: यदि चक्कर के साथ सीने में दर्द, बोलने में लड़खड़ाहट या एक तरफ की कमजोरी हो, तो तुरंत इमरजेंसी 112 पर कॉल करें।"
        )
    }
]

# Generic health inquiry keywords indicating the user is asking about an illness or cure
HEALTH_QUERY_TRIGGERS = [
    "cure", "treatment", "remedy", "home remedy", "medicine", "how to treat", "how to cure",
    "what to do for", "suffering from", "symptoms", "pain", "relief", "remedies",
    "first aid", "what should i take", "health issue", "prescription",
    "upay", "ilaj", "dawa", "dard",
    "उपाय", "इलाज", "दवा", "घरेलू नुस्खा", "राहत", "दर्द", "निवारण", "बीमारी"
]


def _call_gemini_fallback(query, lang="en"):
    """Optionally query Gemini API if GEMINI_API_KEY is available in the environment."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        prompt = (
            f"You are a clinical AI Health Assistant for EmergencyCare 360 hospital. "
            f"A patient asks: '{query}'. "
            f"Provide a warm, empathetic, practical response in {'Hindi' if lang == 'hi' else 'English'} in under 70 words. "
            f"Include: 1. Practical first aid / home cure steps. 2. Safe hydration / rest tips. "
            f"3. Red-flag warning signs on when to visit the emergency department immediately. "
            f"Do not prescribe regulated drugs."
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = requests.post(url, json=payload, timeout=2.5)
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        pass
    return None


def answer_question(query, lang="en", patient_context=None):
    """Return a warm, human explanatory answer string for health issues or hospital queries."""
    q = (query or "").strip().lower()
    is_hi = lang == "hi" or bool(re.search(r"[\u0900-\u097F]", q))

    # 1. Red-flag critical emergencies first
    if any(_match_keyword(k, q) for k in EMERGENCY_RED_FLAGS) and ("what is" not in q and "meaning" not in q):
        if is_hi:
            return (
                "यदि आपको या आपके किसी परिजन को सीने में गंभीर दर्द, सांस लेने में अत्यधिक तकलीफ, "
                "भारी रक्तस्राव या बेहोशी है, तो कृपया तुरंत नजदीकी इमरजेंसी डेस्क पर स्टाफ को सूचित करें "
                "या 112 पर संपर्क करें। कतार में प्रतीक्षा न करें।"
            )
        return (
            "If you or someone with you is experiencing severe chest pain, shortness of breath, "
            "heavy bleeding, or loss of consciousness, please alert the triage staff at the emergency desk "
            "immediately or call 112. Do not wait in line."
        )

    # 2. Patient-specific live status query
    if patient_context and any(_match_keyword(w, q) for w in ["my status", "where am i", "my bed", "my doctor", "मेरी स्थिति", "मेरा बिस्तर"]):
        name = patient_context.get("name", "Patient")
        status = patient_context.get("status_label", "Under review")
        dept = patient_context.get("dept", "General")
        bed = patient_context.get("bed")
        bed_str = f", Bed {bed}" if bed else ""
        if is_hi:
            return f"नमस्ते {name}। आपकी वर्तमान स्थिति {status} है। आप {dept} विभाग{bed_str} में हैं। अस्पताल के डॉक्टर और नर्स आपकी देखभाल कर रहे हैं।"
        return f"Hello {name}. Your current status is {status}. You are assigned to {dept}{bed_str}. Our clinical team is coordinating your care."

    # 3. Match against comprehensive Health Cures catalog (prioritize specific matches)
    for item in HEALTH_CURES:
        if any(_match_keyword(k, q) for k in item["keywords"]):
            return item["hi"] if is_hi else item["en"]

    # 4. Hospital Registration questions
    if any(_match_keyword(k, q) for k in HOSPITAL_REGISTRATION_KEYWORDS):
        if is_hi:
            return (
                "आपातकालीन पंजीकरण के लिए बस अपना नाम, उम्र, फ़ोन नंबर और लक्षण दर्ज करें। "
                "यदि आपके पास पुरानी मेडिकल रिपोर्ट या पर्ची है, तो आप 3 एमबी तक की पीडीएफ या फोटो भी अपलोड कर सकते हैं। "
                "जमा करने के तुरंत बाद अस्पताल स्टाफ आपकी प्राथमिकता तय करेगा।"
            )
        return (
            "To register, enter your full name, age, phone number, and symptoms. "
            "You can also upload previous medical reports or prescription photos under 3 MB. "
            "Once submitted, our authenticated medical staff will immediately review your case."
        )

    # 5. Triage and Priority questions
    if any(_match_keyword(k, q) for k in HOSPITAL_PRIORITY_KEYWORDS):
        if is_hi:
            return (
                "इमरजेंसी में प्राथमिकता केवल अधिकृत डॉक्टरों और ट्राइएज नर्सों द्वारा मरीज के लक्षणों और वाइटल्स "
                "की गंभीरता के आधार पर तय की जाती है। सबसे गंभीर मरीजों को पहले देखा जाता है। "
                "यदि प्रतीक्षा के दौरान आपकी तकलीफ बढ़े, तो तुरंत स्टाफ को बताएं।"
            )
        return (
            "Clinical priority is determined strictly by authenticated doctors and triage nurses based on "
            "your vital signs and clinical urgency. Patients in critical need are attended to first. "
            "If your condition worsens while waiting, please alert the emergency desk right away."
        )

    # 6. Status & Timeline questions
    if any(_match_keyword(k, q) for k in HOSPITAL_STATUS_KEYWORDS):
        if is_hi:
            return (
                "आपकी स्थिति 'पंजीकृत' से शुरू होकर 'जांच की प्रतीक्षा', 'जांच जारी', 'इलाज जारी' और अंत में 'छुट्टी' में बदलती है। "
                "आप अपने टोकन या आईडी से किसी भी समय अपनी लाइव स्थिति देख सकते हैं।"
            )
        return (
            "Your status progresses through distinct clinical steps: Registered, Waiting for assessment, "
            "Under assessment, Treatment in progress, and Discharged. You can track live updates in real time "
            "using your Patient ID."
        )

    # 7. Family sharing and Privacy questions
    if any(_match_keyword(k, q) for k in HOSPITAL_FAMILY_KEYWORDS):
        if is_hi:
            return (
                "आपकी स्पष्ट सहमति होने पर ही आपका परिवार आपकी स्थिति देख सकता है। "
                "आपकी मेडिकल हिस्ट्री या गुप्त जानकारी कभी साझा नहीं की जाती, केवल वर्तमान स्थिति दिखती है।"
            )
        return (
            "Your family can only view your status if you give explicit consent. "
            "To protect your privacy, only the status level is visible; medical history and clinical details are never shared."
        )

    # 8. Department & Bed questions
    if any(_match_keyword(k, q) for k in HOSPITAL_DEPARTMENT_KEYWORDS):
        if is_hi:
            return (
                "हमारे आपातकालीन केंद्र में कार्डियोलॉजी, बाल रोग, सर्जरी, न्यूरोलॉजी और जनरल वार्ड शामिल हैं। "
                "जांच के बाद डॉक्टर आपको उपयुक्त विभाग और बिस्तर आवंटित करते हैं।"
            )
        return (
            "Our emergency care center features dedicated departments including Cardiology, Pediatrics, "
            "Surgery, Neurology, and General Medicine. The attending clinician assigns you to the appropriate bed after initial assessment."
        )

    # 9. Generic Health Inquiries & Unknown Health questions
    is_health_query = any(_match_keyword(w, q) for w in HEALTH_QUERY_TRIGGERS) or any(_match_keyword(w, q) for w in ["feel", "sick", "pain", "hurt", "cure", "help me", "बीमार", "दर्द"])
    if is_health_query:
        # Try Gemini API if key is present
        gemini_answer = _call_gemini_fallback(query, lang="hi" if is_hi else "en")
        if gemini_answer:
            return gemini_answer

        # Structured general health advice & first-aid fallback
        if is_hi:
            return (
                "आपके स्वास्थ्य लक्षण के लिए प्राथमिक सुझाव: 1. पर्याप्त आराम करें और शरीर को हाइड्रेटेड रखने के लिए पानी, ओआरएस या नारियल पानी पिएं। "
                "2. भारी या तला-भुना खाना टालें और हल्के सुपाच्य आहार लें। 3. प्रभावित हिस्से पर आवश्यकतानुसार ठंडी या गर्म सिकाई करें। "
                "4. चेतावनी: यदि तेज दर्द, उच्च बुखार, सांस की तकलीफ या असामान्य लक्षण महसूस हों, तो तुरंत हमारे अस्पताल में डॉक्टरों से जांच कराएं।"
            )
        return (
            "For your health concern, here is general first-aid guidance: 1. Rest in a comfortable position and stay well hydrated with water or electrolytes. "
            "2. Avoid strenuous physical activity and heavy, oily foods. 3. Apply a warm or cool compress depending on whether it is muscle tension or swelling. "
            "4. Warning: If you experience escalating pain, high fever, shortness of breath, or persistent weakness, please visit our emergency department immediately for an evaluation by a physician."
        )

    # 10. Helpful default response
    if is_hi:
        return (
            "मैं आपका इमरजेंसी केयर 360 AI स्वास्थ्य सहायक हूँ। आप मुझसे किसी भी बीमारी या लक्षण के उपचार (जैसे बुखार, सिरदर्द, पेट दर्द, एसिडिटी, खांसी, चोट) "
            "या अस्पताल की सेवाओं के बारे में पूछ सकते हैं। मैं आपको मानवीय आवाज़ में समझाऊंगा।"
        )
    return (
        "I am your EmergencyCare 360 AI Health Assistant. You can ask me about remedies and cures for health issues "
        "(such as fever, headache, stomach ache, acidity, burns, cough, or sprains), as well as hospital registration and triage. "
        "I will explain the cure in human voice."
    )

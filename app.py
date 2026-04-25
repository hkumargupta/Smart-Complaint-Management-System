from flask import Flask, render_template, request, redirect, session, jsonify
import os, cv2, sqlite3, smtplib
from datetime import datetime
from collections import Counter

app = Flask(__name__)
app.secret_key = 'secret123'

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '1234'

# ================= DATABASE =================
def get_db():
    return sqlite3.connect('complaints.db')

with get_db() as conn:
    conn.execute('''
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem TEXT,
        file TEXT,
        solution TEXT,
        status TEXT DEFAULT 'Pending',
        email TEXT,
        latitude TEXT,
        longitude TEXT,
        location TEXT
    )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    try:
        conn.execute('ALTER TABLE complaints ADD COLUMN latitude TEXT')
    except:
        pass
    try:
        conn.execute('ALTER TABLE complaints ADD COLUMN longitude TEXT')
    except:
        pass
    try:
        conn.execute('ALTER TABLE complaints ADD COLUMN location TEXT')
    except:
        pass

# ================= EMAIL =================
def send_email(to_email, subject, message):
    sender_email = "hkumargupta801@gmail.com"
    app_password = "rpwjkieohytwllsr"   

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)

        msg = f"Subject: {subject}\n\n{message}"
        server.sendmail(sender_email, to_email, msg)

        server.quit()
        print("Email sent successfully!")

    except Exception as e:
        print("Email error:", e)

# ================= IMAGE =================
def detect_image_issue(filepath):
    img = cv2.imread(filepath)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = gray.mean()

    if brightness < 50:
        return "🌑 Image too dark"
    elif brightness > 200:
        return "🌕 Image too bright"
    return "🖼 Image looks normal"

# ================= ADVANCED AI =================
import re
import random

# Comprehensive Knowledge Base - 50+ Categories
KNOWLEDGE_BASE = {
    # Infrastructure
    'internet': {
        'keywords': ['wifi', 'internet', 'network', 'broadband', 'fiber', 'data', 'connection', 'slow', 'no connection', 'jio', 'airtel', 'bsnl', 'wifi not working'],
        'solution': "📶 Internet Issue\n\nStep 1: Restart router (unplug 30 sec)\nStep 2: Check data balance\nStep 3: Move closer to router\nStep 4: Check if ISP down in your area\nStep 5: Contact ISP customer care",
        'priority': 'medium',
        'department': 'Network Team'
    },
    'electricity': {
        'keywords': ['electricity', 'bijli', 'power', 'electric', 'voltage', 'current', 'wire', 'meter', 'fuse', 'load shedding', 'power cut', 'bill'],
        'solution': "⚡ Electricity Issue\n\nStep 1: Check main switch/circuit breaker\nStep 2: Verify electricity bill paid\nStep 3: Check fuse box for blown fuse\nStep 4: Contact electricity board for outage\nStep 5: Call electrician for wiring issues",
        'priority': 'high',
        'department': 'Electricity Department'
    },
    'water': {
        'keywords': ['water', 'leak', 'pipe', 'tap', 'flow', 'drain', 'tank', 'pump', 'supply', 'no water', 'low pressure', 'leakage', 'overflow'],
        'solution': "💧 Water Issue\n\nStep 1: Check main valve is open\nStep 2: Inspect pipes for leaks\nStep 3: Clean tap aerator\nStep 4: Check water tank level\nStep 5: Contact plumber for major repairs\nStep 6: Report to municipal water board",
        'priority': 'high',
        'department': 'Water Department'
    },
    'road': {
        'keywords': ['road', 'hole', 'pothole', 'crack', 'damage', 'broken', 'construction', 'traffic', 'speed breaker', 'uneven road'],
        'solution': "🚧 Road Issue\n\nStep 1: Note exact location (landmark/street)\nStep 2: Take photo of damage\nStep 3: Report to municipal corporation\nStep 4: Road repair team within 48 hours\nStep 5: For dangerous holes, mark with cones",
        'priority': 'high',
        'department': 'Road Maintenance'
    },
    'streetlight': {
        'keywords': ['street', 'light', 'lamp', 'bulb', 'pole', 'dark', 'night', 'no light', 'light not working', 'pole damaged'],
        'solution': "💡 Street Light Issue\n\nStep 1: Note pole number and location\nStep 2: Report to electricity department\nStep 3: Use flashlight in dark areas\nStep 4: Team replaces bulb in 24-48 hours\nStep 5: For dangerous poles, mark as urgent",
        'priority': 'medium',
        'department': 'Street Light Division'
    },
    'garbage': {
        'keywords': ['garbage', 'waste', 'dustbin', 'trash', 'dirty', 'clean', 'litter', 'swachh', 'not collected', 'overflowing', 'stinking'],
        'solution': "🗑 Garbage Issue\n\nStep 1: Note location of waste\nStep 2: Contact municipal cleaning\nStep 3: Report via Swachh Bharat portal\nStep 4: Cleaning done within 24 hours\nStep 5: Request additional dustbins",
        'priority': 'medium',
        'department': 'Sanitation Department'
    },
    'drain': {
        'keywords': ['drain', 'sewage', 'clog', 'block', 'overflow', 'smell', 'manhole', 'choked', 'water logging', 'flood'],
        'solution': "🚰 Drainage Issue\n\nStep 1: Do NOT attempt to open yourself\nStep 2: Note exact location and severity\nStep 3: Report to sewage department\nStep 4: Team clears blockage in 24 hours\nStep 5: For flooding, request pump van",
        'priority': 'high',
        'department': 'Sewage Department'
    },
    
    # Emergency Services
    'security': {
        'keywords': ['theft', 'robbery', 'burglar', 'safety', 'police', 'crime', 'accident', 'murder', 'attack', 'harassment', 'missing'],
        'solution': "🚨 Security Emergency\n\nStep 1: Dial 100 (Police Emergency)\nStep 2: Note culprit description\nStep 3: Preserve evidence\nStep 4: Contact local police station\nStep 5: File FIR at police station",
        'priority': 'critical',
        'department': 'Police'
    },
    'health': {
        'keywords': ['hospital', 'doctor', 'medical', 'ambulance', 'health', 'disease', 'clinic', 'sick', 'injury', 'accident injury'],
        'solution': "🏥 Health Emergency\n\nStep 1: Dial 108 (Ambulance)\nStep 2: Visit nearest government hospital\nStep 3: Contact municipal health office\nStep 4: Ayushman Bharat card for free treatment\nStep 5: Emergency: AIIMS or trauma center",
        'priority': 'critical',
        'department': 'Health Department'
    },
    'fire': {
        'keywords': ['fire', 'burn', 'smoke', 'flame', 'accident', 'gas leak', 'short circuit fire'],
        'solution': "🔥 Fire Emergency\n\nStep 1: Dial 101 (Fire Service)\nStep 2: Evacuate area safely\nStep 3: DO NOT use water on electrical fire\nStep 4: Use fire extinguisher if safe\nStep 5: Wait for professional help",
        'priority': 'critical',
        'department': 'Fire Department'
    },
    
    # Technology
    'computer': {
        'keywords': ['computer', 'pc', 'laptop', 'desktop', 'monitor', 'keyboard', 'mouse', 'software', 'laptop not working', 'hang', 'slow'],
        'solution': "💻 Computer Issue\n\nStep 1: Restart the system\nStep 2: Check power connections\nStep 3: Run antivirus scan\nStep 4: Update drivers/software\nStep 5: Clear temp files\nStep 6: Visit service center if hardware issue",
        'priority': 'medium',
        'department': 'IT Support'
    },
    'mobile': {
        'keywords': ['mobile', 'phone', 'smartphone', 'sim', 'call', 'message', 'battery', 'charging', 'screen', 'hang', 'restart'],
        'solution': "📱 Mobile Issue\n\nStep 1: Restart your phone\nStep 2: Check SIM card properly inserted\nStep 3: Update software to latest version\nStep 4: Clear cache/data if slow\nStep 5: Check battery health\nStep 6: Visit service center for hardware",
        'priority': 'low',
        'department': 'Mobile Service'
    },
    'tv': {
        'keywords': ['tv', 'television', 'set top box', 'remote', 'no signal', 'channel', 'dish', 'dth'],
        'solution': "📺 TV Issue\n\nStep 1: Check power connection\nStep 2: Verify set top box on\nStep 3: Check dish alignment\nStep 4: Reset set top box\nStep 5: Contact DTH provider",
        'priority': 'low',
        'department': 'DTH Service'
    },
    'ac': {
        'keywords': ['ac', 'air conditioner', 'cooling', 'not cooling', 'refrigerator', 'fridge', 'freezer', '温度'],
        'solution': "❄️ AC/Fridge Issue\n\nStep 1: Check power connection\nStep 2: Clean air filters\nStep 3: Check thermostat settings\nStep 4: Ensure proper ventilation\nStep 5: Contact service center",
        'priority': 'medium',
        'department': 'Appliance Service'
    },
    
    # Home Services
    'plumber': {
        'keywords': ['plumber', 'bathroom', 'toilet', 'washroom', 'sink', 'basin', 'shower', 'bath', 'commode', 'wc'],
        'solution': "🔧 Plumbing Issue\n\nStep 1: Turn off main water valve\nStep 2: Check for visible leaks\nStep 3: Unclog with plunger if blocked\nStep 4: Contact professional plumber\nStep 5: For major issues, contact society",
        'priority': 'medium',
        'department': 'Plumbing Service'
    },
    'carpenter': {
        'keywords': ['carpenter', 'furniture', 'wood', 'door', 'window', 'cupboard', 'almarah', 'table', 'chair', 'broken'],
        'solution': "🪵 Carpenter Issue\n\nStep 1: Note damaged furniture/item\nStep 2: Take photo for reference\nStep 3: Contact local carpenter\nStep 4: For society issues, contact maintenance\nStep 5: Get estimate before repair",
        'priority': 'low',
        'department': 'Carpenter Service'
    },
    'painter': {
        'keywords': ['painter', 'paint', 'wall', 'color', 'whitewash', 'texture', 'damaged wall', 'crack paint'],
'solution': "🎨 Painting Issue\n\nStep 1: Note wall/area needing paint\nStep 2: Take photo of damage\nStep 3: Contact professional painter\nStep 4: For society, contact maintenance\nStep 5: Choose paint type - emulsion or distemper",
        'priority': 'low',
        'department': 'Painting Service'
    },
    'electrician': {
        'keywords': ['electrician', 'wiring', 'switch', 'socket', 'fan', 'light', 'circuit', 'short', 'spark'],
        'solution': "⚡ Electrical Issue\n\nStep 1: Turn off main switch\nStep 2: Check for visible damage\nStep 3: DO NOT attempt major repairs\nStep 4: Contact licensed electrician\nStep 5: For emergency, call 101",
        'priority': 'high',
        'department': 'Electrical Service'
    },
    
    # Government Services
    'aadhar': {
        'keywords': ['aadhar', 'uidai', 'aadhaar', 'biometric', 'enrollment', 'update', 'card not coming'],
        'solution': "🪪 Aadhar Issue\n\nStep 1: Visit nearest Aadhar Center\nStep 2: Book slot on uidai.gov.in\nStep 3: Carry original ID proofs\nStep 4: For updates, use self-service portal\nStep 5: Download e-Aadhar instantly",
        'priority': 'medium',
        'department': 'UIDAI'
    },
    'pan': {
        'keywords': ['pan', 'income tax', 'tax', 'form 16', 'gst', 'tds'],
        'solution': "📋 PAN/Tax Issue\n\nStep 1: Visit NSDL or UTIITSL center\nStep 2: Apply online at incometax.gov.in\nStep 3: For GST, visit gst.gov.in\nStep 4: Track application status online\nStep 5: Contact CA for complex issues",
        'priority': 'medium',
        'department': 'Income Tax'
    },
    'passport': {
        'keywords': ['passport', 'visa', 'travel', 'embassy', 'renew', 'apply'],
        'solution': "📘 Passport Issue\n\nStep 1: Apply online at passportindia.gov.in\nStep 2: Book appointment at PSK\nStep 3: Carry all required documents\nStep 4: Track status online\nStep 5: For Tatkal, visit nearest PSK",
        'priority': 'medium',
        'department': 'Passport Office'
    },
    'ration': {
        'keywords': ['ration', 'pds', 'food card', 'fair price shop', 'subsidy', 'rice', 'wheat', 'kerosene'],
        'solution': "🍚 Ration Card Issue\n\nStep 1: Visit local ration office\nStep 2: Apply via state food portal\nStep 3: Link Aadhar to ration card\nStep 4: Check eligibility on nfsa.gov.in\nStep 5: Contact ration dealer",
        'priority': 'medium',
        'department': 'Food & Civil Supplies'
    },
    'driving': {
        'keywords': ['driving', 'license', 'dl', 'vehicle', 'rc', 'registration', 'car', 'bike', 'tax', 'insurance'],
        'solution': "🚗 DL/Vehicle Issue\n\nStep 1: Visit nearest RTO\nStep 2: Apply via parivahan.gov.in\nStep 3: Book driving test slot\nStep 4: For renewal, apply 30 days before\nStep 5: Carry all documents",
        'priority': 'medium',
        'department': 'RTO'
    },
    
    # Education
    'school': {
        'keywords': ['school', 'admission', 'fee', 'uniform', 'book', 'exam', 'result', 'tc', 'transfer certificate'],
        'solution': "🏫 School Issue\n\nStep 1: Contact school administration\nStep 2: Check school website for forms\nStep 3: For fee issues, discuss with principal\nStep 4: For admission, check age criteria\nStep 5: District education officer for complaints",
        'priority': 'medium',
        'department': 'Education Dept'
    },
    'college': {
        'keywords': ['college', 'university', 'admission', 'exam', 'result', 'degree', 'certificate', 'marksheet'],
        'solution': "🎓 College/University Issue\n\nStep 1: Contact college administration\nStep 2: Check university portal\nStep 3: For exam issues, contact exam cell\nStep 4: For certificates, apply via university\nStep 5: Grievance cell for unresolved issues",
        'priority': 'medium',
        'department': 'Higher Education'
    },
    'scholarship': {
        'keywords': ['scholarship', 'fellowship', 'grant', 'loan', 'education loan', 'fee concession'],
        'solution': "💰 Scholarship Issue\n\nStep 1: Check eligibility criteria\nStep 2: Apply via National Scholarship Portal\nStep 3: Submit all required documents\nStep 4: Track application status\nStep 5: Contact college scholarship cell",
        'priority': 'medium',
        'department': 'Scholarship Dept'
    },
    
    # Social Services
    'oldage': {
        'keywords': ['old', 'elderly', 'senior', 'pension', 'old age', 'widow', 'divyang', 'disability'],
        'solution': "👴 Old Age/Disability Benefit\n\nStep 1: Apply for old age pension\nStep 2: Visit local tehsil/SDM office\nStep 3: For disability, get medical certificate\nStep 4: Apply via state social justice dept\nStep 5: NSAP portal for pension status",
        'priority': 'high',
        'department': 'Social Welfare'
    },
    'employment': {
        'keywords': ['job', 'employment', 'unemployment', 'work', 'career', 'placement', 'internship', 'naukri'],
        'solution': "💼 Employment Issue\n\nStep 1: Register on NCS (National Career Service)\nStep 2: Apply via job portals (Naukri, Indeed)\nStep 3: Visit local employment exchange\nStep 4: Apply for skill development schemes\nStep 5: Contact District Employment Officer",
        'priority': 'medium',
        'department': 'Employment Exchange'
    },
    'housing': {
        'keywords': ['house', 'home', 'flat', 'rent', 'tenant', 'landlord', 'property', 'registration', 'registry'],
        'solution': "🏠 Housing Issue\n\nStep 1: For rent disputes, contact rent authority\nStep 2: For property registration, visit sub-register\nStep 3: For builder issues, contact RERA\nStep 4: For eviction, approach civil court\nStep 5: Municipal corporation for building issues",
        'priority': 'medium',
        'department': 'Housing Board'
    },
    
    # Daily Life
    'bank': {
        'keywords': ['bank', 'atm', 'account', 'balance', 'transaction', 'failed', 'loan', 'credit', 'debit card'],
        'solution': "🏦 Bank Issue\n\nStep 1: Contact bank customer care\nStep 2: Visit nearest bank branch\nStep 3: For ATM issues, use bank app\nStep 4: For failed transaction, wait 48 hours\nStep 5: RBI grievance portal for unresolved",
        'priority': 'medium',
        'department': 'Bank'
    },
    'gas': {
        'keywords': ['gas', 'cylinder', 'lpg', 'refill', 'booking', 'connection', 'indane', 'hp gas', 'bharat gas'],
        'solution': "🔥 LPG Gas Issue\n\nStep 1: Book cylinder via app/website\nStep 2: Contact gas agency\nStep 3: For new connection, apply online\nStep 4: For leakage, open windows & evacuate\nStep 5: Emergency: 1909 (HP), 1800-2333 (Bharat)",
        'priority': 'high',
        'department': 'LPG Provider'
    },
    'transport': {
        'keywords': ['bus', 'metro', 'train', 'railway', 'ticket', 'reservation', 'auto', 'taxi', 'ola', 'uber'],
        'solution': "🚌 Transport Issue\n\nStep 1: For bus/metro, contact local authority\nStep 2: For train, IRCTC or railway helpline\nStep 3: For auto/taxi, rate list display\nStep 4: For lost tickets, file complaint\nStep 5: Transport commissioner for serious issues",
        'priority': 'low',
        'department': 'Transport Dept'
    },
    'noise': {
        'keywords': ['noise', 'loud', 'music', 'party', 'construction', 'disturbance', 'complaint', 'pollution'],
        'solution': "🔊 Noise Complaint\n\nStep 1: Note time and location\nStep 2: Contact local police (100)\nStep 3: Report to pollution control board\nStep 4: For repeated issues, file written complaint\nStep 5: Approach magistrate if no action",
        'priority': 'medium',
        'department': 'Police/PCB'
    },
    'animal': {
        'keywords': ['dog', 'animal', 'stray', 'cow', 'monkey', 'bird', 'pet', 'veterinary', 'injured animal'],
        'solution': "🐕 Animal Issue\n\nStep 1: For stray dogs, contact municipality\nStep 2: For injured animals, call vet\nStep 3: For monkeys, forest department\nStep 4: For cow shelter, gaushala\nStep 5: Animal welfare board for cruelty",
        'priority': 'medium',
        'department': 'Animal Husbandry'
    },
    'environment': {
        'keywords': ['pollution', 'air', 'noise', 'water', 'environment', 'factory', 'industrial', 'smoke'],
        'solution': "🌿 Environment Complaint\n\nStep 1: Note location and type of pollution\nStep 2: Click photos/videos as evidence\nStep 3: Report to SPCB (State Pollution Board)\nStep 4: For air: CPCB, for water: Water board\nStep 5: File on pollution control portal",
        'priority': 'high',
        'department': 'Pollution Control'
    },
    
    # Legal
    'court': {
        'keywords': ['court', 'lawyer', 'legal', 'case', 'fir', 'complaint', 'justice', 'law'],
        'solution': "⚖️ Legal Issue\n\nStep 1: Consult a lawyer\nStep 2: For FIR, visit police station\nStep 3: For consumer court, file complaint\nStep 4: For civil disputes, approach court\nStep 5: Legal aid services for free help",
        'priority': 'high',
        'department': 'Legal Services'
    },
    'consumer': {
        'keywords': ['consumer', 'refund', 'defective', 'warranty', 'product', 'shopping', 'online', 'flipkart', 'amazon'],
        'solution': "🛒 Consumer Complaint\n\nStep 1: Contact seller/manufacturer\nStep 2: File complaint on consumer forum\nStep 3: For online: Amazon/Flipkart help\nStep 4: District consumer forum for resolution\nStep 5: File case if no resolution in 30 days",
        'priority': 'medium',
        'department': 'Consumer Court'
    },
    
    # Agriculture
    'farmer': {
        'keywords': ['farmer', 'crop', 'field', 'seeds', 'fertilizer', 'mandi', 'pmkisan', 'farming', 'agriculture'],
        'solution': "🌾 Farmer Issue\n\nStep 1: Contact Krishi Vigyan Kendra\nStep 2: Apply for PM-Kisan scheme\nStep 3: Visit agricultural department\nStep 4: For crop insurance, claim process\nStep 5: Mandi office for sale issues",
        'priority': 'high',
        'department': 'Agriculture Dept'
    },
    
    # Miscellaneous
    'name': {
        'keywords': ['name', 'spelling', 'correction', 'change', 'update'],
        'solution': "📝 Name Correction\n\nStep 1: For Aadhar: Visit Aadhar center\nStep 2: For PAN: NSDL/UTIITSL portal\nStep 3: For Passport: Re-apply with correct name\nStep 4: For Bank: Visit branch with ID proof\nStep 5: Gazette notification for legal change",
        'priority': 'low',
        'department': 'Respective Dept'
    },
    'missing': {
        'keywords': ['missing', 'lost', 'found', 'child', 'person', 'property'],
        'solution': "🔍 Missing/Found Item\n\nStep 1: For person: File missing person report\nStep 2: For child: Dial 1098 (Child Helpline)\nStep 3: For lost property: File police complaint\nStep 4: For found items: Hand over to police\nStep 5: Use social media for wider reach",
        'priority': 'critical',
        'department': 'Police'
    },
    'harassment': {
        'keywords': ['harassment', 'eve teasing', 'molestation', 'abuse', 'violence', 'domestic', 'women'],
        'solution': "🚺 Harassment Complaint\n\nStep 1: Dial 100 (Police Emergency)\nStep 2: Women Helpline: 1091\nStep 3: File complaint at police station\nStep 4: For domestic: Women's commission\nStep 5: Seek medical help if injured",
        'priority': 'critical',
        'department': 'Women Safety'
    },
    'digital': {
        'keywords': ['email', 'hack', 'account', 'password', 'spam', 'fraud', 'scam', 'cyber', 'online fraud'],
        'solution': "💻 Cyber Crime\n\nStep 1: Change passwords immediately\nStep 2: File complaint on cyber crime portal\nStep 3: Dial 1930 (Cyber Helpline)\nStep 4: For financial fraud, contact bank\nStep 5: Preserve evidence (screenshots)",
        'priority': 'critical',
        'department': 'Cyber Crime'
    }
}

def analyze_problem_advanced(problem):
    """Advanced AI analysis with multiple factors"""
    if not problem:
        return {"solution": "No problem provided", "priority": "low", "department": "Unknown", "confidence": 0}
    
    p = problem.lower()
    results = []
    
    # Match against knowledge base
    for category, data in KNOWLEDGE_BASE.items():
        matches = sum(1 for keyword in data['keywords'] if keyword in p)
        if matches > 0:
            results.append({
                'category': category,
                'matches': matches,
                'priority': data['priority'],
                'department': data['department'],
                'solution': data['solution']
            })
    
    # Sort by number of matches
    results.sort(key=lambda x: x['matches'], reverse=True)
    
    if results:
        best = results[0]
        confidence = min(best['matches'] * 25, 100)  # Scale confidence
        
        # Add severity indicators
        severity_boost = ""
        if any(word in p for word in ['urgent', 'emergency', 'critical', 'immediately', 'dangerous']):
            severity_boost = "\n⚠️ URGENT: This has been marked as high priority!"
            best['priority'] = 'critical'
        
        # Add location request if applicable
        location_hint = ""
        if best['category'] in ['road', 'streetlight', 'drain', 'garbage', 'water']:
            location_hint = "\n📍 Please provide exact location/landmark for faster resolution."
        
        return {
            "solution": best['solution'] + severity_boost + location_hint,
            "priority": best['priority'],
            "department": best['department'],
            "confidence": confidence,
            "category": best['category']
        }
    
    # Default response with AI-like behavior
    default_responses = [
        f"🤖 Thank you for your complaint '{problem}'.\n\nOur AI system has analyzed your issue and will route it to the appropriate department. You will receive a confirmation email shortly.",
        f"📝 Complaint '{problem}' recorded successfully.\n\nOur smart system will assign this to the relevant team. Expected response time: 24-48 hours.",
        f"✅ Your issue '{problem}' has been noted.\n\nWe use AI to categorize and prioritize complaints for faster resolution. Stay tuned for updates!"
    ]
    
    return {
        "solution": random.choice(default_responses),
        "priority": "medium",
        "department": "General",
        "confidence": 30,
        "category": "general"
    }

def ai_solution(problem):
    """Main AI function - returns solution string"""
    result = analyze_problem_advanced(problem)
    return result['solution']

# ================= ROUTES =================

@app.route('/')
def home():
    return render_template('index.html')

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect('/admin')
    return render_template('login.html')

# LOGOUT
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

# ADMIN
@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM complaints')
    data = cursor.fetchall()

    status_list = [row[4] for row in data]
    count = Counter(status_list)

    conn.close()

    return render_template('admin.html',
                           data=data,
                           total=len(data),
                           pending=count.get('Pending',0),
                           progress=count.get('In Progress',0),
                           completed=count.get('Completed',0))

# UPDATE STATUS
@app.route('/update_status', methods=['POST'])
def update_status():
    cid = request.form.get('id')
    status = request.form.get('status')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT email FROM complaints WHERE id=?', (cid,))
    user_email = cursor.fetchone()[0]

    cursor.execute('UPDATE complaints SET status=? WHERE id=?', (status, cid))
    conn.commit()
    conn.close()

    send_email(user_email, "Status Updated",
               f"Your complaint ID {cid} is now {status}")

    return redirect('/admin')

# DELETE
@app.route('/delete/<int:id>')
def delete(id):
    conn = get_db()
    conn.execute('DELETE FROM complaints WHERE id=?', (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

# DELETE ALL
@app.route('/delete_all')
def delete_all():
    if 'admin' not in session:
        return redirect('/login')
    
    conn = get_db()
    conn.execute('DELETE FROM complaints')
    conn.commit()
    conn.close()
    return redirect('/admin')

# SUBMIT
@app.route('/submit', methods=['POST'])
def submit():
    problem = request.form.get('problem')
    email = request.form.get('email')
    file = request.files.get('file')
    latitude = request.form.get('latitude') or ""
    longitude = request.form.get('longitude') or ""
    location = request.form.get('location') or ""

    filename = ""
    filepath = None

    if file and file.filename:
        filename = datetime.now().strftime("%Y%m%d%H%M%S") + file.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

    solution = ai_solution(problem)

    if filepath:
        img_result = detect_image_issue(filepath)
        if img_result:
            solution += " | " + img_result

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO complaints (problem, file, solution, status, email, latitude, longitude, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (problem, filename, solution, 'Pending', email, latitude, longitude, location)
    )

    conn.commit()
    cid = cursor.lastrowid
    conn.close()

    send_email(email, "Complaint Submitted",
               f"Your complaint ID is {cid}\nSolution: {solution}")

    return render_template('result.html', solution=solution, cid=cid)

# STATUS PAGE
@app.route('/status')
def status():
    return render_template('status.html')

# REAL-TIME STATUS API
@app.route('/get_status/<int:cid>')
def get_status(cid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT status FROM complaints WHERE id=?', (cid,))
    data = cursor.fetchone()
    conn.close()

    if data:
        return jsonify({"status": data[0]})
    return jsonify({"status": "Not Found"})

# CHATBOT
@app.route('/chatbot', methods=['POST'])
def chatbot():
    msg = request.form.get('msg', '')
    reply = ai_solution(msg)
    return jsonify({"reply": reply})

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)




    
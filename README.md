# 🥗 AI Calorie Counter

AI Calorie Counter is a full-stack web application that uses AI to identify food items from images and estimate their nutritional content. It features a Python backend for image analysis and a React frontend for user interaction.

---

## 📸 Features

- Upload food images
- AI-powered food recognition using Google Vision API
- Calorie and nutrition estimation
- Clean and responsive UI
- Deployable via Vercel

---

## 🧰 Tech Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, Google Vision API
- **Deployment:** Vercel

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ai-calorie-counter.git
```

### 2. Setup Backend (Python)
```
cd ai-calorie-counter
cd API
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create a .env file inside the API folder:
```
GOOGLE_APPLICATION_CREDENTIALS=client_secret_XXXX.json
```

### 4. Start the backend:

```bash
python analyze-food.py
```

 ### 5. Setup Frontend (React + TypeScript)
 ```bash
cd frontend
npm install
npm run dev
```



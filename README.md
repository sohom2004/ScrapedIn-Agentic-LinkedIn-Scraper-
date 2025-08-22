# ScrapedIn  

ScrapedIn is a LinkedIn scraping tool that allows you to extract data from LinkedIn using either a **CLI interface** or a **Streamlit web UI**.  

---

## 🚀 Requirements  

- **Python**: Works best with versions **below 3.12** (e.g., 3.9–3.11).  
- Install dependencies with:  
  ```bash
  pip install -r requirements.txt
  ```

---

## ⚡ How to Run  

### 1. Clone the repository & install dependencies  
```bash
git clone https://github.com/sohom2004/ScrapedIn-Agentic-LinkedIn-Scraper-.git
cd ScrapedIn
pip install -r requirements.txt
```

### 2. Login to LinkedIn  
Before running the app, you need to authenticate with LinkedIn:  
```bash
python runner.py
```  
- This will open a browser window for you to log in to your LinkedIn account.  
- After successful login, your session will be stored locally for reuse.  

### 3. Run the CLI version  
If you prefer using the command line:  
```bash
python main.py
```

### 4. Run the Streamlit UI version  
If you want a web interface:  
```bash
streamlit run app.py
```  
This will launch a local server and open the app in your browser.  

---

## 📂 Output  

- Scraped results are saved as `.csv` files in the `output.csv` file.  

---

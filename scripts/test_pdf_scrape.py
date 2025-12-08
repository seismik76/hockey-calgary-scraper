import requests
from bs4 import BeautifulSoup
import pdfplumber
import io
import re

def test_pdf_scrape():
    # Tuscany Profile URL
    url = 'https://www.calgary.ca/communities/profiles/tuscany.html'
    print(f'Fetching {url}...')
    
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find PDF link
    pdf_url = None
    for a in soup.find_all('a', href=True):
        if 'pdf' in a['href'] and 'profile' in a.get_text().lower():
            pdf_url = a['href']
            if not pdf_url.startswith('http'):
                pdf_url = 'https://www.calgary.ca' + pdf_url
            break
            
    if not pdf_url:
        print('PDF link not found.')
        return

    print(f'Found PDF: {pdf_url}')
    
    # Download PDF
    pdf_response = requests.get(pdf_url)
    f = io.BytesIO(pdf_response.content)
    
    # Parse PDF
    with pdfplumber.open(f) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if 'Median total income' in text:
                print(f'--- Page {i+1} (Income) ---')
                # Try table extraction
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Look for row with Median total income
                        # Row usually looks like ['Median total income ...', '142,000', '98,000']
                        # Clean None values
                        clean_row = [str(x).replace('\n', ' ').strip() for x in row if x]
                        row_str = ' '.join(clean_row)
                        
                        if 'Median total income' in row_str:
                            print(f'Found Row: {clean_row}')
            
            if 'Population in private households' in text:
                 print(f'--- Page {i+1} (Population) ---')
                 tables = page.extract_tables()
                 for table in tables:
                    for row in table:
                        clean_row = [str(x).replace('\n', ' ').strip() for x in row if x]
                        row_str = ' '.join(clean_row)
                        if 'Population in private households' in row_str:
                             print(f'Found Pop Row: {clean_row}')

if __name__ == '__main__':
    test_pdf_scrape()

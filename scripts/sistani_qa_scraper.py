#!/usr/bin/env python3
"""
Sistani Q&A Scraper
Scrapes questions and answers from Ayatollah Sistani's official Q&A website
Organized by alphabetical topics with proper formatting for PDF conversion
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin
import os
import csv
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SistaniQAScraper:
    def __init__(self, base_url="https://www.sistani.org"):
        self.base_url = base_url
        self.qa_url = f"{base_url}/english/qa/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.scraped_data = []
        self.failed_urls = []

    def get_page_content(self, url, retries=3, delay=2):
        """Fetch page content with retry mechanism and proper error handling"""
        for attempt in range(retries):
            try:
                logger.info(f"Fetching: {url} (attempt {attempt + 1})")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"Unexpected status code {response.status_code} for {url}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.failed_urls.append(url)
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None

    def extract_topics_from_main_page(self, html_content):
        """Extract all topics based on HTML structure from screenshots"""
        soup = BeautifulSoup(html_content, 'html.parser')
        topics = []

        try:
            # Method 1: Look for alphabet letters followed by topic trees
            letter_elements = soup.find_all(['div', 'span'], class_=re.compile(r'.*letter.*'))

            for letter_elem in letter_elements:
                alphabet_text = letter_elem.get_text(strip=True)

                # Skip if not a single letter
                if len(alphabet_text) != 1 or not alphabet_text.isalpha():
                    continue

                # Find associated topic container
                topic_container = self.find_topic_container(letter_elem)

                if topic_container:
                    topic_links = topic_container.find_all('a', href=True)

                    for link in topic_links:
                        topic_info = self.extract_topic_info(link, alphabet_text)
                        if topic_info:
                            topics.append(topic_info)

            # Method 2: Direct search for topic links if Method 1 fails
            if not topics:
                logger.info("Method 1 failed, trying direct link extraction...")
                all_links = soup.find_all('a', href=re.compile(r'/english/qa/\d+/?'))

                for link in all_links:
                    topic_info = self.extract_topic_info(link, 'Unknown')
                    if topic_info:
                        topics.append(topic_info)

        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}")

        logger.info(f"Extracted {len(topics)} topics from main page")
        return topics

    def find_topic_container(self, letter_elem):
        """Find the container holding topic links for a given alphabet"""
        # Try different methods to find the topic container
        containers_to_try = [
            letter_elem.find_next_sibling('div'),
            letter_elem.parent.find('div', class_=re.compile(r'.*tree.*')),
            letter_elem.find_parent().find_next('div'),
        ]

        for container in containers_to_try:
            if container and container.find('a', href=True):
                return container

        return None

    def extract_topic_info(self, link, alphabet):
        """Extract topic information from a link element"""
        try:
            href = link.get('href', '').strip()
            topic_name = link.get_text(strip=True)
            title = link.get('title', '')

            # Skip empty or invalid links
            if not href or not topic_name or len(topic_name) < 2:
                return None

            # Extract question count from title
            question_count = 0
            if title and 'question' in title.lower():
                count_match = re.search(r'(\d+)', title)
                if count_match:
                    question_count = int(count_match.group(1))

            # Build full URL
            if href.startswith('/'):
                full_url = self.base_url + href
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(self.qa_url, href)

            return {
                'alphabet': alphabet,
                'topic_name': topic_name,
                'topic_url': full_url,
                'question_count': question_count,
                'href': href
            }

        except Exception as e:
            logger.error(f"Error extracting topic info: {str(e)}")
            return None

    def extract_qa_from_topic_page(self, topic_url, topic_name):
        """Extract Q&A pairs from a topic page"""
        html_content = self.get_page_content(topic_url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'html.parser')
        qa_pairs = []

        try:
            # Method 1: Look for structured Q&A divs (as seen in screenshot)
            qa_containers = soup.find_all('div', class_=re.compile(r'.*qa.*'))

            for container in qa_containers:
                qa_pair = self.extract_qa_from_container(container, topic_name, topic_url)
                if qa_pair:
                    qa_pairs.append(qa_pair)

            # Method 2: Look for question/answer spans
            if not qa_pairs:
                qa_pairs = self.extract_qa_from_spans(soup, topic_name, topic_url)

            # Method 3: Pattern-based extraction
            if not qa_pairs:
                qa_pairs = self.extract_qa_by_patterns(soup, topic_name, topic_url)

        except Exception as e:
            logger.error(f"Error extracting Q&A from {topic_url}: {str(e)}")

        logger.info(f"Extracted {len(qa_pairs)} Q&A pairs from {topic_name}")
        return qa_pairs

    def extract_qa_from_container(self, container, topic_name, topic_url):
        """Extract Q&A from a structured container"""
        try:
            # Look for question
            question_elem = container.find(['span', 'div'], string=re.compile(r'question:', re.I))
            if not question_elem:
                question_elem = container.find(['span', 'div'], class_=re.compile(r'.*question.*|.*myv.*b.*'))

            # Look for answer
            answer_elem = container.find(['span', 'div'], string=re.compile(r'answer:', re.I))
            if not answer_elem:
                answer_elem = container.find(['span', 'div'], class_=re.compile(r'.*answer.*|.*myv(?!.*b).*'))

            if question_elem and answer_elem:
                question_text = self.clean_text(question_elem.get_text())
                answer_text = self.clean_text(answer_elem.get_text())

                # Remove prefixes
                question_text = re.sub(r'^question:\s*', '', question_text, flags=re.I)
                answer_text = re.sub(r'^answer:\s*', '', answer_text, flags=re.I)

                if question_text and answer_text:
                    return {
                        'question': question_text,
                        'answer': answer_text,
                        'topic': topic_name,
                        'source_url': topic_url,
                        'scraped_at': datetime.now().isoformat()
                    }

        except Exception as e:
            logger.error(f"Error in container extraction: {str(e)}")

        return None

    def extract_qa_from_spans(self, soup, topic_name, topic_url):
        """Extract Q&A from span elements"""
        qa_pairs = []

        try:
            spans = soup.find_all('span', class_=re.compile(r'.*myv.*'))
            current_question = ""

            for span in spans:
                text = self.clean_text(span.get_text())
                span_classes = span.get('class', [])

                # Check if this is a question
                if ('b' in span_classes or 
                    text.lower().startswith('question:') or
                    span.find_parent(attrs={'id': re.compile(r'.*q\d+.*')})):

                    current_question = re.sub(r'^question:\s*', '', text, flags=re.I)

                # Check if this is an answer
                elif (text.lower().startswith('answer:') or
                      ('b' not in span_classes and current_question)):

                    current_answer = re.sub(r'^answer:\s*', '', text, flags=re.I)

                    if current_question and current_answer:
                        qa_pairs.append({
                            'question': current_question,
                            'answer': current_answer,
                            'topic': topic_name,
                            'source_url': topic_url,
                            'scraped_at': datetime.now().isoformat()
                        })
                        current_question = ""

        except Exception as e:
            logger.error(f"Error in span extraction: {str(e)}")

        return qa_pairs

    def extract_qa_by_patterns(self, soup, topic_name, topic_url):
        """Extract Q&A using regex patterns on full text"""
        qa_pairs = []

        try:
            full_text = soup.get_text()

            # Pattern to match Q&A pairs
            qa_pattern = r'question:\s*(.+?)answer:\s*(.+?)(?=question:|$)'
            matches = re.findall(qa_pattern, full_text, re.DOTALL | re.IGNORECASE)

            for question, answer in matches:
                question_clean = self.clean_text(question)
                answer_clean = self.clean_text(answer)

                if question_clean and answer_clean:
                    qa_pairs.append({
                        'question': question_clean,
                        'answer': answer_clean,
                        'topic': topic_name,
                        'source_url': topic_url,
                        'scraped_at': datetime.now().isoformat()
                    })

        except Exception as e:
            logger.error(f"Error in pattern extraction: {str(e)}")

        return qa_pairs

    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""

        # Remove extra whitespace and normalize
        text = ' '.join(text.split())

        # Remove common artifacts
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\r\n\t]+', ' ', text)

        return text.strip()

    def scrape_all_topics(self, max_topics=None, start_from=0):
        """Main scraping function with resume capability"""
        logger.info("Starting Sistani Q&A scraping...")

        # Get main page
        main_content = self.get_page_content(self.qa_url)
        if not main_content:
            logger.error("Failed to fetch main Q&A page")
            return []

        # Extract topics
        topics = self.extract_topics_from_main_page(main_content)
        if not topics:
            logger.error("No topics found on main page")
            return []

        # Apply limits
        if start_from > 0:
            topics = topics[start_from:]
            logger.info(f"Starting from topic {start_from}")

        if max_topics:
            topics = topics[:max_topics]
            logger.info(f"Limited to {max_topics} topics")

        logger.info(f"Processing {len(topics)} topics...")

        # Scrape each topic
        total_scraped = 0
        successful_topics = 0

        for i, topic in enumerate(topics):
            logger.info(f"\n[{i+1}/{len(topics)}] Processing: {topic['topic_name']}")
            logger.info(f"Expected questions: {topic['question_count']}")

            try:
                qa_pairs = self.extract_qa_from_topic_page(topic['topic_url'], topic['topic_name'])

                if qa_pairs:
                    self.scraped_data.extend(qa_pairs)
                    total_scraped += len(qa_pairs)
                    successful_topics += 1
                    logger.info(f"✓ Successfully scraped {len(qa_pairs)} Q&A pairs")
                else:
                    logger.warning(f"✗ No Q&A pairs found for {topic['topic_name']}")

            except Exception as e:
                logger.error(f"✗ Error processing {topic['topic_name']}: {str(e)}")

            # Respectful delay
            time.sleep(1.5)

            # Save progress periodically
            if (i + 1) % 10 == 0:
                self.save_progress()

        # Final summary
        logger.info(f"\n=== Scraping Complete ===")
        logger.info(f"Topics processed: {len(topics)}")
        logger.info(f"Successful topics: {successful_topics}")
        logger.info(f"Total Q&A pairs: {total_scraped}")
        logger.info(f"Failed URLs: {len(self.failed_urls)}")

        return self.scraped_data

    def save_progress(self):
        """Save current progress"""
        if not self.scraped_data:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sistani_qa_progress_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Progress saved: {len(self.scraped_data)} Q&A pairs in {filename}")

    def save_complete_data(self):
        """Save all data in multiple formats"""
        if not self.scraped_data:
            logger.warning("No data to save")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        files_created = {}

        # JSON format
        json_file = f"sistani_qa_complete_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_data, f, ensure_ascii=False, indent=2)
        files_created['json'] = json_file

        # Markdown format (PDF ready)
        md_file = f"sistani_qa_complete_{timestamp}.md"
        self.create_markdown_file(md_file)
        files_created['markdown'] = md_file

        # CSV format
        csv_file = f"sistani_qa_complete_{timestamp}.csv"
        self.create_csv_file(csv_file)
        files_created['csv'] = csv_file

        # Summary file
        summary_file = f"sistani_qa_summary_{timestamp}.txt"
        self.create_summary_file(summary_file)
        files_created['summary'] = summary_file

        logger.info("Data saved in multiple formats:")
        for format_type, filename in files_created.items():
            logger.info(f"  {format_type.upper()}: {filename}")

        return files_created

    def create_markdown_file(self, filename):
        """Create markdown file optimized for PDF conversion"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# Ayatollah Sistani Q&A Collection\n\n")
            f.write(f"*Compiled on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n\n")
            f.write(f"Total Questions: {len(self.scraped_data)}\n\n")
            f.write("---\n\n")

            # Group by topic and sort
            topics_dict = {}
            for qa in self.scraped_data:
                topic = qa['topic']
                if topic not in topics_dict:
                    topics_dict[topic] = []
                topics_dict[topic].append(qa)

            # Write each topic
            for topic_name in sorted(topics_dict.keys()):
                qa_list = topics_dict[topic_name]

                f.write(f"## {topic_name}\n\n")
                f.write(f"*{len(qa_list)} Question{'s' if len(qa_list) != 1 else ''}*\n\n")

                for i, qa in enumerate(qa_list, 1):
                    f.write(f"### Question {i}\n\n")
                    f.write(f"**Q:** {qa['question']}\n\n")
                    f.write(f"**A:** {qa['answer']}\n\n")

                    if i < len(qa_list):
                        f.write("---\n\n")

                f.write("\n\\pagebreak\n\n")  # Page break for PDF

    def create_csv_file(self, filename):
        """Create CSV file for data analysis"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['topic', 'question', 'answer', 'source_url', 'scraped_at']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for qa in self.scraped_data:
                writer.writerow(qa)

    def create_summary_file(self, filename):
        """Create summary statistics file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("SISTANI Q&A SCRAPING SUMMARY\n")
            f.write("="*50 + "\n\n")
            f.write(f"Scraping Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Q&A Pairs: {len(self.scraped_data)}\n")

            # Topic statistics
            topics_count = len(set(qa['topic'] for qa in self.scraped_data))
            f.write(f"Total Topics: {topics_count}\n")
            f.write(f"Average Q&A per Topic: {len(self.scraped_data)/topics_count:.2f}\n\n")

            # Topic breakdown
            topic_stats = {}
            for qa in self.scraped_data:
                topic = qa['topic']
                topic_stats[topic] = topic_stats.get(topic, 0) + 1

            sorted_topics = sorted(topic_stats.items(), key=lambda x: x[1], reverse=True)

            f.write("TOPIC BREAKDOWN:\n")
            f.write("-" * 30 + "\n")
            for topic, count in sorted_topics:
                f.write(f"{topic}: {count} questions\n")

            if self.failed_urls:
                f.write(f"\nFAILED URLS ({len(self.failed_urls)}): \n")
                for url in self.failed_urls:
                    f.write(f"  - {url}\n")


def main():
    """Main execution function"""
    scraper = SistaniQAScraper()

    print("Sistani Q&A Scraper")
    print("==================")
    print("This script will scrape Q&A from Ayatollah Sistani's website")
    print("and save the data in multiple formats suitable for PDF conversion.\n")

    # Get user preferences
    try:
        max_topics = input("Enter max topics to scrape (press Enter for all): ").strip()
        max_topics = int(max_topics) if max_topics else None

        print(f"\nStarting scrape{'with limit of ' + str(max_topics) + ' topics' if max_topics else ' of all topics'}...")

        # Perform scraping
        data = scraper.scrape_all_topics(max_topics=max_topics)

        if data:
            print(f"\nScraping completed! Found {len(data)} Q&A pairs.")

            # Save data
            files = scraper.save_complete_data()

            print("\nFiles created:")
            for format_type, filename in files.items():
                print(f"  - {filename}")

            print(f"\nTo convert Markdown to PDF, use:")
            print(f"pandoc {files['markdown']} -o sistani_qa.pdf")

        else:
            print("No data scraped. Please check the website structure or network connection.")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
        if scraper.scraped_data:
            print("Saving progress...")
            scraper.save_progress()

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        if scraper.scraped_data:
            print("Saving available data...")
            scraper.save_complete_data()


if __name__ == "__main__":
    main()

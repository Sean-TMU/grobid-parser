import os, datetime
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from model.grobid_parse import GrobidParser
from flask import (Flask, request, redirect, render_template, flash,
                    url_for, send_from_directory, session, after_this_request)

app = Flask(__name__)
app.secret_key = os.urandom(12)

STATIC_FOLDER = os.environ.get('STATIC_FOLDER')
ALLOWED_EXTENSIONS = set(['pdf'])

# Check file format
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.')[-1] in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET','POST'])
def mainpage():
    if request.method == 'GET':
        os.makedirs(STATIC_FOLDER, exist_ok=True)
        if request.headers.get('Cache-Control') == 'max-age=0':
            session.clear()
            # Clear any cached files
            for file in os.listdir(STATIC_FOLDER):
                try:
                    os.remove(os.path.join(STATIC_FOLDER, file))
                except:
                    pass
        return render_template('index.html')
    
    # If user uploads a PDF file, parse it and return the results
    if request.method == 'POST':
        file = request.files['file']
        if not file or not allowed_file(file.filename):
            flash("Please upload a valid PDF file", 'danger')
            return render_template('index.html')
        
        if file and allowed_file(file.filename):
            # Use current time as file name
            now = datetime.datetime.now()
            currentTime = now.strftime("%Y-%m-%d_%H-%M-%S")
            filepath = os.path.join(STATIC_FOLDER, f"{currentTime}.pdf")
            file.save(filepath)

            # Call GROBID service
            grobid_parser = GrobidParser()
            grobid_parser.logger.info(f"Processing {currentTime}.pdf")
            result = grobid_parser.parse_pdf(STATIC_FOLDER, f"{currentTime}.pdf")
            if isinstance(result, dict):
                grobid_parser.logger.info(f"Successfully parsed {currentTime}.pdf")
                df = pd.DataFrame(result)
                output_path = f"{STATIC_FOLDER}/{currentTime}_results.csv"
                df.to_csv(output_path)

                if os.path.exists(output_path):
                    grobid_parser.logger.info(f"Parsed results saved to {output_path}")
                    os.remove(filepath)
                    os.remove(f"{STATIC_FOLDER}/{currentTime}.grobid.tei.xml")
                    # Store results in session
                    session['result'] = result
                    session['csv_filename'] = f"{currentTime}_results.csv"
                    flash("Success", 'success')
                    return render_template('index.html')
                else:
                    grobid_parser.logger.error(f"Failed to export parse result")
                    flash("Failed to export parsed result", 'danger')
                    return render_template('index.html')
            else:
                grobid_parser.logger.error(f"Failed to parse {currentTime}.pdf")
                flash(f"Failed to parse this file", 'danger')
                return render_template('index.html')

# Route for downloading the CSV file
@app.route('/download/<filename>')
def download_file(filename):
    try:
        return_value = send_from_directory(STATIC_FOLDER, filename, as_attachment=True)
        # Remove the file after sending it
        @after_this_request
        def remove_file(response):
            try:
                os.remove(os.path.join(STATIC_FOLDER, filename))
            except Exception as error:
                print("Error removing file: %s", error)
            return response
        return return_value
    except Exception as e:
        flash("Error downloading file", 'danger')
        return redirect(url_for("mainpage"))

if __name__ == '__main__':
    app.run()
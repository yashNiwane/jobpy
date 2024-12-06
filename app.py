from flask import Flask, request, jsonify, render_template
from jobspy import scrape_jobs
import csv
from io import StringIO
import traceback
import pandas as pd

app = Flask(__name__)

def process_jobs_data(jobs_df):
    if jobs_df is None or jobs_df.empty:
        return None
    
    # Select only the important columns
    important_columns = [
        'title', 'company', 'location', 'date_posted', 'job_type',
        'salary_source', 'interval', 'min_amount', 'max_amount', 'currency',
        'is_remote', 'job_url'
    ]
    
    # Filter the DataFrame to keep only the important columns
    filtered_df = jobs_df[important_columns].copy()
    
    # Format salary information
    filtered_df['salary'] = filtered_df.apply(
        lambda row: f"{row['currency']} {row['min_amount']} - {row['max_amount']} per {row['interval']}"
        if pd.notnull(row['min_amount']) and pd.notnull(row['max_amount'])
        else "Not specified",
        axis=1
    )
    
    # Drop individual salary columns
    filtered_df = filtered_df.drop(['salary_source', 'interval', 'min_amount', 'max_amount', 'currency'], axis=1)
    
    # Rename columns for clarity
    filtered_df = filtered_df.rename(columns={
        'date_posted': 'date',
        'is_remote': 'remote'
    })
    
    # Convert boolean 'remote' to Yes/No
    filtered_df['remote'] = filtered_df['remote'].map({True: 'Yes', False: 'No'})
    
    return filtered_df

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            data = request.form
            
            jobs = scrape_jobs(
                site_name=data.getlist('site_name') or ["indeed", "linkedin", "glassdoor"],
                search_term=data['search_term'],
                location=data['location'],
                results_wanted=int(data.get('results_wanted', 20)),
                hours_old=int(data.get('hours_old', 72)),
                country_indeed=data.get('country_indeed', 'India'),
            )
            
            if not isinstance(jobs, pd.DataFrame) or jobs.empty:
                return render_template('index.html', error='No jobs found or invalid response from scraper')
            
            # Process and filter the jobs data
            filtered_jobs = process_jobs_data(jobs)
            
            if filtered_jobs is None or filtered_jobs.empty:
                return render_template('index.html', error='No jobs found after processing')
            
            jobs_list = filtered_jobs.to_dict('records')
            
            # Create CSV string
            csv_buffer = StringIO()
            filtered_jobs.to_csv(csv_buffer, index=False, quoting=csv.QUOTE_NONNUMERIC)
            csv_string = csv_buffer.getvalue()
            
            return render_template('index.html', jobs=jobs_list, csv=csv_string, count=len(jobs_list))
        except Exception as e:
            app.logger.error(f"An error occurred: {str(e)}")
            app.logger.error(traceback.format_exc())
            return render_template('index.html', error=str(e))
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
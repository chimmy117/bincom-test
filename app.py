from flask import Flask, render_template_string, request
import mysql.connector

app = Flask(__name__)

# Simple DB connection
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",  # Update if different
        database="bincomphptest"
    )

# Home page with links
@app.route('/')
def home():
    return """
    <h1>Bincom Test - Beginner Level</h1>
    <ul>
        <li><a href="/question1">Question 1: Show one Polling Unit Result</a></li>
        <li><a href="/question2">Question 2: Show Sum for one LGA</a></li>
        <li><a href="/question3">Question 3: Add New Polling Unit Results</a></li>
    </ul>
    """

# Question 1: Show result for one polling unit
@app.route('/question1', methods=['GET', 'POST'])
def question1():
    results = None
    pus = []

    conn = get_db()
    cursor = conn.cursor()

    # Get all polling units (removed state filter for debugging; add back if needed)
    cursor.execute("""
        SELECT pu.uniqueid, pu.polling_unit_name 
        FROM polling_unit pu
        JOIN lga l ON pu.lga_id = l.uniqueid
        WHERE l.state_id = 25
        ORDER BY pu.polling_unit_name
    """)
    pus = cursor.fetchall()

    if request.method == 'POST':
        pu_id = request.form.get('pu_id')
        if pu_id:
            cursor.execute("""
                SELECT party_abbreviation, party_score 
                FROM announced_pu_results 
                WHERE polling_unit_uniqueid = %s 
                ORDER BY party_abbreviation
            """, (pu_id,))
            results = cursor.fetchall()
        if not results:
            results = [("No scores recorded for this polling unit", "")]

    cursor.close()
    conn.close()

    return render_template_string("""
    <h2>Question 1: Individual Polling Unit Result</h2>
    <form method="post">
        <label>Select Polling Unit:</label><br>
        <select name="pu_id">
            <option value="">-- Choose --</option>
            {% for pu in polling_units %}
                <option value="{{ pu[0] }}">{{ pu[1] }}</option>
            {% endfor %}
        </select><br><br>
        <button type="submit">Show Result</button>
    </form>

    {% if results %}
    <h3>Results:</h3>
    <table border="1">
        <tr><th>Party</th><th>Score</th></tr>
        {% for row in results %}
        <tr>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p style="color: orange;">No polling unit selected yet.</p>
    {% endif %}
    <br><a href="/">Back</a>
    """, polling_units=pus, results=results)

# Question 2: Summed total for one LGA
@app.route('/question2', methods=['GET', 'POST'])
def question2():
    results = None
    lgas = []

    conn = get_db()
    cursor = conn.cursor()

    # Get LGAs (removed state filter for debugging; add back if needed)
    cursor.execute("SELECT uniqueid, lga_name FROM lga WHERE state_id = 25 ORDER BY lga_name")
    lgas = cursor.fetchall()

    if request.method == 'POST':
        lga_id = request.form.get('lga_id')
        if lga_id:
            cursor.execute("""
                SELECT apr.party_abbreviation, SUM(apr.party_score) AS total
                FROM announced_pu_results apr
                JOIN polling_unit pu ON apr.polling_unit_uniqueid = pu.uniqueid
                WHERE pu.lga_id = %s
                GROUP BY apr.party_abbreviation
                ORDER BY apr.party_abbreviation
            """, (lga_id,))
            results = cursor.fetchall()
        if not results:
            results = [("No summed scores for this LGA", "")]

    cursor.close()
    conn.close()

    return render_template_string("""
    <h2>Question 2: Total Results for one LGA</h2>
    <form method="post">
        <label>Select Local Government Area (LGA):</label><br>
        <select name="lga_id">
            <option value="">-- Please choose an LGA --</option>
            {% for lga in lga_list %}
                <option value="{{ lga[0] }}">{{ lga[1] }}</option>
            {% endfor %}
        </select><br><br>
        <button type="submit">Show Total Scores</button>
    </form>
    {% if results and results[0][0] != "No results" %}
    <h3>Total Scores for this LGA:</h3>
    <table border="1" style="margin-top: 20px;">
        <tr style="background-color: #f0f0f0;">
            <th>Party</th>
            <th>Total Votes</th>
        </tr>
        {% for row in results %}
        <tr>
            <td>{{ row[0] }}</td>
            <td>{{ row[1] }}</td>
        </tr>
        {% endfor %}
    </table>
    {% else %}
    <p style="color: #e67e22; margin-top: 20px;">
        No vote totals found for this LGA yet.<br>
        (This is normal in the test data – try another LGA like Aniocha North)
    </p>
    {% endif %}
    <br><br>
    <a href="/">← Back to Home</a>
    """, lga_list=lgas, results=results)

# Question 3: Add new polling unit and results
@app.route('/question3', methods=['GET', 'POST'])
def question3():
    message = ""
    error = ""
    parties = []

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT partyid FROM party ORDER BY partyid")
    parties = [row[0] for row in cursor.fetchall()]

    if request.method == 'POST':
        pu_name = request.form.get('pu_name', '').strip()
        if pu_name:
            try:
                cursor.execute("SELECT MAX(uniqueid) FROM polling_unit")
                max_id = cursor.fetchone()[0] or 0
                new_id = max_id + 1

                # Insert new polling unit and link it to a real LGA (lga_id=1 = Aniocha North)
                cursor.execute("""
                    INSERT INTO polling_unit 
                    (uniqueid, polling_unit_id, ward_id, lga_id, uniquewardid, polling_unit_name, 
                     polling_unit_description, lat, `long`, entered_by_user, date_entered, user_ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                """, (new_id, 0, 0, 1, 0, pu_name, 'New PU description', '0.0', '0.0', 'beginner_user', '127.0.0.1'))

                # Insert scores — skip parties with names longer than 4 letters
                for party in parties:
                    if len(party) > 4:
                        continue
                    score = int(request.form.get(f'score_{party}', 0))
                    cursor.execute("""
                        INSERT INTO announced_pu_results 
                        (polling_unit_uniqueid, party_abbreviation, party_score, entered_by_user, date_entered, user_ip_address)
                        VALUES (%s, %s, %s, 'beginner_user', NOW(), '127.0.0.1')
                    """, (new_id, party, score))

                conn.commit()
                message = f"Added '{pu_name}' (ID {new_id})! Now go to Home → Question 1 → refresh page to see it."
            except mysql.connector.Error as e:
                error = f"Error: {str(e)}"

    cursor.close()
    conn.close()

    return render_template_string("""
    <h2>Question 3: Add Results for New Polling Unit</h2>
    <form method="post">
        <label>Polling Unit Name:</label><br>
        <input type="text" name="pu_name" required><br><br>

        <h3>Enter Scores for Each Party:</h3>
        {% for party in parties %}
            <label>{{ party }}:</label>
            <input type="number" name="score_{{ party }}" value="0" min="0"><br>
        {% endfor %}
        <br>
        <button type="submit">Save New Results</button>
    </form>

    {% if message %}
        <p style="color:green;">{{ message }}</p>
    {% endif %}
    {% if error %}
        <p style="color:red;">{{ error }}</p>
    {% endif %}
    <br><a href="/">Back</a>
    """, parties=parties, message=message, error=error)

    
import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Render sets PORT env var
    app.run(host="0.0.0.0", port=port, debug=False)  # bind to all interfaces

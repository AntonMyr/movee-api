from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

app = Flask(__name__)

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(
    "1hkUx3NtkESWNRw9rHeI6k45aY9xYAjmNWjY_VnhG1Gc"
).sheet1  # Replace with your sheet name


@app.route("/items", methods=["GET"])
def get_items():
    data = sheet.get_all_records()
    return jsonify(data)


@app.route("/items", methods=["POST"])
def add_item():
    data = request.json
    sheet.append_row([data["name"]])
    return jsonify({"message": "Item added"}), 201


@app.route("/add-distance", methods=["POST"])
def add_distance():
    try:
        distance = float(request.form["distance"])
        username = request.form["username"]
        usercode = request.form["usercode"]
    except (ValueError, KeyError):
        return jsonify({"error": "Invalid input"}), 400

    # Fetch all rows to find the correct column
    rows = sheet.get_all_values()

    # Combine "username+usercode" and find the column index
    header = rows[0]  # First row
    target_column = f"{username}-{usercode}"

    try:
        col_index = header.index(target_column) + 1  # Google Sheets uses 1-based index
    except ValueError:
        return jsonify({"message": "Column not found"}), 404

    # Prepare the entry in the format "<iso date>,<distance>"
    today = date.today().isoformat()
    entry = f"{today}|{distance}"

    # Find the next empty row in the target column
    col_values = sheet.col_values(col_index)
    next_row = len(col_values) + 1

    # Add the entry to the next row in the target column
    sheet.update_cell(next_row, col_index, entry)

    return jsonify({"message": "Distance added"}), 200

@app.route("/get-entries", methods=["GET"])
def get_entries():
    rows = sheet.get_all_values()

    # Create a dictionary to store distances by date
    distance_by_date = {}

    # Iterate through all columns starting from the second column
    for col_idx in range(1, len(rows[0])):
        col_values = [row[col_idx] for row in rows[1:] if len(row) > col_idx]
        for entry in col_values:
            if "|" in entry:
                iso_date, distance = entry.split("|")
                try:
                    distance = float(distance)
                except ValueError:
                    continue

                # Add distance to the corresponding date
                if iso_date in distance_by_date:
                    distance_by_date[iso_date] += distance
                else:
                    distance_by_date[iso_date] = distance

    # Convert the dictionary into the desired array of objects
    result = [{"day": day, "total_distance": total} for day, total in distance_by_date.items()]
    return jsonify(result)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

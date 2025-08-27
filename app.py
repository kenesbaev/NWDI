import cv2
import numpy as np
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB_FILE = "database.db"
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT,
    total_pixels INTEGER,
    water_pixels INTEGER,
    water_area REAL,
    water_ratio REAL,
    result_file TEXT
)
""")
conn.commit()
conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files["image"]
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            image = cv2.imread(filepath)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lower_bound = np.array([85, 50, 50])
            upper_bound = np.array([140, 255, 255])
            mask = cv2.inRange(hsv, lower_bound, upper_bound)


            
            a = np.sum(mask > 0)
            b = mask.size
            c = 10
            d = (c * c) / 1e6
            water_km2 = a * d
            water_ratio = (a / b) * 100


            water = cv2.bitwise_and(image_rgb, image_rgb, mask=mask)
            result_path = os.path.join(RESULT_FOLDER, "result_" + filename)
            cv2.imwrite(result_path, cv2.cvtColor(water, cv2.COLOR_RGB2BGR))
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("""
                INSERT INTO results (filename, total_pixels, water_pixels, water_area, water_ratio, result_file)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (filename, b, a, water_km2, water_ratio, result_path))
            conn.commit()
            conn.close()
            return render_template("index.html",
                                   original=os.path.relpath(filepath, "static").replace("\\", "/"),
                                   result=os.path.relpath(result_path, "static").replace("\\", "/"),
                                   total=b,
                                   water=a,
                                   area=round(water_km2, 2),
                                   ratio=round(water_ratio, 2))
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

from datetime import datetime

from fastapi import FastAPI, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select


# ---------- Database setup ----------

sqlite_url = "sqlite:///./survey.db"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)  # [web:13][web:14][web:23]


class SurveyResponse(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    rating: int
    feedback_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)  # [web:13][web:95]


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)  # [web:13][web:95]


def get_session():
    with Session(engine) as session:
        yield session  # [web:96]


# ---------- FastAPI app ----------

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head>
        <title>Survey App</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; }
          a.button { display: inline-block; padding: 8px 16px; margin: 4px 0; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; }
          a.button-secondary { background: #555; }
        </style>
      </head>
      <body>
        <h1>Survey App</h1>
        <p>Welcome! Please share your feedback with us.</p>
        <p>
          <a class="button" href="/survey">Fill out the survey</a>
          <a class="button button-secondary" href="/responses">View responses</a>
        </p>
      </body>
    </html>
    """


@app.get("/survey", response_class=HTMLResponse)
def get_survey_form():
    return """
    <html>
      <head>
        <title>Survey Form</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; }
          label { font-weight: bold; }
          input, textarea, select { width: 100%; padding: 8px; margin-top: 4px; box-sizing: border-box; }
          button { margin-top: 12px; padding: 8px 16px; }
        </style>
      </head>
      <body>
        <h1>Survey Form</h1>
        <form method="post" action="/survey">
          <label for="name">Name</label>
          <input id="name" type="text" name="name" placeholder="Your name" required>

          <br><br>
          <label for="email">Email</label>
          <input id="email" type="email" name="email" placeholder="you@example.com" required>

          <br><br>
          <label for="rating">Rating (1-5)</label>
          <input id="rating" type="number" name="rating" min="1" max="5" required>

          <br><br>
          <label for="feedback_text">Feedback</label>
          <textarea id="feedback_text" name="feedback_text" rows="4" placeholder="Write your feedback here..." required></textarea>

          <br><br>
          <button type="submit">Submit</button>
        </form>
      </body>
    </html>
    """


@app.post("/survey", response_class=HTMLResponse)
def submit_survey(
    name: str = Form(...),
    email: str = Form(...),
    rating: int = Form(...),
    feedback_text: str = Form(...),
    session: Session = Depends(get_session),
):
    errors = []

    # Basic string checks
    if len(name.strip()) < 2:
        errors.append("Name must be at least 2 characters long.")
    if "@" not in email or "." not in email:
        errors.append("Please enter a valid email address.")

    # Numeric validation for rating
    if rating < 1 or rating > 5:
        errors.append("Rating must be between 1 and 5.")
    if len(feedback_text.strip()) < 5:
        errors.append("Feedback must be at least 5 characters long.")

    if errors:
        error_list = "".join(f"<li>{e}</li>" for e in errors)
        return HTMLResponse(
            content=f"""
            <html>
              <head>
                <title>Survey Error</title>
                <style>
                  body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; }}
                  ul {{ color: red; }}
                  a.button {{ display: inline-block; padding: 8px 16px; margin-top: 12px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; }}
                </style>
              </head>
              <body>
                <h1>There were problems with your submission</h1>
                <ul>{error_list}</ul>
                <a class="button" href="/survey">Go back to the survey</a>
              </body>
            </html>
            """,
            status_code=400,
        )  # [web:120][web:121][web:127][web:128]

    # If everything is OK, save to DB
    response = SurveyResponse(
        name=name.strip(),
        email=email.strip(),
        rating=rating,
        feedback_text=feedback_text.strip(),
    )
    session.add(response)
    session.commit()
    session.refresh(response)  # [web:13][web:96]

    return RedirectResponse(url="/thank-you", status_code=303)


@app.get("/thank-you", response_class=HTMLResponse)
def thank_you():
    return """
    <html>
      <head>
        <title>Thank You</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; text-align: center; }
          a.button { display: inline-block; padding: 8px 16px; margin: 4px 4px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; }
          a.button-secondary { background: #555; }
        </style>
      </head>
      <body>
        <h1>Thank you for your feedback!</h1>
        <p>Your response has been recorded.</p>
        <p>
          <a class="button" href="/survey">Submit another response</a>
          <a class="button button-secondary" href="/responses">View all responses</a>
        </p>
      </body>
    </html>
    """


@app.get("/responses", response_class=HTMLResponse)
def list_responses(session: Session = Depends(get_session)):
    statement = select(SurveyResponse).order_by(SurveyResponse.id.desc())
    results = session.exec(statement).all()  # [web:13][web:23][web:96]

    rows_html = ""
    for r in results:
        created_at_str = getattr(r, "created_at", None)
        created_at_str = created_at_str.strftime("%Y-%m-%d %H:%M:%S") if created_at_str else ""
        rows_html += f"""
        <tr>
          <td>{r.id}</td>
          <td>{r.name}</td>
          <td>{r.email}</td>
          <td>{r.rating}</td>
          <td>{r.feedback_text}</td>
          <td>{created_at_str}</td>
        </tr>
        """

    count = len(results)

    return f"""
    <html>
      <head>
        <title>Responses</title>
        <style>
          body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; }}
          table {{ border-collapse: collapse; width: 100%; }}
          th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
          th {{ background: #f5f5f5; }}
          a.button {{ display: inline-block; padding: 8px 16px; margin-top: 12px; background: #1976d2; color: white; text-decoration: none; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <h1>Survey Responses ({count} total)</h1>
        <table>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Rating</th>
            <th>Feedback</th>
            <th>Submitted At</th>
          </tr>
          {rows_html}
        </table>
        <a class="button" href="/survey">Back to survey</a>
      </body>
    </html>
    """

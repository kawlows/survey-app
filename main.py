from fastapi import FastAPI, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import SQLModel, Field, Session, create_engine, select


# ---------- Database setup ----------

sqlite_url = "sqlite:///./survey.db"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


class SurveyResponse(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    email: str
    rating: int
    feedback_text: str


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


# ---------- FastAPI app ----------

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
      <head><title>Survey App</title></head>
      <body>
        <h1>Survey App</h1>
        <p><a href="/survey">Fill out the survey</a></p>
        <p><a href="/responses">View responses</a></p>
      </body>
    </html>
    """


@app.get("/survey", response_class=HTMLResponse)
def get_survey_form():
    return """
    <html>
      <head><title>Survey Form</title></head>
      <body>
        <h1>Survey Form</h1>
        <form method="post" action="/survey">
          <label>Name:</label><br>
          <input type="text" name="name" required><br><br>

          <label>Email:</label><br>
          <input type="email" name="email" required><br><br>

          <label>Rating (1-5):</label><br>
          <input type="number" name="rating" min="1" max="5" required><br><br>

          <label>Feedback:</label><br>
          <textarea name="feedback_text" rows="4" cols="40" required></textarea><br><br>

          <button type="submit">Submit</button>
        </form>
      </body>
    </html>
    """


@app.post("/survey")
def submit_survey(
    name: str = Form(...),
    email: str = Form(...),
    rating: int = Form(...),
    feedback_text: str = Form(...),
    session: Session = Depends(get_session),
):
    response = SurveyResponse(
        name=name,
        email=email,
        rating=rating,
        feedback_text=feedback_text,
    )
    session.add(response)
    session.commit()
    session.refresh(response)

    return RedirectResponse(url="/thank-you", status_code=303)


@app.get("/thank-you", response_class=HTMLResponse)
def thank_you():
    return """
    <html>
      <head><title>Thank You</title></head>
      <body>
        <h1>Thank you for your feedback!</h1>
        <p><a href="/responses">View all responses</a></p>
        <p><a href="/survey">Submit another response</a></p>
      </body>
    </html>
    """


@app.get("/responses", response_class=HTMLResponse)
def list_responses(session: Session = Depends(get_session)):
    statement = select(SurveyResponse).order_by(SurveyResponse.id.desc())
    results = session.exec(statement).all()

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
      <head><title>Responses</title></head>
      <body>
        <h1>Survey Responses ({count} total)</h1>
        <table border="1" cellpadding="5" cellspacing="0">
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
        <p><a href="/survey">Back to survey</a></p>
      </body>
    </html>
    """

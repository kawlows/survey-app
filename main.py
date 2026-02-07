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


@app.post("/survey", response_class=HTMLResponse)
def submit_survey(
    name: str = Form(...),
    email: str = Form(...),
    rating: int = Form(...),
    feedback_text: str = Form(...),
    session: Session = Depends(get_session),
):
    # Basic validation for rating range
    if rating < 1 or rating > 5:
        return HTMLResponse(
            content="""
            <html>
              <head><title>Survey Error</title></head>
              <body>
                <h1>Invalid rating</h1>
                <p>Rating must be between 1 and 5.</p>
                <p><a href="/survey">Go back to the survey</a></p>
              </body>
            </html>
            """,
            status_code=400,
        )

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
    statement = select(SurveyResponse)
    results = session.exec(statement).all()

    rows_html = ""
    for r in results:
        rows_html += f"""
        <tr>
          <td>{r.id}</td>
          <td>{r.name}</td>
          <td>{r.email}</td>
          <td>{r.rating}</td>
          <td>{r.feedback_text}</td>
        </tr>
        """

    return f"""
    <html>
      <head><title>Responses</title></head>
      <body>
        <h1>Survey Responses</h1>
        <table border="1" cellpadding="5" cellspacing="0">
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Rating</th>
            <th>Feedback</th>
          </tr>
          {rows_html}
        </table>
        <p><a href="/survey">Back to survey</a></p>
      </body>
    </html>
    """
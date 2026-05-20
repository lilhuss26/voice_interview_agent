from marshmallow import Schema, fields, validate

class InterviewStartRequest(Schema):
    job_description = fields.Str(required=True)

class StartInterviewResponse(Schema):
    session_id = fields.Str()
    first_question = fields.Str()

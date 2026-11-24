"""Document/PDF task points: one GET completes them.

  GET /ananas/job/document?jobid=<j>&knowledgeid=<kid>&courseid=<cid>
      &clazzid=<cl>&objectid=<property.objectid>&jtoken=<attachment.jtoken>
  -> {"msg":"添加考核点成功"}
"""
from .session import CPI

DOC_JOB = "https://mooc1.chaoxing.com/ananas/job/document"


def complete_document(s, job) -> bool:
    """job: dict from cards.jobs_from_marg. Returns True on success."""
    r = s.get(DOC_JOB, params={
        "jobid": job["jobid"],
        "knowledgeid": job["kid"],
        "courseid": job["cid"],
        "clazzid": job["cl"],
        "objectid": job["objectid"],
        "jtoken": job["jtoken"],
    }, timeout=30)
    return "考核点" in r.text or '"status":true' in r.text or '"status": true' in r.text

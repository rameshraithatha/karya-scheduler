# Karya - Async Job Scheduler

**Karya** is a lightweight, extensible, async job scheduler designed to orchestrate dynamic job flows using JSON-defined steps — similar to AWS Step Functions. It supports REST APIs, wait/sleep logic with retries, and conditional branching.

---

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-async-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

---

## 🚀 Features

* JSON-defined workflows with step-by-step execution
* Support for:

  * ✅ HTTP API execution
  * ⏸️ Wait/pause logic with retry and `max_retries`
  * 🔀 Conditional branching (`choice` steps)
* Context-aware templating using Jinja2
* Step outputs saved dynamically and reused in later steps
* Persisted execution context for **crash recovery and job resumption**
* Async job execution using `asyncio` with support for \~1000 concurrent jobs
* Background `job_resumer.py` handles resuming paused jobs via polling
* 💡 **NEW:** Manage reusable actions via REST API (instead of static files)

---

## 📁 Folder Structure

```
karya/
├── core/              # Executor and job resumer logic
├── db/                # SQLAlchemy models and DB session
├── api/               # FastAPI routes
├── config.py          # Configs for DB, polling, etc.
├── main.py            # FastAPI entrypoint
├── job_resumer.py     # Poller to resume paused jobs
├── workflows/         # (Optional) Predefined workflow JSONs
```

---

## 📡️ API Endpoints

### `POST /jobs`

Trigger a new job with inline workflow definition.

```json
{
  "workflow_name": "JiraEscalation",
  "parameters": { "ticket_id": "ABC-123" },
  "steps": [
    { "id": "check_jira", "type": "task", "action": "CheckJiraStatus" },
    { "id": "decision", "type": "choice", "conditions": [
      { "if": "output.check_jira.status == 'Done'", "next": "done" },
      { "default": "wait_step" }
    ]},
    { "id": "wait_step", "type": "wait", "duration": "{{ output.check_jira.retry_after }}", "max_retries": 3 },
    { "id": "done", "type": "task", "action": "FetchTodo" }
  ]
}
```

### `GET /jobs/{job_id}`

Returns job status and execution context.

### `GET /jobs/{job_id}/steps`

Returns raw step definitions for the job.

### `GET /jobs`

Returns all job records.

### `POST /jobs/{job_id}/pause`

(Stub) Pause a running job — coming soon.

### `DELETE /jobs/{job_id}`

Delete a job record.

---

## 🔧 Action Management API

Define actions like `FetchTodo` or `CheckJiraStatus` once and reuse across jobs.

* `POST /actions` — Create new action
* `GET /actions/{name}` — Fetch by name
* `PUT /actions/{name}` — Update action
* `DELETE /actions/{name}` — Delete action
* `GET /actions` — List all actions

---

## 📄 Action JSON Example

```json
{
  "name": "FetchTodo",
  "type": "http",
  "method": "POST",
  "url": "https://jsonplaceholder.typicode.com/posts",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "user_id": "{{ context.user_id }}",
    "step": "{{ meta.current_step }}",
    "retries": "{{ meta.step_retries[meta.current_step] | default(0) }}",
    "timestamp": "{{ meta.current_time }}"
  },
  "save_as": "fetch_todo"
}
```

---

## 🔀 Execution Flow Diagram

```
+--------+      +--------------+      +------------+      +----------+
| Start  +----->+  fetch_todo  +----->+  condition +----->+  success |
+--------+      +--------------+      +------------+      +----------+
                                         |
                                         v
                                   +-----------------+
                                   | wait + retry    |
                                   +-----------------+
```

---

## 📦 Setup & Run

1. **Install dependencies**:

```bash
pip install -r requirements.txt
```

2. **Start FastAPI app**:

```bash
uvicorn karya.main:app --reload
```

3. **(Recommended)** Run `job_resumer.py` in the background:

```bash
python karya/job_resumer.py
```

4. **Trigger jobs via curl/Postman**.

---

## 🤀 Curl Example

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d @job_request.json
```

---

## 🥺 Postman Collection

Coming soon: `postman_collection.json` for testing endpoints.

---

## 🤝 Contributing

1. Fork the repo
2. Create a new branch for your feature/fix
3. Add/update tests if needed
4. Submit a pull request

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

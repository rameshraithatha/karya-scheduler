import json
import httpx
import jinja2
import logging
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Any, Optional
from db.models import Job, Action
from db.session import SessionLocal

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(name)s: %(message)s"
)


class FlowExecutor:
    def __init__(
        self, steps: List[Dict[str, Any]], parameters: Dict[str, Any], job_id: str
    ):

        self.job_id = job_id
        self.template_env = jinja2.Environment()
        self.session = SessionLocal()
        self.default_max_retries = 5

        # Fetch job to get existing retry state if any
        job = self.session.query(Job).get(job_id)

        # Load existing retry counts from DB (if any)
        step_retries = {}
        if job and job.step_retry_counts:
            step_retries = job.step_retry_counts.copy()

        self.steps = steps
        self.context = {
            "context": parameters,
            "meta": {
                "job_id": job_id,
                "start_time": datetime.now(UTC).isoformat(),
                "step_retries": step_retries
            },
        }

        self.retry_counts = step_retries.copy()

    def persist_context(self):
        job = self.session.query(Job).get(self.job_id)
        if job:
            job.context = self.context
            job.current_step_id = self.context["meta"].get("current_step")
            job.step_retry_counts = self.context["meta"]["step_retries"].copy()
            self.session.commit()
            logger.info(
                f"[Job {self.job_id}] Context persisted after step '{job.current_step_id}'"
            )

    def update_job_status(self, status: str, error: Optional[str] = None):
        job = self.session.query(Job).get(self.job_id)
        if job:
            job.status = status
            job.context = self.context
            job.current_step_id = self.context["meta"].get("current_step")
            job.updated_at = datetime.now(UTC)
            if error and hasattr(job, "message"):
                job.message = error
            self.session.commit()
            logger.info(f"[Job {self.job_id}] Status updated to {status}")

    async def load_action(self, action_name: str) -> Dict[str, Any]:
        action_obj = (
            self.session.query(Action).filter(Action.name == action_name).first()
        )
        if not action_obj:
            raise ValueError(f"Action '{action_name}' not found in DB")
        return {"type": action_obj.type, **action_obj.config}

    async def execute_http(self, action: Dict[str, Any]) -> str:
        url = self.template_env.from_string(action["url"]).render(**self.context)
        body_template = action.get("body")

        if body_template is None:
            body = self.context
        else:
            rendered_body = {}
            for key, template_val in body_template.items():
                template_str = self.template_env.from_string(template_val)
                rendered_json = template_str.render(**self.context)
                rendered_body[key] = json.loads(rendered_json)
            body = rendered_body

        headers = {
            k: self.template_env.from_string(v).render(**self.context)
            for k, v in action.get("headers", {}).items()
        }

        logger.info(
            f"[Job {self.job_id}] Executing HTTP {action['method']} request to {url}"
        )
        async with httpx.AsyncClient() as client:
            logger.info(
                f"method: {action['method']}, url: {url}, headers: {headers}, body: {body}"
            )
            resp = await client.request(
                action["method"], url, headers=headers, json=body
            )
            data = resp.json()
            if "save_as" in action:
                self.context.setdefault("output", {})[action["save_as"]] = data
            logger.info(
                f"[Job {self.job_id}] HTTP response saved to '{action.get('save_as', 'output')}'"
            )
            return "http_completed"

    def evaluate_choice(self, step: Dict[str, Any]) -> str:
        for cond in step["conditions"]:
            if "if" in cond:
                expr = cond["if"]
                try:
                    template = self.template_env.from_string(
                        f"{{% if {expr} %}}true{{% else %}}false{{% endif %}}"
                    )
                    result = template.render(**self.context)
                    if result == "true":
                        return cond["next"]
                except Exception as e:
                    logger.warning(
                        f"[Job {self.job_id}] Failed to evaluate condition '{expr}': {str(e)}"
                    )
        for cond in step["conditions"]:
            if "default" in cond:
                return cond["default"]
        raise ValueError("No matching condition and no default found")

    async def run_step(self, step: Dict[str, Any]) -> Optional[str]:
        step_type = step["type"]
        step_id = step["id"]
        logger.info(
            f"[Job {self.job_id}] Running step '{step_id}' of type '{step_type}'"
        )

        self.context["meta"]["current_step"] = step_id
        self.context["meta"]["current_time"] = datetime.now(UTC).isoformat()

        try:
            if step_type == "task":
                result = None
                action = await self.load_action(step["action"])
                if action["type"] == "http":
                    result = await self.execute_http(action)
                self.persist_context()
                return result

            elif step_type == "wait":
                max_retries = step.get("max_retries", self.default_max_retries)
                self.retry_counts[step_id] = self.retry_counts.get(step_id, 0) + 1
                self.context["meta"]["step_retries"][step_id] = self.retry_counts[
                    step_id
                ]

                if self.retry_counts[step_id] > max_retries:
                    self.update_job_status(
                        "FAILED", f"Max retries exceeded for step '{step_id}'"
                    )
                    return None

                duration_str = self.template_env.from_string(
                    str(step["duration"])
                ).render(**self.context)
                if not duration_str.strip():
                    self.update_job_status(
                        "FAILED", f"Invalid wait duration for step '{step_id}'"
                    )
                    return None

                try:
                    resume_after_seconds = float(duration_str)
                except ValueError:
                    self.update_job_status(
                        "FAILED", f"Wait duration not a number for step '{step_id}'"
                    )
                    return None

                resume_at = datetime.now(UTC) + timedelta(seconds=resume_after_seconds)
                job = self.session.query(Job).get(self.job_id)
                if job:
                    job.resume_at = resume_at
                    job.status = "WAITING"
                    job.context = self.context
                    job.current_step_id = step_id
                    job.step_retry_counts = self.context["meta"]["step_retries"].copy()
                    job.updated_at = datetime.now(UTC)
                    self.session.commit()
                    logger.info(
                        f"[Job {self.job_id}] Paused. Will resume at {resume_at.isoformat()}"
                    )
                return "job_paused"  # Halt execution here; poller will resume it later

            elif step_type == "choice":
                next_id = self.evaluate_choice(step)
                self.persist_context()
                return next_id

            else:
                raise ValueError(f"Unsupported step type: {step_type}")

        except Exception as e:
            logger.error(
                f"[Job {self.job_id}] Error in step '{step_id}': {str(e)}",
                exc_info=True,
            )
            raise

    async def execute_steps(self) -> str:
        index_map = {step["id"]: i for i, step in enumerate(self.steps)}
        last_step_id = self.context["meta"].get("current_step")
        i = index_map.get(last_step_id, 0)
        logger.info(
            f"[Job {self.job_id}] {'Resuming' if last_step_id else 'Starting'} from step '{self.steps[i]['id']}'"
        )

        while i < len(self.steps):
            step = self.steps[i]
            result = await self.run_step(step)
            if result == "job_paused":
                self.update_job_status("WAITING", f"Paused at step '{step['id']}'")
                return "paused"

            if step["type"] == "choice":
                if result not in index_map:
                    self.update_job_status("FAILED", f"Invalid next step ID: {result}")
                    return "failed"
                i = index_map[result]
            else:
                i += 1

        self.update_job_status("COMPLETED")
        return "completed"

    async def run(self):
        try:
            logger.info(f"[Job {self.job_id}] Starting job execution")
            self.update_job_status("RUNNING")
            await self.execute_steps()
        except Exception as e:
            logger.error(f"[Job {self.job_id}] Job failed: {str(e)}", exc_info=True)
            self.update_job_status("FAILED", str(e))

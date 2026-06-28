from __future__ import annotations
import time
import httpx


class PipelineError(RuntimeError):
    pass


class PipelineClient:
    """Thin client over the Ephemera FastAPI: generate -> poll -> fetch collage JSON."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "PipelineClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def generate(self, topic: str, density: str | None = None, layout_seed: int | None = None) -> str:
        payload: dict = {"topic": topic, "density": density}
        if layout_seed is not None:
            payload["layout_seed"] = layout_seed
        r = self._client.post(f"{self.base_url}/generate", json=payload)
        r.raise_for_status()
        return r.json()["job_id"]

    def job_status(self, job_id: str) -> str:
        r = self._client.get(f"{self.base_url}/job/{job_id}")
        r.raise_for_status()
        return r.json()["status"]

    def wait(
        self,
        job_id: str,
        want_enriched: bool = True,
        timeout: float = 180.0,
        interval: float = 2.0,
    ) -> str:
        """Block until the job reaches a terminal state.

        Ephemera runs two phases: the base collage ("done") then enrichment
        ("enriched"). want_enriched waits for the fuller, second-pass collage.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.job_status(job_id)
            if status == "failed":
                raise PipelineError(f"pipeline failed for job {job_id}")
            if status == "enriched":
                return status
            if status == "done" and not want_enriched:
                return status
            time.sleep(interval)
        raise PipelineError(f"timed out waiting for job {job_id} after {timeout}s")

    def fetch_collage(self, job_id: str) -> dict:
        r = self._client.get(f"{self.base_url}/collage/{job_id}")
        r.raise_for_status()
        return r.json()

    def run(self, topic: str, density: str | None = None, layout_seed: int | None = None,
            want_enriched: bool = True) -> dict:
        """Convenience: generate, wait, and return the finished collage dict."""
        job_id = self.generate(topic, density, layout_seed)
        self.wait(job_id, want_enriched=want_enriched)
        return self.fetch_collage(job_id)

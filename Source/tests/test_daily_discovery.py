from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from jobfinder.daily_jobs import DailyJobRecord, classify_work_mode, deduplicate_jobs, is_relevant_remote_development_job
from jobfinder.daily_storage import daily_database_path, merge_and_save_daily_jobs, parse_daily_database
from jobfinder.discovery import run_daily_discovery
from jobfinder.skill_matching import SkillProfile, evaluate_job_skills
from jobfinder.sources.web_boards import SourceScanResult, extract_json_ld_jobs


class DailyJobTests(unittest.TestCase):
    def test_relevance_accepts_remote_software_development_variations(self) -> None:
        job = DailyJobRecord(
            companyName="Example",
            jobTitle="Senior Full Stack .NET Developer",
            jobUrl="https://example.com/jobs/1",
            applicationUrl="https://example.com/apply/1",
            source="Built In",
            location="Remote - United States",
            remote=True,
        )

        self.assertTrue(is_relevant_remote_development_job(job))

    def test_relevance_excludes_obvious_non_development_roles(self) -> None:
        job = DailyJobRecord(
            companyName="Example",
            jobTitle="Project Manager",
            jobUrl="https://example.com/jobs/1",
            applicationUrl="https://example.com/apply/1",
            source="Built In",
            location="Remote",
            remote=True,
        )

        self.assertFalse(is_relevant_remote_development_job(job))

    def test_work_mode_classifier_reads_description_evidence(self) -> None:
        work_mode, evidence = classify_work_mode(
            "This is a hybrid role with three days per week in office and two days remote."
        )

        self.assertEqual(work_mode, "hybrid")
        self.assertIn("hybrid role", evidence or "")

    def test_work_mode_classifier_uses_metadata_remote_when_description_is_silent(self) -> None:
        work_mode, evidence = classify_work_mode(
            "Build APIs for a consumer product.",
            metadata_remote=True,
            metadata_evidence="Structured metadata indicates remote or telecommute work.",
        )

        self.assertEqual(work_mode, "remote")
        self.assertEqual(evidence, "Structured metadata indicates remote or telecommute work.")

    def test_relevance_rejects_explicit_hybrid_or_onsite_work_mode(self) -> None:
        job = DailyJobRecord(
            companyName="Example",
            jobTitle="Software Engineer",
            jobUrl="https://example.com/jobs/1",
            applicationUrl="https://example.com/apply/1",
            source="Built In",
            location="USA",
            remote=True,
            workMode="hybrid",
            workModeEvidence="This is a hybrid role.",
        )

        self.assertFalse(is_relevant_remote_development_job(job))

    def test_relevance_rejects_remote_job_with_only_excluded_skills(self) -> None:
        job = DailyJobRecord(
            companyName="Example",
            jobTitle="Software Engineer",
            jobUrl="https://example.com/jobs/1",
            applicationUrl="https://example.com/apply/1",
            source="Built In",
            location="Remote",
            remote=True,
            classification="EXCLUDE",
            excludedSkillsFound=("Java", "Spring Boot"),
            exclusionReason="Only excluded-stack indicators were found in the job description.",
        )

        self.assertFalse(is_relevant_remote_development_job(job))

    def test_relevance_accepts_remote_generic_title_with_current_skill_match(self) -> None:
        job = DailyJobRecord(
            companyName="Example",
            jobTitle="Application Developer",
            jobUrl="https://example.com/jobs/1",
            applicationUrl="https://example.com/apply/1",
            source="Built In",
            location="Remote",
            remote=True,
            classification="INCLUDE",
            matchedSkills=("C#", ".NET", "React"),
        )

        self.assertTrue(is_relevant_remote_development_job(job))

    def test_deduplicate_prefers_more_direct_application_url(self) -> None:
        board_listing = DailyJobRecord(
            companyName="Example Inc.",
            jobTitle="Software Engineer",
            jobUrl="https://www.dice.com/job-detail/1",
            applicationUrl="https://www.dice.com/job-detail/1",
            source="Dice",
            location="Remote",
            remote=True,
        )
        direct_listing = DailyJobRecord(
            companyName="Example Inc",
            jobTitle="Software Engineer",
            jobUrl="https://www.builtin.com/job/1",
            applicationUrl="https://example.com/careers/apply/1",
            source="Built In",
            location="Remote",
            remote=True,
        )

        jobs = deduplicate_jobs([board_listing, direct_listing])

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].applicationUrl, "https://example.com/careers/apply/1")


class DailyStorageTests(unittest.TestCase):
    def test_daily_database_path_uses_generated_date_inside_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            path = daily_database_path(output_dir=output_dir, generated_on=date(2026, 8, 19))

        self.assertEqual(path.name, "jobs-2026-08-19.json")
        self.assertEqual(path.parent.name, "Job Database")

    def test_merge_and_save_preserves_existing_jobs_and_writes_parseable_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            existing = DailyJobRecord(
                companyName="Existing",
                jobTitle="Software Engineer",
                jobUrl="https://existing.example/jobs/1",
                applicationUrl="https://existing.example/apply/1",
                source="Indeed",
                location="Remote",
                remote=True,
            )
            new = DailyJobRecord(
                companyName="New",
                jobTitle="Full Stack Developer",
                jobUrl="https://new.example/jobs/1",
                applicationUrl="https://new.example/apply/1",
                source="Built In",
                location="Remote",
                remote=True,
            )

            path = merge_and_save_daily_jobs([existing], output_dir=output_dir, generated_on=generated_on)
            merge_and_save_daily_jobs([new], output_dir=output_dir, generated_on=generated_on)
            payload = parse_daily_database(path)

        self.assertEqual(payload["generatedDate"], "2026-08-19")
        self.assertEqual(len(payload["jobs"]), 2)
        self.assertEqual(payload["jobs"][0]["workMode"], "unknown")
        self.assertIn("workModeEvidence", payload["jobs"][0])
        json.dumps(payload)

    def test_existing_file_merge_preserves_work_mode_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            job = DailyJobRecord(
                companyName="Example",
                jobTitle="Software Engineer",
                jobUrl="https://example.com/jobs/1",
                applicationUrl="https://example.com/apply/1",
                source="Indeed",
                location="Remote",
                remote=True,
                workMode="remote",
                workModeEvidence="This is a remote position.",
            )

            path = merge_and_save_daily_jobs([job], output_dir=output_dir, generated_on=generated_on)
            merge_and_save_daily_jobs([], output_dir=output_dir, generated_on=generated_on)
            payload = parse_daily_database(path)

        self.assertEqual(payload["jobs"][0]["workMode"], "remote")
        self.assertEqual(payload["jobs"][0]["workModeEvidence"], "This is a remote position.")

    def test_json_ld_description_overrides_remote_metadata_with_hybrid_mode(self) -> None:
        page_html = """
        <html>
          <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Software Engineer",
            "url": "https://example.com/jobs/1",
            "hiringOrganization": {"name": "Example"},
            "jobLocationType": "TELECOMMUTE",
            "description": "This is a hybrid role based in Chicago with three days per week in office."
          }
          </script>
        </html>
        """

        jobs = extract_json_ld_jobs(page_html, source="Built In", fallback_url="https://builtin.com/job/1")

        self.assertEqual(jobs[0].workMode, "hybrid")
        self.assertFalse(jobs[0].remote)
        self.assertIn("hybrid role", jobs[0].workModeEvidence or "")

    def test_json_ld_excluded_only_job_is_not_relevant(self) -> None:
        profile = SkillProfile(
            current_skills=("C#", ".NET", "React", "AWS"),
            excluded_skills=("Java", "Spring Boot"),
            neutral_skills=("AWS",),
        )
        page_html = """
        <html>
          <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Software Engineer",
            "url": "https://example.com/jobs/1",
            "hiringOrganization": {"name": "Example"},
            "jobLocationType": "TELECOMMUTE",
            "description": "Build services with Java, Spring Boot, and AWS."
          }
          </script>
        </html>
        """

        jobs = extract_json_ld_jobs(
            page_html,
            source="Built In",
            fallback_url="https://builtin.com/job/1",
            skill_profile=profile,
        )

        self.assertEqual(jobs[0].classification, "EXCLUDE")
        self.assertEqual(jobs[0].excludedSkillsFound, ("Java", "Spring Boot"))
        self.assertFalse(is_relevant_remote_development_job(jobs[0]))


class SkillMatchingTests(unittest.TestCase):
    def test_excluded_only_skills_classify_as_exclude(self) -> None:
        profile = SkillProfile(
            current_skills=("C#", ".NET", "React", "AWS"),
            excluded_skills=("Java", "Spring Boot"),
            neutral_skills=("AWS",),
        )

        result = evaluate_job_skills("Required stack: Java, Spring Boot, AWS.", profile)

        self.assertEqual(result.classification, "EXCLUDE")
        self.assertEqual(result.matched_skills, ("AWS",))
        self.assertEqual(result.excluded_skills_found, ("Java", "Spring Boot"))

    def test_current_and_excluded_skills_classify_as_include(self) -> None:
        profile = SkillProfile(
            current_skills=("C#", ".NET", "React"),
            excluded_skills=("Java", "Spring Boot"),
        )

        result = evaluate_job_skills("Required stack: C#, .NET, React. Some Java services exist.", profile)

        self.assertEqual(result.classification, "INCLUDE")
        self.assertEqual(result.matched_skills, ("C#", ".NET", "React"))
        self.assertEqual(result.excluded_skills_found, ("Java",))

    def test_java_does_not_match_javascript(self) -> None:
        profile = SkillProfile(
            current_skills=("JavaScript", "TypeScript"),
            excluded_skills=("Java",),
        )

        result = evaluate_job_skills("Build web applications with JavaScript and TypeScript.", profile)

        self.assertEqual(result.classification, "INCLUDE")
        self.assertEqual(result.matched_skills, ("JavaScript", "TypeScript"))
        self.assertEqual(result.excluded_skills_found, ())


class DailyDiscoveryTests(unittest.TestCase):
    def test_authentication_checkpoint_stops_before_later_sources(self) -> None:
        sources = [
            FakeSource("Built In", [sample_job("Built In")]),
            FakeSource("LinkedIn Jobs", [], authentication_required=True),
            FakeSource("Wellfound", [sample_job("Wellfound")]),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("jobfinder.discovery.default_sources", return_value=sources):
                result = run_daily_discovery(
                    output_dir=Path(temporary_directory) / "Job Database",
                    generated_on=date(2026, 8, 19),
                )

        self.assertEqual(result.scanned_sites, ["Built In"])
        self.assertEqual(result.authentication_required_sites, ["LinkedIn Jobs"])
        self.assertEqual(len(result.jobs), 1)

    def test_source_failure_keeps_successful_results_valid(self) -> None:
        sources = [
            FakeSource("Built In", [sample_job("Built In")]),
            FakeSource("Dice", [], failed_reason="layout changed"),
            FakeSource("Indeed", [sample_job("Indeed", company="Another Co")]),
        ]

        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("jobfinder.discovery.default_sources", return_value=sources):
                result = run_daily_discovery(
                    output_dir=Path(temporary_directory) / "Job Database",
                    generated_on=date(2026, 8, 19),
                )
                self.assertTrue(result.output_path.exists())
                self.assertEqual(len(parse_daily_database(result.output_path)["jobs"]), 2)

        self.assertEqual(result.failed_sites, {"Dice": "layout changed"})
        self.assertEqual(len(result.jobs), 2)

    def test_progress_callback_reports_scan_steps_and_save_path(self) -> None:
        sources = [FakeSource("Built In", [sample_job("Built In")])]
        messages: list[str] = []

        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch("jobfinder.discovery.default_sources", return_value=sources):
                run_daily_discovery(
                    output_dir=Path(temporary_directory) / "Job Database",
                    generated_on=date(2026, 8, 19),
                    progress=messages.append,
                )

        self.assertIn("Starting daily job discovery.", messages)
        self.assertTrue(any(message == "Scanning Built In." for message in messages))
        self.assertTrue(any(message.startswith("Output target:") for message in messages))
        self.assertTrue(any(message == "After dedupe: 1 unique jobs." for message in messages))


class FakeSource:
    def __init__(
        self,
        name: str,
        jobs: list[DailyJobRecord],
        *,
        authentication_required: bool = False,
        failed_reason: str | None = None,
    ) -> None:
        self.display_name = name
        self.jobs = jobs
        self.authentication_required = authentication_required
        self.failed_reason = failed_reason

    def scan(self, *, limit_per_query: int = 10, progress=None) -> SourceScanResult:
        if progress is not None:
            progress(f"{self.display_name}: fake progress.")
        return SourceScanResult(
            self.display_name,
            self.jobs,
            authentication_required=self.authentication_required,
            failed_reason=self.failed_reason,
        )


def sample_job(source: str, *, company: str = "Example") -> DailyJobRecord:
    return DailyJobRecord(
        companyName=company,
        jobTitle="Software Engineer",
        jobUrl=f"https://{company.lower().replace(' ', '')}.example/jobs/1",
        applicationUrl=f"https://{company.lower().replace(' ', '')}.example/apply/1",
        source=source,
        location="Remote",
        remote=True,
    )


if __name__ == "__main__":
    unittest.main()

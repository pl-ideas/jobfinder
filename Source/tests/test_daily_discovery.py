from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from jobfinder.daily_jobs import (
    DailyJobRecord,
    classify_work_mode,
    deduplicate_jobs,
    is_relevant_remote_development_job,
    salary_sort_value,
)
from jobfinder.company_careers import (
    career_entry_urls,
    company_homepage_candidates,
    company_search_urls,
    discover_career_urls_from_homepage,
    discover_career_urls_from_search,
    latest_daily_database_path,
    run_company_careers_discovery,
    scan_company_careers,
)
from jobfinder.daily_storage import daily_database_path, merge_and_save_daily_jobs, parse_daily_database
from jobfinder.discovery import run_daily_discovery
from jobfinder.employer_exclusions import is_acceptable_recruiting_agency, is_excluded_employer
from jobfinder.job_ranking import RankingProfile, rank_job_text
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

    def test_relevance_rejects_recruiting_or_staffing_employers(self) -> None:
        job = DailyJobRecord(
            companyName="Random Technology Staffing",
            jobTitle="Software Engineer",
            jobUrl="https://example.com/jobs/1",
            applicationUrl="https://example.com/apply/1",
            source="Built In",
            location="Remote",
            remote=True,
            classification="INCLUDE",
            matchedSkills=("C#", ".NET", "React"),
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

    def test_deduplicate_sorts_by_rank_then_salary_descending(self) -> None:
        jobs = deduplicate_jobs(
            [
                sample_job("Built In", company="Rank Nine Lower", rank=9, salary="USD 120000 - 160000 YEAR"),
                sample_job("Built In", company="Rank Ten", rank=10, salary="USD 90000 - 130000 YEAR"),
                sample_job("Built In", company="Rank Nine Higher", rank=9, salary="USD 170000 - 220000 YEAR"),
            ]
        )

        self.assertEqual([job.companyName for job in jobs], ["Rank Ten", "Rank Nine Higher", "Rank Nine Lower"])

    def test_salary_sort_value_uses_highest_amount(self) -> None:
        self.assertEqual(salary_sort_value("USD 169000 - 240000 YEAR"), 240000)
        self.assertEqual(salary_sort_value("$120k - $150k"), 150000)


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

    def test_json_ld_job_gets_rank_from_description_and_docs(self) -> None:
        skill_profile = SkillProfile(current_skills=("C#", ".NET", "React", "Azure"))
        ranking_profile = RankingProfile(
            primary_skills=("C#", ".NET", "React", "Azure"),
            secondary_skills=("Docker",),
            specialized_skills=("PingOne",),
            resume_terms=("System Design",),
        )
        page_html = """
        <html>
          <script type="application/ld+json">
          {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Senior Full Stack Engineer",
            "url": "https://example.com/jobs/1",
            "hiringOrganization": {"name": "Example"},
            "jobLocationType": "TELECOMMUTE",
            "description": "Build remote systems with C#, .NET, React, Azure, Docker, PingOne, and System Design."
          }
          </script>
        </html>
        """

        jobs = extract_json_ld_jobs(
            page_html,
            source="Built In",
            fallback_url="https://builtin.com/job/1",
            skill_profile=skill_profile,
            ranking_profile=ranking_profile,
        )

        self.assertEqual(jobs[0].rank, 10)
        self.assertIn("C#", jobs[0].rankEvidence)
        self.assertIn("Azure", jobs[0].rankEvidence)

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


class EmployerExclusionTests(unittest.TestCase):
    def test_named_staffing_company_is_excluded(self) -> None:
        self.assertTrue(is_excluded_employer("Synersys Technologies"))

    def test_staffing_indicator_text_is_excluded(self) -> None:
        self.assertTrue(is_excluded_employer("Example", "Technology Consulting and Staffing"))

    def test_acceptable_recruiting_agencies_are_not_excluded(self) -> None:
        self.assertTrue(is_acceptable_recruiting_agency("Kforce Technology Staffing"))
        self.assertFalse(is_excluded_employer("Kforce Technology Staffing"))


class JobRankingTests(unittest.TestCase):
    def test_rank_job_text_returns_one_for_no_profile_matches(self) -> None:
        profile = RankingProfile(primary_skills=("C#", ".NET"))

        result = rank_job_text("Customer support and ticket triage.", profile)

        self.assertEqual(result.rank, 1)
        self.assertEqual(result.evidence, ())

    def test_rank_job_text_returns_ten_for_strong_profile_overlap(self) -> None:
        profile = RankingProfile(
            primary_skills=("C#", ".NET", "React", "Azure"),
            secondary_skills=("Docker",),
            specialized_skills=("PingOne",),
            resume_terms=("System Design",),
        )

        result = rank_job_text("C# .NET React Azure Docker PingOne System Design", profile)

        self.assertEqual(result.rank, 10)
        self.assertEqual(result.evidence[:4], ("C#", ".NET", "React", "Azure"))


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


class CompanyCareersTests(unittest.TestCase):
    def test_latest_daily_database_path_uses_newest_date(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            output_dir.mkdir()
            older = output_dir / "jobs-2026-08-18.json"
            newer = output_dir / "jobs-2026-08-19.json"
            older.write_text('{"generatedDate": "2026-08-18", "jobs": []}', encoding="utf-8")
            newer.write_text('{"generatedDate": "2026-08-19", "jobs": []}', encoding="utf-8")

            self.assertEqual(latest_daily_database_path(output_dir), newer)

    def test_career_entry_urls_skips_job_board_and_ats_urls(self) -> None:
        job = DailyJobRecord(
            companyName="Example Inc",
            jobTitle="Software Engineer",
            jobUrl="https://builtin.com/job/123",
            applicationUrl="https://boards.greenhouse.io/example/jobs/123",
            source="Built In",
        )

        self.assertEqual(career_entry_urls(job), [])

    def test_company_homepage_candidates_include_common_domains(self) -> None:
        self.assertEqual(
            company_homepage_candidates("Example Inc"),
            [
                "https://example.com",
                "https://www.example.com",
                "https://example.net",
                "https://www.example.net",
                "https://example.org",
                "https://www.example.org",
                "https://example.io",
                "https://www.example.io",
                "https://example.co",
                "https://www.example.co",
            ],
        )

    def test_homepage_discovery_finds_career_link(self) -> None:
        pages = {"https://example.com": '<html><a href="/careers">Work for us</a></html>'}

        result = discover_career_urls_from_homepage("Example", fetcher=lambda url: pages[url])

        self.assertEqual(result.status, "HOMEPAGE_CAREERS_FOUND")
        self.assertEqual(result.career_urls, ["https://example.com/careers"])

    def test_homepage_discovery_reports_no_homepage(self) -> None:
        result = discover_career_urls_from_homepage("Missing", fetcher=lambda url: (_ for _ in ()).throw(RuntimeError(url)))

        self.assertEqual(result.status, "NO_HOMEPAGE")

    def test_homepage_discovery_reports_homepage_without_career_links(self) -> None:
        pages = {"https://example.com": "<html><a href='/about'>About</a></html>"}

        result = discover_career_urls_from_homepage("Example", fetcher=lambda url: pages[url])

        self.assertEqual(result.status, "HOMEPAGE_FOUND_NO_CAREER_LINKS")

    def test_public_search_finds_official_career_link(self) -> None:
        search_url = company_search_urls("Citadel Securities")[0]
        pages = {
            search_url: """
                <html>
                  <a href="/l/?uddg=https%3A%2F%2Fwww.citadelsecurities.com%2Fcareers%2F">Careers</a>
                </html>
            """,
        }

        result = discover_career_urls_from_search("Citadel Securities", fetcher=lambda url: pages[url])

        self.assertEqual(result.status, "SEARCH_CAREERS_FOUND")
        self.assertEqual(result.career_urls, ["https://www.citadelsecurities.com/careers/"])

    def test_company_careers_discovery_writes_matching_corporate_job_to_verified_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            seed = DailyJobRecord(
                companyName="Example",
                jobTitle="Software Engineer",
                jobUrl="https://builtin.com/job/123",
                applicationUrl="https://example.com/apply/seed",
                source="Built In",
                location="Remote",
                remote=True,
                matchedSkills=("C#", ".NET", "React"),
                rank=8,
            )
            input_path = merge_and_save_daily_jobs([seed], output_dir=output_dir, generated_on=generated_on)
            pages = {
                "https://example.com/careers": '<html><a href="/jobs/2">Senior Software Engineer</a></html>',
                "https://example.com/jobs/2": """
                    <html>
                      <script type="application/ld+json">
                      {
                        "@context": "https://schema.org",
                        "@type": "JobPosting",
                        "title": "Software Engineer",
                        "url": "https://example.com/jobs/2",
                        "hiringOrganization": {"name": "Example"},
                        "jobLocationType": "TELECOMMUTE",
                        "description": "Remote role building C# .NET React Azure systems."
                      }
                      </script>
                    </html>
                """,
            }

            result = run_company_careers_discovery(
                input_path=input_path,
                output_dir=output_dir,
                limit_pages_per_company=5,
                fetcher=lambda url: pages[url],
            )
            seed_payload = parse_daily_database(input_path)
            verified_payload = parse_daily_database(result.output_path)

        self.assertEqual(result.companies_reviewed, ["Example"])
        self.assertEqual(len(result.jobs_added), 1)
        self.assertEqual(result.review_statuses[0].status, "FULLY_REVIEWED")
        self.assertEqual(result.review_statuses[0].pagesReviewed, 2)
        self.assertEqual(result.output_path.name, "verified-jobs-2026-08-19.json")
        self.assertEqual(seed_payload["jobs"][0]["source"], "Built In")
        self.assertEqual(verified_payload["jobs"][0]["source"], "Company Careers: Example")
        self.assertEqual(verified_payload["jobs"][0]["jobUrl"], "https://example.com/jobs/2")

    def test_company_careers_discovery_uses_homepage_career_link_when_seed_has_no_corporate_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            seed = DailyJobRecord(
                companyName="Example",
                jobTitle="Software Engineer",
                jobUrl="https://builtin.com/job/123",
                applicationUrl="https://builtin.com/job/123",
                source="Built In",
                location="Remote",
                remote=True,
                matchedSkills=("C#", ".NET", "React"),
                rank=8,
            )
            input_path = merge_and_save_daily_jobs([seed], output_dir=output_dir, generated_on=generated_on)
            pages = {
                "https://example.com": '<html><a href="/careers">Careers</a></html>',
                "https://example.com/careers": '<html><a href="/jobs/2">Senior Software Engineer</a></html>',
                "https://example.com/jobs/2": """
                    <html>
                      <script type="application/ld+json">
                      {
                        "@context": "https://schema.org",
                        "@type": "JobPosting",
                        "title": "Software Engineer",
                        "url": "https://example.com/jobs/2",
                        "hiringOrganization": {"name": "Example"},
                        "jobLocationType": "TELECOMMUTE",
                        "description": "Remote role building C# .NET React Azure systems."
                      }
                      </script>
                    </html>
                """,
            }

            result = run_company_careers_discovery(
                input_path=input_path,
                output_dir=output_dir,
                limit_pages_per_company=5,
                fetcher=lambda url: pages[url],
            )

        self.assertEqual(result.review_statuses[0].status, "FULLY_REVIEWED")
        self.assertEqual(len(result.jobs_added), 1)

    def test_company_careers_discovery_uses_public_search_career_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            seed = DailyJobRecord(
                companyName="Citadel Securities",
                jobTitle="Software Engineer",
                jobUrl="https://builtin.com/job/123",
                applicationUrl="https://builtin.com/job/123",
                source="Built In",
                location="Remote",
                remote=True,
                matchedSkills=("C#", ".NET", "React"),
                rank=8,
            )
            input_path = merge_and_save_daily_jobs([seed], output_dir=output_dir, generated_on=generated_on)
            search_url = company_search_urls("Citadel Securities")[0]
            pages = {
                search_url: """
                    <html>
                      <a href="/l/?uddg=https%3A%2F%2Fwww.citadelsecurities.com%2Fcareers%2F">Careers</a>
                    </html>
                """,
                "https://www.citadelsecurities.com/careers/": '<html><a href="/careers/job/2">Senior Software Engineer</a></html>',
                "https://www.citadelsecurities.com/careers/job/2": """
                    <html>
                      <script type="application/ld+json">
                      {
                        "@context": "https://schema.org",
                        "@type": "JobPosting",
                        "title": "Software Engineer",
                        "url": "https://www.citadelsecurities.com/careers/job/2",
                        "hiringOrganization": {"name": "Citadel Securities"},
                        "jobLocationType": "TELECOMMUTE",
                        "description": "Remote role building C# .NET React Azure systems."
                      }
                      </script>
                    </html>
                """,
            }

            result = run_company_careers_discovery(
                input_path=input_path,
                output_dir=output_dir,
                limit_pages_per_company=5,
                fetcher=lambda url: pages[url],
            )

        self.assertEqual(result.review_statuses[0].status, "FULLY_REVIEWED")
        self.assertEqual(len(result.jobs_added), 1)

    def test_company_careers_discovery_reports_no_homepage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            seed = sample_job("Built In", company="Missing")
            seed = DailyJobRecord(
                companyName=seed.companyName,
                jobTitle=seed.jobTitle,
                jobUrl="https://builtin.com/job/123",
                applicationUrl="https://builtin.com/job/123",
                source=seed.source,
                location=seed.location,
                remote=seed.remote,
                matchedSkills=("C#",),
            )
            input_path = merge_and_save_daily_jobs([seed], output_dir=output_dir, generated_on=generated_on)

            result = run_company_careers_discovery(
                input_path=input_path,
                output_dir=output_dir,
                fetcher=lambda url: (_ for _ in ()).throw(RuntimeError(url)),
            )

        self.assertEqual(result.review_statuses[0].status, "NO_HOMEPAGE")

    def test_company_careers_discovery_skips_excluded_employer_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            seed = DailyJobRecord(
                companyName="Synersys Technologies",
                jobTitle="Software Engineer",
                jobUrl="https://builtin.com/job/123",
                applicationUrl="https://synersys.example/careers",
                source="Built In",
                location="Remote",
                remote=True,
                matchedSkills=("C#", ".NET"),
                rank=7,
            )
            input_path = merge_and_save_daily_jobs([seed], output_dir=output_dir, generated_on=generated_on)

            result = run_company_careers_discovery(
                input_path=input_path,
                output_dir=output_dir,
                fetcher=lambda url: (_ for _ in ()).throw(RuntimeError(url)),
            )

        self.assertEqual(result.review_statuses[0].status, "EXCLUDED_EMPLOYER")
        self.assertEqual(len(result.jobs_added), 0)

    def test_company_careers_discovery_flags_acceptable_agency_for_manual_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "Job Database"
            generated_on = date(2026, 8, 19)
            seed = DailyJobRecord(
                companyName="Apex Systems",
                jobTitle="Software Engineer",
                jobUrl="https://builtin.com/job/123",
                applicationUrl="https://builtin.com/job/123",
                source="Built In",
                location="Remote",
                remote=True,
                matchedSkills=("C#", ".NET"),
                rank=7,
            )
            input_path = merge_and_save_daily_jobs([seed], output_dir=output_dir, generated_on=generated_on)

            result = run_company_careers_discovery(
                input_path=input_path,
                output_dir=output_dir,
                fetcher=lambda url: self.fail(f"Unexpected fetch for {url}"),
            )

        self.assertEqual(result.review_statuses[0].status, "MANUAL_VERIFICATION")
        self.assertEqual(result.failed_companies, {})
        self.assertEqual(len(result.jobs_added), 0)

    def test_company_careers_scan_reports_limit_reached(self) -> None:
        seed = sample_job("Built In", company="Example")
        pages = {
            "https://example.com/careers": """
                <html>
                  <a href="/jobs/1">Job 1</a>
                  <a href="/jobs/2">Job 2</a>
                </html>
            """,
        }

        result = scan_company_careers(
            seed,
            ["https://example.com/careers"],
            limit_pages=1,
            fetcher=lambda url: pages[url],
        )

        self.assertEqual(result.status, "LIMIT_REACHED")
        self.assertEqual(result.pages_reviewed, 1)

    def test_company_careers_scan_reports_possible_js_pagination(self) -> None:
        seed = sample_job("Built In", company="Example")
        pages = {
            "https://example.com/careers": '<html><button>Load more jobs</button></html>',
        }

        result = scan_company_careers(
            seed,
            ["https://example.com/careers"],
            limit_pages=5,
            fetcher=lambda url: pages[url],
        )

        self.assertEqual(result.status, "POSSIBLE_JS_PAGINATION")
        self.assertEqual(result.pages_reviewed, 1)

    def test_company_careers_scan_follows_search_jobs_form_action_without_query(self) -> None:
        seed = DailyJobRecord(
            companyName="Example",
            jobTitle="Software Engineer",
            jobUrl="https://builtin.com/job/123",
            applicationUrl="https://builtin.com/job/123",
            source="Built In",
            location="Remote",
            remote=True,
            matchedSkills=("C#", ".NET", "React"),
        )
        pages = {
            "https://example.com/careers": """
                <html>
                  <form action="/jobs">
                    <input placeholder="Keyword">
                    <input placeholder="Location">
                    <button>Search Jobs</button>
                  </form>
                </html>
            """,
            "https://example.com/jobs": '<html><a href="/jobs/2">Senior Software Engineer</a></html>',
            "https://example.com/jobs/2": """
                <html>
                  <script type="application/ld+json">
                  {
                    "@context": "https://schema.org",
                    "@type": "JobPosting",
                    "title": "Software Engineer",
                    "url": "https://example.com/jobs/2",
                    "hiringOrganization": {"name": "Example"},
                    "jobLocationType": "TELECOMMUTE",
                    "description": "Remote role building C# .NET React Azure systems."
                  }
                  </script>
                </html>
            """,
        }

        result = scan_company_careers(
            seed,
            ["https://example.com/careers"],
            limit_pages=5,
            fetcher=lambda url: pages[url],
        )

        self.assertEqual(result.status, "FULLY_REVIEWED")
        self.assertEqual(len(result.jobs), 1)

    def test_company_careers_scan_follows_next_pagination_link(self) -> None:
        seed = DailyJobRecord(
            companyName="Example",
            jobTitle="Software Engineer",
            jobUrl="https://builtin.com/job/123",
            applicationUrl="https://builtin.com/job/123",
            source="Built In",
            location="Remote",
            remote=True,
            matchedSkills=("C#", ".NET", "React"),
        )
        pages = {
            "https://example.com/careers": '<html><a href="/careers?page=2">Next</a></html>',
            "https://example.com/careers?page=2": """
                <html>
                  <script type="application/ld+json">
                  {
                    "@context": "https://schema.org",
                    "@type": "JobPosting",
                    "title": "Software Engineer",
                    "url": "https://example.com/careers?page=2",
                    "hiringOrganization": {"name": "Example"},
                    "jobLocationType": "TELECOMMUTE",
                    "description": "Remote role building C# .NET React Azure systems."
                  }
                  </script>
                </html>
            """,
        }

        result = scan_company_careers(
            seed,
            ["https://example.com/careers"],
            limit_pages=5,
            fetcher=lambda url: pages[url],
        )

        self.assertEqual(result.status, "FULLY_REVIEWED")
        self.assertEqual(len(result.jobs), 1)

    def test_company_careers_scan_follows_software_engineering_category_link(self) -> None:
        seed = DailyJobRecord(
            companyName="Example",
            jobTitle="Software Engineer",
            jobUrl="https://builtin.com/job/123",
            applicationUrl="https://builtin.com/job/123",
            source="Built In",
            location="Remote",
            remote=True,
            matchedSkills=("C#", ".NET", "React"),
        )
        pages = {
            "https://example.com/careers": '<html><a href="/careers/software-engineering">Software Engineering</a></html>',
            "https://example.com/careers/software-engineering": '<html><a href="/jobs/2">Senior Software Engineer</a></html>',
            "https://example.com/jobs/2": """
                <html>
                  <script type="application/ld+json">
                  {
                    "@context": "https://schema.org",
                    "@type": "JobPosting",
                    "title": "Software Engineer",
                    "url": "https://example.com/jobs/2",
                    "hiringOrganization": {"name": "Example"},
                    "jobLocationType": "TELECOMMUTE",
                    "description": "Remote role building C# .NET React Azure systems."
                  }
                  </script>
                </html>
            """,
        }

        result = scan_company_careers(
            seed,
            ["https://example.com/careers"],
            limit_pages=5,
            fetcher=lambda url: pages[url],
        )

        self.assertEqual(result.status, "FULLY_REVIEWED")
        self.assertEqual(len(result.jobs), 1)


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


def sample_job(
    source: str,
    *,
    company: str = "Example",
    rank: int = 1,
    salary: str | None = None,
) -> DailyJobRecord:
    return DailyJobRecord(
        companyName=company,
        jobTitle="Software Engineer",
        jobUrl=f"https://{company.lower().replace(' ', '')}.example/jobs/1",
        applicationUrl=f"https://{company.lower().replace(' ', '')}.example/apply/1",
        source=source,
        location="Remote",
        remote=True,
        salary=salary,
        rank=rank,
    )


if __name__ == "__main__":
    unittest.main()

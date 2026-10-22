import json

from app.models.memory import EvidencePointer
from app.models.onboarding import (
    DraftClaim,
    DraftEvidence,
    FileClaimsDraft,
    RepositoryClaimDraft,
    RepositoryClaimsDraft,
)
from app.onboarding.explore import chunk_ranges, explore, git_commit
from app.onboarding.generate import build_memory
from app.services.repositories import REPO_ROOT, content_hash, get_citation_excerpt


class FakeFileGenerator:
    """Cites real lines for src/auth.py and out-of-range lines everywhere else."""

    def __init__(self):
        self.paths = []

    def invoke(self, messages):
        path = json.loads(messages[1][1])["path"]
        self.paths.append(path)
        if path == "src/auth.py":
            evidence = [
                DraftEvidence(start_line=4, end_line=8),
                DraftEvidence(start_line=90, end_line=99),
            ]
        else:
            evidence = [DraftEvidence(start_line=500, end_line=510)]
        return FileClaimsDraft(
            claims=[
                DraftClaim(
                    title=f"About {path}",
                    text=f"{path} does something.",
                    keywords=["demo"],
                    evidence=evidence,
                )
            ]
        )


class FakeRepositoryGenerator:
    def invoke(self, messages):
        return RepositoryClaimsDraft(
            claims=[
                RepositoryClaimDraft(
                    title="Auth flow",
                    text="Routes call the auth helper.",
                    keywords=["auth"],
                    supporting_claim_ids=["src.auth-001", "made-up-id"],
                ),
                RepositoryClaimDraft(
                    title="Unsupported",
                    text="Cites only ids that don't exist.",
                    keywords=[],
                    supporting_claim_ids=["made-up-id"],
                ),
            ]
        )


def onboard_demo():
    file_generator = FakeFileGenerator()
    memory = build_memory(
        "demo-repo",
        REPO_ROOT,
        snapshot_id="demo-snapshot-v2",
        workers=2,
        file_generator=file_generator,
        repository_generator=FakeRepositoryGenerator(),
    )
    return memory, file_generator


def test_demo_fixture_is_not_mistaken_for_a_git_checkout():
    # demo_repo sits inside the project's own git repository.
    assert git_commit(REPO_ROOT) is None
    assert explore(REPO_ROOT).files == ("src/auth.py", "src/config.py", "src/routes.py")


def test_build_memory_keeps_only_verified_evidence():
    memory, file_generator = onboard_demo()

    assert sorted(file_generator.paths) == [
        "src/auth.py",
        "src/config.py",
        "src/routes.py",
    ]
    file_claims = [c for c in memory.claims if c.level == "file"]
    # Claims for config.py and routes.py had only out-of-range evidence.
    assert [c.claim_id for c in file_claims] == ["src.auth-001"]
    [pointer] = file_claims[0].evidence
    assert (pointer.path, pointer.start_line, pointer.end_line) == ("src/auth.py", 4, 8)
    excerpt = get_citation_excerpt(
        EvidencePointer(path="src/auth.py", start_line=4, end_line=8)
    )
    assert pointer.content_hash == content_hash(excerpt)


def test_repository_claims_reuse_file_claim_evidence():
    memory, _ = onboard_demo()

    repository_claims = [c for c in memory.claims if c.level == "repository"]
    assert [c.claim_id for c in repository_claims] == ["repository-001"]
    assert repository_claims[0].evidence == memory.claims[1].evidence
    assert memory.claims[0] is repository_claims[0]


def test_build_memory_records_snapshot_and_cost():
    memory, _ = onboard_demo()

    assert memory.snapshot_id == "demo-snapshot-v2"
    assert memory.build_cost is not None
    assert memory.build_cost.model
    assert memory.build_cost.elapsed_s >= 0


def test_chunks_cut_before_decorated_definitions():
    lines = ["import x", ""]
    for i in range(6):
        lines += [
            "@decorator(",
            "    arg,",
            ")",
            f"def f{i}():",
            "    return 1",
            "",
        ]

    ranges = chunk_ranges(lines, max_lines=10)

    assert ranges[0][0] == 1 and ranges[-1][1] == len(lines)
    for (_, end), (start, _) in zip(ranges, ranges[1:]):
        assert start == end + 1
        assert lines[start - 1] == "@decorator("
    assert all(end - start < 10 for start, end in ranges)

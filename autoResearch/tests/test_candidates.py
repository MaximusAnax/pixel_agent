"""Candidate schema: strict keys, validation, hashing, overrides."""

import pytest

from auto_research.candidates import (
  Candidate,
  apply_overrides,
  candidate_from_dict,
)


def test_roundtrip_and_hash_stability():
  cand = candidate_from_dict({"name": "x"})
  assert cand.content_hash() == candidate_from_dict({"name": "x"}).content_hash()


def test_notes_do_not_change_hash():
  a = candidate_from_dict({"name": "x", "notes": "one"})
  b = candidate_from_dict({"name": "x", "notes": "two"})
  assert a.content_hash() == b.content_hash()


def test_param_change_changes_hash():
  a = candidate_from_dict({"name": "x"})
  b = candidate_from_dict({"name": "x", "detectors": {"min_repeat": 2}})
  assert a.content_hash() != b.content_hash()


def test_unknown_keys_rejected():
  with pytest.raises(ValueError, match="Unknown keys"):
    candidate_from_dict({"name": "x", "detectors": {"magic": 1}})
  with pytest.raises(ValueError, match="Unknown keys"):
    candidate_from_dict({"name": "x", "sneaky_new_section": {}})


def test_validation_bounds():
  with pytest.raises(ValueError):
    candidate_from_dict({"name": "x", "detectors": {"min_repeat": 1}})
  with pytest.raises(ValueError):
    candidate_from_dict({"name": "x", "judge": {"protocol": "v3"}})
  with pytest.raises(ValueError):
    candidate_from_dict({"name": "x", "detectors": {"order": ["not_a_detector"]}})


def test_apply_overrides_is_nondestructive():
  base = candidate_from_dict({"name": "base"})
  new = apply_overrides(base, {"detectors": {"min_repeat": 2}}, name="mut")
  assert isinstance(new, Candidate)
  assert new.detectors.min_repeat == 2
  assert base.detectors.min_repeat == 3
  assert new.name == "mut"

# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path
import platform
import re

import pytest
import typing
from pprint import pprint

from clouddq import lib
from clouddq import utils
from clouddq.classes.dq_entity import DqEntity
from clouddq.classes.dq_row_filter import DqRowFilter
from clouddq.classes.dq_rule import DqRule
from clouddq.classes.dq_rule_binding import DqRuleBinding
from clouddq.classes.rule_type import RuleType

RE_NEWLINES = r"(\n( )*)+"
RE_CONFIGS_HASHSUM = r"'[\w\d]+' AS configs_hashsum,"
CONFIGS_HASHSUM_REP = "'' AS configs_hashsum,"


def replace_expected_sql_table(
    sql_string, entities_collection, rule_binding_configs
) -> str:
    entity_id = rule_binding_configs.get("entity_id")
    database_name = entities_collection.get(entity_id).get("database_name")
    instance_name = entities_collection.get(entity_id).get("instance_name")
    output = sql_string.replace(
        "kthxbayes-sandbox.dq_test", f"{instance_name}.{database_name}"
    )
    return output


class TestJinjaTemplates:
    """ """

    @pytest.fixture
    def test_entities_collection(self):
        """ """
        return lib.load_entities_config(configs_path=Path("configs"))

    def test_dq_entities_class(self, test_entities_collection):
        """

        Args:
          test_entities_collection:

        Returns:

        """
        for key, value in test_entities_collection.items():
            entity = DqEntity.from_dict(entity_id=key, kwargs=value)
            assert key in entity.to_dict()
            assert dict(entity.dict_values()) == dict(value)

    @pytest.fixture
    def test_rules_collection(self):
        """ """
        return lib.load_rules_config(configs_path=Path("configs"))

    def test_rules_class(self, test_rules_collection):
        """

        Args:
          test_rules_collection:

        Returns:

        """
        for key, value in test_rules_collection.items():
            if value["rule_type"] == RuleType.CUSTOM_SQL_STATEMENT:
                continue
            rule = DqRule.from_dict(rule_id=key, kwargs=value)
            assert key in rule.to_dict()
            value.update({"rule_sql_expr": rule.resolve_sql_expr()})
            if "params" not in value:
                value.update({"params": {}})
            assert dict(rule.dict_values()) == dict(value)

    @pytest.fixture
    def test_row_filters_collection(self):
        """ """
        return lib.load_row_filters_config(configs_path=Path("configs"))

    def test_filters_class(self, test_row_filters_collection):
        """

        Args:
          test_row_filters_collection:

        Returns:

        """
        for key, value in test_row_filters_collection.items():
            dq_filter = DqRowFilter.from_dict(row_filter_id=key, kwargs=value)
            assert key in dq_filter.to_dict()
            assert dict(dq_filter.dict_values()) == dict(value)

    @pytest.fixture
    def test_dq_summary_rule_bindings_collection(self):
        """ """
        return lib.load_rule_bindings_config(
            Path("configs/rule_bindings/dq-summary-table-rule-bindings.yml")
        )

    def test_resolve_time_filter_column(self, test_dq_summary_rule_bindings_collection):
        """ """
        pprint(test_dq_summary_rule_bindings_collection)
        first_rule_binding_config = (
            test_dq_summary_rule_bindings_collection.values().__iter__().__next__()
        )
        entities_configs = lib.load_entities_config(configs_path=Path("configs"))
        rule_binding = DqRuleBinding.from_dict(
            rule_binding_id="dq_summary",
            kwargs=first_rule_binding_config,
        )
        entity = rule_binding.resolve_table_entity_config(entities_configs)
        entity.resolve_column_config(rule_binding.incremental_time_filter_column_id)
        with pytest.raises(ValueError):
            entity.resolve_column_config("invalid_column")

    @pytest.fixture
    def test_rule_bindings_collection_team_2(self):
        """ """
        return lib.load_rule_bindings_config(
            Path("configs/rule_bindings/team-2-rule-bindings.yml")
        )

    @pytest.fixture
    def test_rule_bindings_collection_team_3(self):
        """ """
        return lib.load_rule_bindings_config(
            Path("configs/rule_bindings/team-3-rule-bindings.yml")
        )

    @pytest.fixture
    def test_rule_bindings_collection_dq_summary(self):
        """ """
        return lib.load_rule_bindings_config(
            Path("configs/rule_bindings/dq-summary-table-rule-bindings.yml")
        )

    def test_rule_bindings_class(self, test_rule_bindings_collection_team_2):
        """

        Args:
          test_rule_bindings_collection_team_2:

        Returns:

        """
        for key, value in test_rule_bindings_collection_team_2.items():
            rule_binding = DqRuleBinding.from_dict(rule_binding_id=key, kwargs=value)
            assert key in rule_binding.to_dict()
            if "metadata" not in value:
                value.update({"metadata": {}})
            if "incremental_time_filter_column_id" not in value:
                value.update({"incremental_time_filter_column_id": None})
            assert dict(rule_binding.dict_values()) == dict(value)

    def test_rule_bindings_class_resolve_configs(
        self,
        test_rule_bindings_collection_team_2,
        test_entities_collection,
        test_rules_collection,
        test_row_filters_collection,
    ):
        """

        Args:
          test_rule_bindings_collection_team_2:

        Returns:

        """
        for key, value in test_rule_bindings_collection_team_2.items():
            rule_binding = DqRuleBinding.from_dict(rule_binding_id=key, kwargs=value)
            rule_binding.resolve_table_entity_config(
                entities_collection=test_entities_collection
            )
            rule_binding.resolve_rule_config_list(
                rules_collection=test_rules_collection
            )
            rule_binding.resolve_row_filter_config(
                row_filters_collection=test_row_filters_collection
            )
            rule_binding.resolve_all_configs_to_dict(
                entities_collection=test_entities_collection,
                rules_collection=test_rules_collection,
                row_filters_collection=test_row_filters_collection,
            )

    @pytest.fixture
    def test_all_rule_bindings_collections(self):
        """ """
        return lib.load_rule_bindings_config(configs_path=Path("configs"))

    def test_load_rule_bindings_valid(self, test_all_rule_bindings_collections):
        """

        Args:
          test_all_rule_bindings_collections:

        Returns:

        """
        self.test_rule_bindings_class(test_all_rule_bindings_collections)

    def test_render_run_dq_main_sql(
        self,
        test_rule_bindings_collection_team_2,
        test_entities_collection,
        test_rules_collection,
        test_row_filters_collection,
    ):
        """

        Args:
          test_rule_bindings_collection_team_2:
          test_entities_collection:
          test_rules_collection:
          test_row_filters_collection:

        Returns:

        """
        with open("tests/resources/test_render_run_dq_main_sql_expected.sql") as f:
            expected = f.read()
        rule_binding_id, rule_binding_configs = (
            test_rule_bindings_collection_team_2.items()
            .__iter__()
            .__next__()  # use first rule binding
        )
        output = lib.create_rule_binding_view_model(
            configs_path=Path("configs"),
            rule_binding_id=rule_binding_id,
            rule_binding_configs=rule_binding_configs,
            dq_summary_table_name="kthxbayes-sandbox.dq_test.dq_summary",
            entities_collection=test_entities_collection,
            rules_collection=test_rules_collection,
            row_filters_collection=test_row_filters_collection,
            environment="DEV",
            debug=True,
        )
        expected = replace_expected_sql_table(
            sql_string=expected,
            entities_collection=test_entities_collection,
            rule_binding_configs=rule_binding_configs,
        )
        expected = utils.strip_margin(re.sub(RE_NEWLINES, '\n', expected)).strip()
        output = re.sub(RE_NEWLINES, '\n', output).strip()
        output = re.sub(RE_CONFIGS_HASHSUM, CONFIGS_HASHSUM_REP, output)
        assert output == expected

    def test_render_run_dq_main_sql_env_override(
        self,
        test_rule_bindings_collection_team_2,
        test_entities_collection,
        test_rules_collection,
        test_row_filters_collection,
    ):
        """

        Args:
          test_rule_bindings_collection_team_2:
          test_entities_collection:
          test_rules_collection:
          test_row_filters_collection:

        Returns:

        """
        with open("tests/resources/test_render_run_dq_main_sql_expected.sql") as f:
            expected = f.read()
        rule_binding_id, rule_binding_configs = (
            test_rule_bindings_collection_team_2.items()
            .__iter__()
            .__next__()  # use first rule binding
        )
        output = lib.create_rule_binding_view_model(
            configs_path=Path("configs"),
            rule_binding_id=rule_binding_id,
            rule_binding_configs=rule_binding_configs,
            dq_summary_table_name="kthxbayes-sandbox.dq_test.dq_summary",
            entities_collection=test_entities_collection,
            rules_collection=test_rules_collection,
            row_filters_collection=test_row_filters_collection,
            environment="TEST",
            debug=True,
        )
        expected = expected.replace(
            "kthxbayes-sandbox.dq_test", "does_not_exists.does_not_exists"
        )
        expected = utils.strip_margin(re.sub(RE_NEWLINES, '\n', expected)).strip()
        output = re.sub(RE_NEWLINES, '\n', output).strip()
        output = re.sub(RE_CONFIGS_HASHSUM, CONFIGS_HASHSUM_REP, output)
        assert output == expected

    def test_render_run_dq_main_sql_high_watermark(
        self,
        test_rule_bindings_collection_dq_summary,
        test_entities_collection,
        test_rules_collection,
        test_row_filters_collection,
    ):
        """

        Args:
          test_rule_bindings_collection_dq_summary:
          test_entities_collection:
          test_rules_collection:
          test_row_filters_collection:

        Returns:

        """
        with open(
            "tests/resources/test_render_run_dq_main_sql_expected_high_watermark.sql",
        ) as f:
            expected = f.read()
        rule_binding_id, rule_binding_configs = (
            test_rule_bindings_collection_dq_summary.items()
            .__iter__()
            .__next__()  # use first rule binding
        )
        output = lib.create_rule_binding_view_model(
            configs_path=Path("configs"),
            rule_binding_id=rule_binding_id,
            rule_binding_configs=rule_binding_configs,
            dq_summary_table_name="kthxbayes-sandbox.dq_test.dq_summary",
            entities_collection=test_entities_collection,
            rules_collection=test_rules_collection,
            row_filters_collection=test_row_filters_collection,
            environment="DEV",
            debug=True,
        )
        expected = replace_expected_sql_table(
            sql_string=expected,
            entities_collection=test_entities_collection,
            rule_binding_configs=rule_binding_configs,
        )
        expected = utils.strip_margin(re.sub(RE_NEWLINES, '\n', expected)).strip()
        output = re.sub(RE_NEWLINES, '\n', output).strip()
        output = re.sub(RE_CONFIGS_HASHSUM, CONFIGS_HASHSUM_REP, output)
        assert output == expected

    def test_render_run_dq_main_sql_custom_sql_statement(
        self,
        test_rule_bindings_collection_team_3,
        test_entities_collection,
        test_rules_collection,
        test_row_filters_collection,
    ):
        """

        Args:
          test_rule_bindings_collection_team_3:
          test_entities_collection:
          test_rules_collection:
          test_row_filters_collection:

        Returns:

        """
        with open(
            "tests/resources/test_render_run_dq_main_sql_expected_custom_sql_statement.sql",
        ) as f:
            expected = f.read()
        rule_binding_id, rule_binding_configs = (
            test_rule_bindings_collection_team_3.items()
            .__iter__()
            .__next__()  # use first rule binding
        )
        output = lib.create_rule_binding_view_model(
            configs_path=Path("configs"),
            rule_binding_id=rule_binding_id,
            rule_binding_configs=rule_binding_configs,
            dq_summary_table_name="kthxbayes-sandbox.dq_test.dq_summary",
            entities_collection=test_entities_collection,
            rules_collection=test_rules_collection,
            row_filters_collection=test_row_filters_collection,
            environment="DEV",
            debug=True,
        )
        expected = replace_expected_sql_table(
            sql_string=expected,
            entities_collection=test_entities_collection,
            rule_binding_configs=rule_binding_configs,
        )
        expected = utils.strip_margin(re.sub(RE_NEWLINES, '\n', expected)).strip()
        output = re.sub(RE_NEWLINES, '\n', output).strip()
        output = re.sub(RE_CONFIGS_HASHSUM, CONFIGS_HASHSUM_REP, output)
        assert output == expected

    def test_prepare_configs_from_rule_binding(
        self, test_rule_bindings_collection_team_2
    ):
        """ """
        rule_binding_id, rule_binding_configs = (
            test_rule_bindings_collection_team_2.items()
            .__iter__()
            .__next__()  # use first rule binding
        )
        env = "DEV"
        metadata = {"channel": "two"}
        configs = lib.prepare_configs_from_rule_binding_id(
            rule_binding_id=rule_binding_id,
            rule_binding_configs=rule_binding_configs,
            dq_summary_table_name="kthxbayes-sandbox.dq_test.dq_summary",
            environment=env,
            metadata=metadata,
            configs_path=Path("configs"),
        )
        pprint(json.dumps(configs["configs"]))
        with open("tests/resources/expected_configs.json") as f:
            expected_configs = json.loads(f.read())
        assert configs["configs"] == dict(expected_configs)
        metadata.update(rule_binding_configs["metadata"])
        assert configs["metadata"] == dict(metadata)
        assert configs["environment"] == env

    def test_load_configs(self):
        """ """
        (
            entities_collection,
            row_filters_collection,
            rules_collection,
        ) = lib.load_configs_if_not_defined(configs_path=Path("configs"))
        assert len(entities_collection) > 0
        assert len(row_filters_collection) > 0
        assert len(rules_collection) > 0


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))

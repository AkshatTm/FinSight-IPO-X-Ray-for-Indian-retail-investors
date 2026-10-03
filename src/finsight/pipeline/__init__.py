"""Pipeline steps shared by the offline build CLI (``python -m finsight.pipeline``) and the upload
worker: today the Risk Factors split used by the ``risks_split`` stage."""

from finsight.pipeline.risks_stage import RISKS, RISKS_FILE, split_risks, table_boxes

__all__ = ["RISKS", "RISKS_FILE", "split_risks", "table_boxes"]

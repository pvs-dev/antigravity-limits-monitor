import json
import re
import ssl
import subprocess
import urllib.request
from datetime import datetime, timezone
from typing import Tuple, Optional, List, Dict, Any

from .models import ModelQuota, PlanStatus, AccountStatus
from .config import AppConfig


class QuotaCollector:
    def __init__(self, config: AppConfig):
        self.config = config
        self._cached_pid: Optional[int] = None
        self._cached_token: Optional[str] = None
        self._cached_ports: List[int] = []
        self._cached_working_port: Optional[int] = None
        self._cached_working_proto: Optional[str] = None
        
        # SSL Context for HTTPS calls without verification on localhost
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

    def discover_process(self) -> Tuple[Optional[int], Optional[str], List[int]]:
        """Finds language_server PID, CSRF token, and listening ports on Windows."""
        if self.config.manual_mode and self.config.manual_port > 0:
            return None, self.config.manual_token, [self.config.manual_port]

        try:
            # 1. Query Win32_Process for language_server
            ps_proc_cmd = (
                'Get-CimInstance Win32_Process | '
                'Where-Object { $_.Name -match "language_server" } | '
                'Select-Object ProcessId, CommandLine | '
                'ConvertTo-Json'
            )
            res = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_proc_cmd],
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            if not res.strip():
                return None, None, []

            proc_data = json.loads(res)
            if isinstance(proc_data, list):
                proc_data = proc_data[0]

            pid = proc_data.get("ProcessId")
            cmd = proc_data.get("CommandLine", "")

            # Extract CSRF token
            token_match = re.search(r"--csrf_token\s+([a-f0-9\-]+)", cmd)
            csrf_token = token_match.group(1) if token_match else None

            if not pid or not csrf_token:
                return None, None, []

            # 2. Query listening TCP ports for this PID
            ps_net_cmd = (
                f'Get-NetTCPConnection -OwningProcess {pid} -State Listen | '
                'Select-Object -ExpandProperty LocalPort'
            )
            ports_res = subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_net_cmd],
                text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            ports = [int(p.strip()) for p in ports_res.strip().split() if p.strip().isdigit()]

            return pid, csrf_token, ports
        except Exception as e:
            print(f"Process discovery failed: {e}")
            return None, None, []

    def fetch_status(self) -> AccountStatus:
        """Queries the language_server and returns the current AccountStatus."""
        # Try previously working port/proto first for speed
        if self._cached_working_port and self._cached_token and self._cached_working_proto:
            status = self._query_endpoint(
                self._cached_working_proto,
                self._cached_working_port,
                self._cached_token,
                self._cached_pid
            )
            if status.is_connected:
                return status

        # If cache failed, perform full discovery
        pid, token, ports = self.discover_process()
        if not ports or (not token and not self.config.manual_mode):
            return AccountStatus(
                is_connected=False,
                error_message="Antigravity language_server не найден или не запущен."
            )

        self._cached_pid = pid
        self._cached_token = token
        self._cached_ports = ports

        # Try discovered ports
        for port in ports:
            for proto in ["http", "https"]:
                status = self._query_endpoint(proto, port, token or "", pid)
                if status.is_connected:
                    self._cached_working_port = port
                    self._cached_working_proto = proto
                    return status

        return AccountStatus(
            is_connected=False,
            pid=pid,
            csrf_token=token,
            error_message="Не удалось подключиться к RPC порту language_server."
        )

    def _query_endpoint(
        self, proto: str, port: int, token: str, pid: Optional[int]
    ) -> AccountStatus:
        url = f"{proto}://127.0.0.1:{port}/exa.language_server_pb.LanguageServerService/GetUserStatus"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "X-Codeium-Csrf-Token": token,
                "Connect-Protocol-Version": "1",
            }
        )
        try:
            with urllib.request.urlopen(
                req,
                context=self._ssl_ctx if proto == "https" else None,
                timeout=2.5
            ) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return self._parse_response(data, pid, port, token)
        except Exception as e:
            pass
        return AccountStatus(is_connected=False)

    def _parse_response(
        self, data: Dict[str, Any], pid: Optional[int], port: int, token: str
    ) -> AccountStatus:
        user_status = data.get("userStatus", {})
        name = user_status.get("name", "").strip()
        email = user_status.get("email", "").strip()

        # Plan Info
        plan_dict = user_status.get("planStatus", {})
        plan_info_dict = plan_dict.get("planInfo", {})
        plan = PlanStatus(
            plan_name=plan_info_dict.get("planName", "Pro"),
            teams_tier=plan_info_dict.get("teamsTier", ""),
            monthly_prompt_credits=plan_info_dict.get("monthlyPromptCredits", 0),
            monthly_flow_credits=plan_info_dict.get("monthlyFlowCredits", 0),
            available_prompt_credits=plan_dict.get("availablePromptCredits", 0),
            available_flow_credits=plan_dict.get("availableFlowCredits", 0),
        )

        # Models & Quotas
        raw_configs = user_status.get("cascadeModelConfigData", {}).get("clientModelConfigs", [])
        models: List[ModelQuota] = []

        for item in raw_configs:
            label = item.get("label", "").strip()
            if not label:
                continue
            quota_dict = item.get("quotaInfo", {})
            rem_frac = quota_dict.get("remainingFraction", 1.0)
            reset_time = quota_dict.get("resetTime")
            model_id = item.get("modelOrAlias", {}).get("model", "")
            tag_title = item.get("tagTitle", "")
            is_rec = item.get("isRecommended", False)

            models.append(ModelQuota(
                label=label,
                remaining_fraction=float(rem_frac) if rem_frac is not None else 1.0,
                reset_time=reset_time,
                model_id=model_id,
                tag_title=tag_title,
                is_recommended=is_rec,
            ))

        # Process grouping if enabled
        final_models = self._process_models(models)

        return AccountStatus(
            is_connected=True,
            name=name,
            email=email,
            plan=plan,
            models=final_models,
            last_updated=datetime.now(),
            pid=pid,
            port=port,
            csrf_token=token,
        )

    def _process_models(self, models: List[ModelQuota]) -> List[ModelQuota]:
        """Groups similar model tiers and deterministically sorts them."""
        # 1. Clean & group
        grouped: Dict[str, ModelQuota] = {}
        for m in models:
            if self.config.group_similar_models:
                # Clean base name, removing (High), (Medium), (Low), (Thinking)
                base_label = re.sub(r"\s*\((High|Medium|Low|Thinking)\)", "", m.label).strip()
            else:
                base_label = m.label.strip()

            if base_label in self.config.hidden_models:
                continue

            if base_label not in grouped:
                grouped[base_label] = ModelQuota(
                    label=base_label,
                    remaining_fraction=m.remaining_fraction,
                    reset_time=m.reset_time,
                    model_id=m.model_id,
                    tag_title=m.tag_title,
                    is_recommended=m.is_recommended,
                )
            else:
                existing = grouped[base_label]
                if m.remaining_fraction < existing.remaining_fraction:
                    existing.remaining_fraction = m.remaining_fraction
                if m.reset_time and not existing.reset_time:
                    existing.reset_time = m.reset_time

        # 2. Deterministic stable sorting function
        def get_sort_key(item: ModelQuota) -> tuple:
            lbl = item.label.lower()
            if "3.7" in lbl:
                tier = 1
            elif "3.6" in lbl:
                tier = 2
            elif "3.5" in lbl:
                tier = 3
            elif "3.1" in lbl:
                tier = 4
            elif "gemini" in lbl:
                tier = 5
            elif "sonnet" in lbl:
                tier = 10
            elif "opus" in lbl:
                tier = 11
            elif "claude" in lbl:
                tier = 12
            elif "gpt" in lbl:
                tier = 20
            else:
                tier = 30
            return (tier, item.label)

        result = list(grouped.values())
        result.sort(key=get_sort_key)
        return result


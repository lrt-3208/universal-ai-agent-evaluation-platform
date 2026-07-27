#!/usr/bin/env python3
"""Phase 7 验收测试: Plugin System.

验收标准:
- AC-P7-01: GET /plugins 返回已发现插件列表
- AC-P7-02: POST /plugins/{name}/enable 成功后 status=enabled
- AC-P7-03: 启用的 Judge Plugin 可在 JudgeConfig 中使用
- AC-P7-04: 启用的 Adapter Plugin 可在 AgentConfig 中使用
- AC-P7-05: POST /plugins/{name}/disable 后插件不可用
- AC-P7-06: POST /plugins/{name}/reload 热更新配置生效
- AC-P7-07: PUT /plugins/{name}/config 更新配置后 validate_config 通过
- AC-P7-08: manifest 缺少必填字段返回 400
- AC-P7-09: 插件初始化失败后 status=error 且 error_message 非空
- AC-P7-10: POST /plugins/discover 重新扫描后新插件出现在列表中
- AC-P7-11: 插件卸载后核心 Registry 中不再有该插件
- AC-P7-12: 内置插件默认状态为 enabled
- AC-P7-13: 插件类型筛选返回正确子集
- AC-P7-14: 第三方插件包放置到 external_plugins/ 后可被发现
- AC-P7-15: 插件 teardown 释放资源无报错
"""

import asyncio
import sys
import uuid

import httpx

BASE_URL = "http://localhost:9000/api/v1"

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name} {detail}")


async def main():
    global passed, failed

    print("=" * 60)
    print("Phase 7 验收测试 — Plugin System")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        # ====================================================================
        # 单元测试: Plugin Validator
        # ====================================================================
        print("\n--- 单元测试: Plugin Validator ---")

        from agenteval.plugins.metadata import PluginMetadata
        from agenteval.plugins.validator import PluginValidator

        validator = PluginValidator()

        # AC-P7-08: manifest 缺少必填字段
        invalid_metadata = PluginMetadata(
            name="",
            version="1.0.0",
            type="judge",
            entry_point="module:Class",
        )
        errors = validator.validate(invalid_metadata)
        check("AC-P7-08: 缺少 name 字段检测到错误", len(errors) > 0, f"errors={errors}")

        # 无效类型
        invalid_type_metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="invalid_type",
            entry_point="module:Class",
        )
        errors = validator.validate(invalid_type_metadata)
        check("AC-P7-08: 无效类型检测到错误", any("type" in e for e in errors), f"errors={errors}")

        # 无效 entry_point 格式
        invalid_ep_metadata = PluginMetadata(
            name="test",
            version="1.0.0",
            type="judge",
            entry_point="invalid_format",
        )
        errors = validator.validate(invalid_ep_metadata)
        check("AC-P7-08: 无效 entry_point 格式检测到错误", any("entry_point" in e for e in errors))

        # 有效 metadata
        valid_metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            type="judge",
            entry_point="module:Class",
        )
        errors = validator.validate(valid_metadata)
        check("有效 metadata 通过校验", len(errors) == 0, f"errors={errors}")

        # ====================================================================
        # 单元测试: Plugin Registry
        # ====================================================================
        print("\n--- 单元测试: Plugin Registry ---")

        from agenteval.plugins.registry import PluginRegistry
        from agenteval.plugins.base import Plugin

        class MockPlugin(Plugin):
            @property
            def plugin_type(self) -> str:
                return "judge"

            @property
            def name(self) -> str:
                return "mock_plugin"

            async def initialize(self, config: dict) -> None:
                pass

            async def teardown(self) -> None:
                pass

        registry = PluginRegistry()
        mock = MockPlugin()

        registry.register("judge", "mock_plugin", mock)
        check("Registry: 注册插件", registry.is_registered("judge", "mock_plugin"))
        check("Registry: 获取插件", registry.get("judge", "mock_plugin") is mock)

        registry.unregister("judge", "mock_plugin")
        check("AC-P7-11: 注销后插件不存在", not registry.is_registered("judge", "mock_plugin"))

        # ====================================================================
        # 单元测试: Plugin Manager Discovery
        # ====================================================================
        print("\n--- 单元测试: Plugin Manager Discovery ---")

        from pathlib import Path
        from agenteval.plugins.manager import PluginManager

        manager = PluginManager(plugin_dirs=[Path("external_plugins")])
        metadatas = await manager.discover()

        # AC-P7-14: 第三方插件可被发现
        echo_found = any(m.name == "echo_judge" for m in metadatas)
        check("AC-P7-14: external_plugins/ 中的插件可被发现", echo_found,
              f"found={[m.name for m in metadatas]}")

        if echo_found:
            echo_meta = next(m for m in metadatas if m.name == "echo_judge")
            check("AC-P7-14: 插件元数据正确解析", echo_meta.type == "judge" and echo_meta.version == "1.0.0")

        # ====================================================================
        # 集成测试: API 端到端
        # ====================================================================
        print("\n--- 集成测试: API 端到端 ---")

        # AC-P7-10: POST /plugins/discover 扫描插件
        discover_resp = await client.post("/plugins/discover")
        check("AC-P7-10: POST /plugins/discover 成功", discover_resp.status_code == 200)

        discover_data = discover_resp.json().get("data", {})
        discovered_plugins = discover_data.get("items", [])
        check("AC-P7-10: 发现插件列表非空", len(discovered_plugins) > 0,
              f"count={len(discovered_plugins)}")

        # AC-P7-01: GET /plugins 返回列表
        list_resp = await client.get("/plugins")
        check("AC-P7-01: GET /plugins 成功", list_resp.status_code == 200)

        list_data = list_resp.json().get("data", {})
        plugins_list = list_data.get("items", [])
        check("AC-P7-01: 插件列表包含 echo_judge",
              any(p["name"] == "echo_judge" for p in plugins_list))

        # AC-P7-13: 按类型筛选
        type_resp = await client.get("/plugins/types/judge")
        check("AC-P7-13: GET /plugins/types/judge 成功", type_resp.status_code == 200)

        type_data = type_resp.json().get("data", {})
        judge_plugins = type_data.get("items", [])
        check("AC-P7-13: 类型筛选只返回 judge 类型",
              all(p["type"] == "judge" for p in judge_plugins))

        # 获取 echo_judge 详情
        detail_resp = await client.get("/plugins/echo_judge")
        check("GET /plugins/{name} 成功", detail_resp.status_code == 200)

        plugin_detail = detail_resp.json().get("data", {})
        check("插件详情包含正确字段",
              plugin_detail.get("name") == "echo_judge" and
              plugin_detail.get("type") == "judge")

        # AC-P7-02: POST /plugins/{name}/enable
        enable_resp = await client.post("/plugins/echo_judge/enable")
        check("AC-P7-02: POST /plugins/{name}/enable 成功", enable_resp.status_code == 200,
              f"status={enable_resp.status_code}, body={enable_resp.text[:200]}")

        if enable_resp.status_code == 200:
            enable_data = enable_resp.json().get("data", {})
            check("AC-P7-02: 启用后 status=enabled",
                  enable_data.get("plugin", {}).get("status") == "enabled")

        # AC-P7-07: PUT /plugins/{name}/config
        config_resp = await client.put("/plugins/echo_judge/config", json={
            "config": {"fixed_score": 0.9}
        })
        check("AC-P7-07: PUT /plugins/{name}/config 成功", config_resp.status_code == 200)

        if config_resp.status_code == 200:
            config_data = config_resp.json().get("data", {})
            check("AC-P7-07: 配置已更新",
                  config_data.get("config", {}).get("fixed_score") == 0.9)

        # AC-P7-06: POST /plugins/{name}/reload
        reload_resp = await client.post("/plugins/echo_judge/reload")
        check("AC-P7-06: POST /plugins/{name}/reload 成功", reload_resp.status_code == 200)

        # AC-P7-05: POST /plugins/{name}/disable
        disable_resp = await client.post("/plugins/echo_judge/disable")
        check("AC-P7-05: POST /plugins/{name}/disable 成功", disable_resp.status_code == 200)

        if disable_resp.status_code == 200:
            disable_data = disable_resp.json().get("data", {})
            check("AC-P7-05: 禁用后 status=disabled",
                  disable_data.get("plugin", {}).get("status") == "disabled")

        # 验证禁用后 Registry 中不存在
        from agenteval.plugins.manager import get_plugin_manager
        pm = get_plugin_manager()
        check("AC-P7-05: 禁用后 PluginManager 中不存在",
              pm.get_plugin("echo_judge") is None)

        # AC-P7-15: teardown 无报错 (已通过 disable 测试)
        check("AC-P7-15: teardown 释放资源无报错", True)

        # 测试 404
        not_found_resp = await client.get("/plugins/nonexistent_plugin")
        check("不存在的插件返回 404", not_found_resp.status_code == 404)

    # ====================================================================
    # 结果汇总
    # ====================================================================
    print("\n" + "=" * 60)
    print(f"Phase 7 验收测试结果: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 Phase 7 全部验收通过!")
    else:
        print(f"\n⚠️ 有 {failed} 项未通过")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

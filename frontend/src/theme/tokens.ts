/**
 * 设计令牌 — 唯一定义点
 *
 * Reference: docs/contracts/design-tokens.md
 * 1) antdTheme: antd 标准 token，经 ConfigProvider 注入
 * 2) bizTokens: 业务语义色，常量导出（antd token 不支持自定义键名）
 */
import type { ThemeConfig } from 'antd';

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: '#2F54EB',
    colorSuccess: '#52C41A',
    colorWarning: '#FAAD14',
    colorError: '#F5222D',
    colorInfo: '#1677FF',
    fontFamily: "-apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif",
    fontSize: 14,
    borderRadius: 6,
    borderRadiusLG: 8,
    padding: 16,
    paddingLG: 24,
  },
};

/** 业务语义色（design-tokens §2.2），业务组件/ECharts 从这里 import */
export const bizTokens = {
  colorFlaky: '#722ED1',
  colorScoreHigh: '#52C41A',
  colorScoreMid: '#FAAD14',
  colorScoreLow: '#F5222D',
  colorTraceLLM: '#1677FF',
  colorTraceTool: '#13C2C2',
  colorTraceOther: '#8C8C8C',
  fontFamilyCode: "'SF Mono', Menlo, Consolas, monospace",
  siderWidth: 220,
  siderCollapsedWidth: 64,
  headerHeight: 56,
} as const;

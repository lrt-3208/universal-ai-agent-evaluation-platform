/**
 * Reports Tab — F5.3
 *
 * 生成（202 异步）→ 列表轮询 → 预览（iframe Modal）/ 下载
 * Reference: docs/phases/phase-f5-trace-report.md §2.2
 */
import { useState } from 'react';
import { App, Button, Modal, Space, Table, Tooltip, Typography } from 'antd';
import { DownloadOutlined, EyeOutlined, FileTextOutlined } from '@ant-design/icons';
import { useCreateReport, useReports } from '@/hooks/useTraceReport';
import { reportDownloadUrl, reportPreviewUrl } from '@/api/endpoints/traces';
import type { Report } from '@/api/endpoints/traces';
import { QueryBoundary, StatusTag } from '@/components/common';
import { ApiError } from '@/api/client';

export default function ReportsTab({ evaluationId }: { evaluationId: string }) {
  const { message } = App.useApp();
  const reportsQuery = useReports(evaluationId);
  const createMut = useCreateReport(evaluationId);
  const [previewId, setPreviewId] = useState<string | null>(null);

  const handleCreate = async (format: 'html' | 'json') => {
    try {
      await createMut.mutateAsync(format);
      message.success('报告生成中');
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          icon={<FileTextOutlined />}
          onClick={() => handleCreate('html')}
          loading={createMut.isPending}
          data-testid="gen-html-report-btn"
        >
          生成 HTML 报告
        </Button>
        <Button onClick={() => handleCreate('json')} data-testid="gen-json-report-btn">
          生成 JSON 报告
        </Button>
      </Space>

      <QueryBoundary query={reportsQuery} isEmpty={(d) => d.length === 0} emptyText="暂无报告，点击上方按钮生成">
        {(reports) => (
          <Table
            rowKey="id"
            dataSource={reports}
            pagination={false}
            columns={[
              {
                title: '格式',
                dataIndex: 'format',
                width: 90,
                render: (f: string) => f.toUpperCase(),
              },
              {
                title: '状态',
                dataIndex: 'status',
                width: 110,
                render: (s: string, r: Report) =>
                  s === 'failed' ? (
                    <Tooltip title={String(r.summary ?? '生成失败')}>
                      <span>
                        <StatusTag status={s} />
                      </span>
                    </Tooltip>
                  ) : (
                    <StatusTag status={s} />
                  ),
              },
              {
                title: '摘要',
                render: (_, r: Report) => {
                  const passRate = (r.metrics_snapshot as { pass_rate?: number } | null)?.pass_rate;
                  return passRate != null ? (
                    <Typography.Text style={{ fontSize: 13 }}>
                      通过率 {(passRate * 100).toFixed(0)}%
                    </Typography.Text>
                  ) : (
                    '-'
                  );
                },
              },
              {
                title: '创建时间',
                dataIndex: 'created_at',
                width: 180,
                render: (t: string) => new Date(t).toLocaleString(),
              },
              {
                title: '操作',
                width: 160,
                render: (_, r: Report) =>
                  r.status === 'completed' ? (
                    <Space>
                      {r.format === 'html' && (
                        <a onClick={() => setPreviewId(r.id)} data-testid="preview-report-link">
                          <EyeOutlined /> 预览
                        </a>
                      )}
                      <a href={reportDownloadUrl(r.id)} download data-testid="download-report-link">
                        <DownloadOutlined /> 下载
                      </a>
                    </Space>
                  ) : (
                    '-'
                  ),
              },
            ]}
          />
        )}
      </QueryBoundary>

      {/* 预览 Modal：iframe 加载同源代理路径（phase-f5 §3） */}
      <Modal
        title="报告预览"
        open={!!previewId}
        onCancel={() => setPreviewId(null)}
        footer={null}
        width="80%"
        style={{ top: 32 }}
        destroyOnHidden
      >
        {previewId && (
          <iframe
            src={reportPreviewUrl(previewId)}
            style={{ width: '100%', height: '70vh', border: 'none' }}
            title="report-preview"
            data-testid="report-preview-iframe"
          />
        )}
      </Modal>
    </div>
  );
}

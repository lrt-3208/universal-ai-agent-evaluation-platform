/**
 * Regression 创建页 — F6.1
 *
 * Reference: docs/phases/phase-f6-regression.md §2.1
 * 前端预校验：baseline 与 target 的 dataset_id 不一致时禁用提交（后端 409 兜底）
 */
import { useMemo, useState } from 'react';
import { Alert, App, Button, Card, Form, Input, Select, Slider, Typography } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useEvaluations } from '@/hooks/useEvaluations';
import { useCreateRegression } from '@/hooks/useRegressions';
import { NotFoundResult } from '@/components/common';
import { ApiError } from '@/api/client';

export default function RegressionCreatePage() {
  const { projId } = useParams<{ projId: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();

  // 只列 completed 评测（phase-f6 §2.1）
  const evalsQuery = useEvaluations(projId ?? null, 1, 'completed');
  const createMut = useCreateRegression(projId ?? '');

  const [form] = Form.useForm();
  const [baselineId, setBaselineId] = useState<string | null>(null);
  const [targetId, setTargetId] = useState<string | null>(null);

  const evals = useMemo(() => evalsQuery.data?.items ?? [], [evalsQuery.data]);

  if (!projId) return <NotFoundResult />;

  const options = evals.map((e) => ({
    value: e.id,
    label: `${e.name}${e.version_label ? `（${e.version_label}）` : ''}`,
  }));

  const baseline = evals.find((e) => e.id === baselineId);
  const target = evals.find((e) => e.id === targetId);
  // Dataset 一致性预校验（AC-F6-02）
  const datasetMismatch = !!baseline && !!target && baseline.dataset_id !== target.dataset_id;

  const handleSubmit = async () => {
    const values = await form.validateFields();
    try {
      const regression = await createMut.mutateAsync({
        name: values.name,
        baseline_evaluation_id: values.baseline_evaluation_id,
        target_evaluation_id: values.target_evaluation_id,
        regression_threshold: values.regression_threshold,
      });
      message.success('回归分析完成');
      navigate(`/regressions/${regression.id}`);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  return (
    <div style={{ maxWidth: 640 }}>
      <Typography.Title level={4}>创建回归对比</Typography.Title>
      <Card>
        <Form
          form={form}
          layout="vertical"
          initialValues={{ regression_threshold: 0.05 }}
          onValuesChange={(changed) => {
            if ('baseline_evaluation_id' in changed) setBaselineId(changed.baseline_evaluation_id);
            if ('target_evaluation_id' in changed) setTargetId(changed.target_evaluation_id);
          }}
        >
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="如：v1.0 vs v1.1" />
          </Form.Item>
          <Form.Item
            name="baseline_evaluation_id"
            label="基线评测（Baseline）"
            rules={[{ required: true, message: '请选择基线评测' }]}
          >
            <Select options={options} placeholder="选择已完成的评测" showSearch optionFilterProp="label" data-testid="baseline-select" />
          </Form.Item>
          <Form.Item
            name="target_evaluation_id"
            label="目标评测（Target）"
            rules={[{ required: true, message: '请选择目标评测' }]}
          >
            <Select options={options} placeholder="选择已完成的评测" showSearch optionFilterProp="label" data-testid="target-select" />
          </Form.Item>
          <Form.Item
            name="regression_threshold"
            label="回归阈值"
            tooltip="得分差异低于该值视为无变化（默认 0.05）"
          >
            <Slider min={0} max={1} step={0.01} marks={{ 0.05: '0.05', 0.5: '0.5' }} />
          </Form.Item>

          {datasetMismatch && (
            <Alert
              type="error"
              showIcon
              style={{ marginBottom: 16 }}
              message="两个评测使用了不同的数据集，无法对比"
              data-testid="dataset-mismatch-alert"
            />
          )}

          <Button
            type="primary"
            onClick={handleSubmit}
            loading={createMut.isPending}
            disabled={datasetMismatch}
            data-testid="create-regression-btn"
          >
            创建并分析
          </Button>
        </Form>
      </Card>
    </div>
  );
}

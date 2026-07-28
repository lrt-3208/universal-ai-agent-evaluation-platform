/**
 * 评测创建向导 — F3.3
 *
 * Reference: docs/phases/phase-f3-evaluation.md §2.1
 * Step 3 Judge 配置在 F4 完整实现，本阶段放默认 Rule Judge（扁平结构）
 */
import { useState } from 'react';
import {
  App,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Select,
  Space,
  Steps,
  Typography,
} from 'antd';
import { useNavigate, useParams } from 'react-router-dom';
import { useProject } from '@/hooks/useWorkspaceProject';
import { useDatasets } from '@/hooks/useDatasetScenario';
import { useCreateEvaluation } from '@/hooks/useEvaluations';
import { validateJudgeConfigs } from '@/api/endpoints/judges';
import { JudgeConfigForm } from '@/components/judge';
import { useAvailableJudgeTypes } from '@/hooks/usePlugins';
import type { JudgeConfig } from '@/api/endpoints/evaluations';
import { NotFoundResult } from '@/components/common';
import { ApiError } from '@/api/client';

interface WizardState {
  name?: string;
  version_label?: string;
  dataset_id?: string;
  adapter_type?: string;
  endpoint?: string;
}

export default function EvaluationCreatePage() {
  const { projId } = useParams<{ projId: string }>();
  const { message } = App.useApp();
  const navigate = useNavigate();

  const projectQuery = useProject(projId ?? null);
  const datasetsQuery = useDatasets(projId ?? null, 1, 100);
  const createMut = useCreateEvaluation(projId ?? '');

  const [step, setStep] = useState(0);
  const [state, setState] = useState<WizardState>({});
  // Judge 配置（F4：默认一个 Rule Judge）
  const [judgeConfigs, setJudgeConfigs] = useState<JudgeConfig[]>([
    { judge_type: 'rule', metrics: ['correctness'] },
  ]);
  const [judgeErrors, setJudgeErrors] = useState<string[]>([]);
  const [judgeWarnings, setJudgeWarnings] = useState<string[]>([]);
  const [validating, setValidating] = useState(false);
  const [form] = Form.useForm();
  // judge_type 选项：内置 ∪ enabled judge 插件（F7 联动）
  const judgeTypeOptions = useAvailableJudgeTypes();

  if (!projId) return <NotFoundResult />;

  const datasets = datasetsQuery.data?.items ?? [];
  const project = projectQuery.data;

  const next = async () => {
    // 分步校验当前步字段（两步共用一个 Form 实例）
    const fields = step === 0 ? ['name', 'version_label', 'dataset_id'] : ['adapter_type', 'endpoint'];
    const values = await form.validateFields(fields);
    setState((s) => ({ ...s, ...values }));
    // 进入 Step1 时用项目配置回填 endpoint（若用户未填）
    if (step === 0 && !form.getFieldValue('endpoint')) {
      form.setFieldValue('endpoint', project?.agent_config?.endpoint || '');
    }
    setStep((s) => s + 1);
  };

  const prev = () => setStep((s) => s - 1);

  /** Step3 → Step4：先调 validate 校验 Judge 配置（AC-F4-02） */
  const validateAndNext = async () => {
    if (judgeConfigs.length === 0) {
      setJudgeErrors([]);
      setJudgeWarnings([]);
      setStep(3);
      return;
    }
    setValidating(true);
    try {
      const result = await validateJudgeConfigs(projId, judgeConfigs);
      setJudgeErrors(result.errors);
      setJudgeWarnings(result.warnings);
      if (result.valid) setStep(3);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    } finally {
      setValidating(false);
    }
  };

  const handleSubmit = async () => {
    try {
      const evaluation = await createMut.mutateAsync({
        name: state.name!,
        dataset_id: state.dataset_id!,
        version_label: state.version_label || undefined,
        agent_config: {
          adapter_type: state.adapter_type!,
          endpoint: state.endpoint!,
        },
        judge_configs: judgeConfigs,
      });
      message.success('评测已创建，开始执行');
      navigate(`/evaluations/${evaluation.id}`);
    } catch (e) {
      if (e instanceof ApiError) message.error(e.message);
      else throw e;
    }
  };

  const selectedDataset = datasets.find((d) => d.id === state.dataset_id);

  return (
    <div style={{ maxWidth: 720 }}>
      <Typography.Title level={4}>发起评测</Typography.Title>
      <Steps
        current={step}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          { title: '基本信息' },
          { title: 'Agent 配置' },
          { title: 'Judge 配置' },
          { title: '确认提交' },
        ]}
      />

      <Card>
        {/* Step0/1 共用一个 Form 实例：始终挂载，用 hidden 切换步骤，
            避免 form 实例在无 Form 元素时触发 antd "not connected" 警告 */}
        <Form
          form={form}
          layout="vertical"
          style={{ display: step === 0 || step === 1 ? 'block' : 'none' }}
          initialValues={{ adapter_type: project?.agent_config?.adapter_type || 'http' }}
        >
          <div style={{ display: step === 0 ? 'block' : 'none' }}>
            <Form.Item name="name" label="评测名称" rules={[{ required: true, message: '请输入名称' }]}>
              <Input placeholder="如：v1.2 回归评测" />
            </Form.Item>
            <Form.Item name="version_label" label="版本标签" tooltip="用于回归对比时区分 Agent 版本">
              <Input placeholder="如：v1.2" />
            </Form.Item>
            <Form.Item
              name="dataset_id"
              label="数据集"
              rules={[{ required: true, message: '请选择数据集' }]}
            >
              <Select
                placeholder="选择数据集"
                loading={datasetsQuery.isPending}
                options={datasets.map((d) => ({
                  value: d.id,
                  label: `${d.name} v${d.version}（${d.scenario_count} 个场景）`,
                }))}
                data-testid="dataset-select"
              />
            </Form.Item>
          </div>

          <div style={{ display: step === 1 ? 'block' : 'none' }}>
            <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
              默认继承项目 Agent 配置，可在此覆盖
            </Typography.Paragraph>
            <Form.Item name="adapter_type" label="Adapter 类型" rules={[{ required: true }]}>
              <Select
                options={[
                  { value: 'http', label: 'HTTP' },
                  { value: 'openai', label: 'OpenAI 兼容' },
                  { value: 'custom', label: 'Custom' },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="endpoint"
              label="Agent Endpoint"
              rules={[{ required: true, message: '请输入 endpoint' }]}
              tooltip="base URL，不带 /chat"
            >
              <Input placeholder="http://localhost:9001" />
            </Form.Item>
          </div>
        </Form>

        {step === 2 && (
          <div data-testid="judge-config-step">
            <JudgeConfigForm
              value={judgeConfigs}
              typeOptions={judgeTypeOptions}
              onChange={(c) => {
                setJudgeConfigs(c);
                setJudgeErrors([]);
                setJudgeWarnings([]);
              }}
              errors={judgeErrors}
              warnings={judgeWarnings}
            />
          </div>
        )}

        {step === 3 && (
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="名称">{state.name}</Descriptions.Item>
            <Descriptions.Item label="版本标签">{state.version_label || '-'}</Descriptions.Item>
            <Descriptions.Item label="数据集">
              {selectedDataset ? `${selectedDataset.name} v${selectedDataset.version}（${selectedDataset.scenario_count} 场景）` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Adapter">{state.adapter_type}</Descriptions.Item>
            <Descriptions.Item label="Endpoint">{state.endpoint}</Descriptions.Item>
            <Descriptions.Item label="Judge">
              {judgeConfigs.length > 0
                ? judgeConfigs.map((c) => `${c.judge_type}(${(c.metrics ?? []).join('/')})`).join('，')
                : '无（不评分）'}
            </Descriptions.Item>
          </Descriptions>
        )}

        <Space style={{ marginTop: 24 }}>
          {step > 0 && <Button onClick={prev}>上一步</Button>}
          {step < 3 && (
            <Button
              type="primary"
              onClick={step === 2 ? validateAndNext : next}
              loading={validating}
              data-testid="wizard-next-btn"
            >
              下一步
            </Button>
          )}
          {step === 3 && (
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={createMut.isPending}
              data-testid="wizard-submit-btn"
            >
              提交并开始评测
            </Button>
          )}
        </Space>
      </Card>
    </div>
  );
}

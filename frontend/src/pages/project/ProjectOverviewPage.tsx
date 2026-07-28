/**
 * Project 概览页 — F1.5
 *
 * Reference: docs/contracts/route-map.md（/projects/:projId）
 */
import { Card, Col, Descriptions, Row, Statistic, Tag, Typography } from 'antd';
import { Link, useParams } from 'react-router-dom';
import { useProject } from '@/hooks/useWorkspaceProject';
import { NotFoundResult, QueryBoundary } from '@/components/common';
import { bizTokens } from '@/theme/tokens';

export default function ProjectOverviewPage() {
  const { projId } = useParams<{ projId: string }>();
  const query = useProject(projId ?? null);

  if (!projId) return <NotFoundResult />;

  return (
    <QueryBoundary query={query}>
      {(project) => (
        <div>
          <Typography.Title level={4}>{project.name}</Typography.Title>
          <Row gutter={16}>
            <Col span={16}>
              <Card title="项目信息">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Slug">{project.slug}</Descriptions.Item>
                  <Descriptions.Item label="描述">
                    {project.description || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Adapter">
                    <Tag>{project.agent_config?.adapter_type}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Endpoint">
                    <Typography.Text code style={{ fontFamily: bizTokens.fontFamilyCode }}>
                      {project.agent_config?.endpoint}
                    </Typography.Text>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col span={8}>
              <Card title="快捷入口">
                <Row gutter={[8, 8]}>
                  <Col span={12}>
                    <Link to={`/projects/${project.id}/datasets`}>
                      <Statistic title="数据集" value="管理" valueStyle={{ fontSize: 16 }} />
                    </Link>
                  </Col>
                  <Col span={12}>
                    <Link to={`/projects/${project.id}/evaluations`}>
                      <Statistic title="评测" value="查看" valueStyle={{ fontSize: 16 }} />
                    </Link>
                  </Col>
                  <Col span={12}>
                    <Link to={`/projects/${project.id}/regressions`}>
                      <Statistic title="回归对比" value="查看" valueStyle={{ fontSize: 16 }} />
                    </Link>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        </div>
      )}
    </QueryBoundary>
  );
}

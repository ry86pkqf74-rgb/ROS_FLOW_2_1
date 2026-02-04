/**
 * ComplianceDashboard - View and manage compliance status
 */

import React, { useState, useEffect } from 'react';
import { useParams } from 'wouter';
import {
  Shield,
  CheckCircle,
  FileText,
  Download,
  RefreshCw,
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
  ComplianceScore,
  TRIPODChecklist,
  CONSORTChecklist,
  TransparencyReport,
  AuditTimeline,
} from '@/components/compliance';
import { complianceApi } from '@/api/compliance';
import type { ComplianceData } from '@/api/compliance';

export const ComplianceDashboard: React.FC = () => {
  const params = useParams<{ projectId: string }>();
  const projectId = params.projectId;
  const [data, setData] = useState<ComplianceData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadComplianceData();
  }, [projectId]);

  const loadComplianceData = async () => {
    if (!projectId) return;
    setIsLoading(true);
    try {
      const response = await complianceApi.getComplianceStatus(projectId);
      setData(response);
    } catch (error) {
      console.error('Failed to load compliance data', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportReport = async () => {
    if (!projectId) return;
    try {
      const blob = await complianceApi.exportComplianceReport(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `compliance-report-${projectId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export report', error);
    }
  };

  if (!projectId) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        No project selected
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        Failed to load compliance data
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" />
            Compliance Dashboard
          </h1>
          <p className="text-muted-foreground">
            Monitor regulatory compliance and reporting standards
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadComplianceData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handleExportReport}>
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <ComplianceScore
          title="Overall"
          score={data.overallScore}
          icon={Shield}
          color="primary"
        />
        <ComplianceScore
          title="TRIPOD+AI"
          score={data.tripodScore}
          icon={FileText}
          color="blue"
        />
        <ComplianceScore
          title="CONSORT-AI"
          score={data.consortScore}
          icon={CheckCircle}
          color="green"
        />
        <ComplianceScore
          title="HTI-1"
          score={data.hti1Score}
          icon={Shield}
          color="purple"
        />
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tripod">TRIPOD+AI</TabsTrigger>
          <TabsTrigger value="consort">CONSORT-AI</TabsTrigger>
          <TabsTrigger value="audit">Audit Trail</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <TransparencyReport projectId={projectId} />
        </TabsContent>

        <TabsContent value="tripod" className="space-y-4">
          <TRIPODChecklist items={data.tripodItems} projectId={projectId} />
        </TabsContent>

        <TabsContent value="consort" className="space-y-4">
          <CONSORTChecklist items={data.consortItems} projectId={projectId} />
        </TabsContent>

        <TabsContent value="audit" className="space-y-4">
          <AuditTimeline events={data.auditEvents} />
        </TabsContent>
      </Tabs>

      {/* Last Updated */}
      <div className="text-sm text-muted-foreground text-right">
        Last updated: {new Date(data.lastUpdated).toLocaleString()}
      </div>
    </div>
  );
};

export default ComplianceDashboard;

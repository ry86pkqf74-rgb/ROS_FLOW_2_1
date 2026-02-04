/*
Analytics Dashboard Component
============================

Main dashboard component that combines real-time monitoring and predictive analytics.
Provides a comprehensive view of system performance and operational insights.
*/

import React, { useState } from 'react';
import { Card, CardHeader, CardContent, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RealTimeMonitor } from './RealTimeMonitor';
import { SizePredictorWidget } from './SizePredictorWidget';
import { BarChart3, Activity, Calculator, TrendingUp, Settings, RefreshCw } from 'lucide-react';

// ============================================================================
// Types & Interfaces
// ============================================================================

interface AnalyticsDashboardProps {
  className?: string;
  defaultTab?: 'overview' | 'monitoring' | 'prediction' | 'trends';
}

// ============================================================================
// Analytics Dashboard Component  
// ============================================================================

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  className = '',
  defaultTab = 'overview'
}) => {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Handle manual refresh
  const handleRefresh = () => {
    setLastRefresh(new Date());
    // Trigger refresh in child components if needed
    window.location.reload();
  };

  return (
    <div className={`analytics-dashboard ${className}`}>
      {/* Dashboard Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-gray-600">
            Real-time monitoring, predictive analytics, and performance insights
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <Badge variant="outline">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="flex items-center"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Main Dashboard Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview" className="flex items-center">
            <BarChart3 className="h-4 w-4 mr-2" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="monitoring" className="flex items-center">
            <Activity className="h-4 w-4 mr-2" />
            Real-Time
          </TabsTrigger>
          <TabsTrigger value="prediction" className="flex items-center">
            <Calculator className="h-4 w-4 mr-2" />
            Prediction
          </TabsTrigger>
          <TabsTrigger value="trends" className="flex items-center">
            <TrendingUp className="h-4 w-4 mr-2" />
            Trends
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-6">
          <div className="space-y-6">
            {/* Quick Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <Activity className="h-8 w-8 text-blue-500" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">System Health</p>
                      <div className="flex items-center mt-1">
                        <div className="text-2xl font-bold">98%</div>
                        <Badge variant="default" className="ml-2">Excellent</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <Calculator className="h-8 w-8 text-green-500" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Predictions Today</p>
                      <div className="flex items-center mt-1">
                        <div className="text-2xl font-bold">247</div>
                        <Badge variant="default" className="ml-2">+12%</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <TrendingUp className="h-8 w-8 text-purple-500" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Avg Accuracy</p>
                      <div className="flex items-center mt-1">
                        <div className="text-2xl font-bold">94.2%</div>
                        <Badge variant="default" className="ml-2">+2.1%</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center">
                    <Settings className="h-8 w-8 text-orange-500" />
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-600">Active Operations</p>
                      <div className="flex items-center mt-1">
                        <div className="text-2xl font-bold">12</div>
                        <Badge variant="secondary" className="ml-2">Normal</Badge>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity & Alerts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Recent Predictions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium">Clinical Trial Manuscript</p>
                        <p className="text-sm text-gray-600">Predicted: 2.4 MB</p>
                      </div>
                      <Badge variant="default">96% confidence</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium">Systematic Review</p>
                        <p className="text-sm text-gray-600">Predicted: 8.1 MB</p>
                      </div>
                      <Badge variant="default">89% confidence</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium">Case Study Report</p>
                        <p className="text-sm text-gray-600">Predicted: 1.2 MB</p>
                      </div>
                      <Badge variant="default">92% confidence</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>System Alerts</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div>
                        <p className="font-medium text-green-800">System Performance</p>
                        <p className="text-sm text-green-600">All metrics within normal range</p>
                      </div>
                      <Badge variant="default">Normal</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                      <div>
                        <p className="font-medium text-blue-800">Model Update</p>
                        <p className="text-sm text-blue-600">Prediction model retrained successfully</p>
                      </div>
                      <Badge variant="secondary">Info</Badge>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                      <div>
                        <p className="font-medium text-yellow-800">Queue Length</p>
                        <p className="text-sm text-yellow-600">Processing queue slightly elevated</p>
                      </div>
                      <Badge variant="outline">Warning</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Button 
                    variant="outline" 
                    className="h-16 flex flex-col items-center justify-center"
                    onClick={() => setActiveTab('prediction')}
                  >
                    <Calculator className="h-6 w-6 mb-2" />
                    New Size Prediction
                  </Button>
                  <Button 
                    variant="outline" 
                    className="h-16 flex flex-col items-center justify-center"
                    onClick={() => setActiveTab('monitoring')}
                  >
                    <Activity className="h-6 w-6 mb-2" />
                    View Live Metrics
                  </Button>
                  <Button 
                    variant="outline" 
                    className="h-16 flex flex-col items-center justify-center"
                    onClick={() => setActiveTab('trends')}
                  >
                    <TrendingUp className="h-6 w-6 mb-2" />
                    Analyze Trends
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Real-Time Monitoring Tab */}
        <TabsContent value="monitoring" className="mt-6">
          <RealTimeMonitor />
        </TabsContent>

        {/* Size Prediction Tab */}
        <TabsContent value="prediction" className="mt-6">
          <SizePredictorWidget 
            onPredictionComplete={(prediction) => {
              console.log('Prediction completed:', prediction);
              // Could add notification or redirect to results view
            }}
          />
        </TabsContent>

        {/* Trends Analysis Tab */}
        <TabsContent value="trends" className="mt-6">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Performance Trends</CardTitle>
                <p className="text-sm text-gray-600">
                  Historical analysis of system performance and prediction accuracy
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <h4 className="font-medium mb-3">Prediction Accuracy Trend</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Last 7 days</span>
                        <span className="font-medium">94.2% avg</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Last 30 days</span>
                        <span className="font-medium">93.8% avg</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Last 90 days</span>
                        <span className="font-medium">92.1% avg</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="font-medium mb-3">Processing Volume</h4>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Today</span>
                        <span className="font-medium">247 predictions</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">This week</span>
                        <span className="font-medium">1,834 predictions</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">This month</span>
                        <span className="font-medium">7,921 predictions</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Model Performance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-2">
                        <span className="text-sm">Prediction Accuracy</span>
                        <span className="text-sm font-medium">94.2%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{width: '94.2%'}}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-2">
                        <span className="text-sm">Confidence Score</span>
                        <span className="text-sm font-medium">87.3%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{width: '87.3%'}}></div>
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between mb-2">
                        <span className="text-sm">Processing Speed</span>
                        <span className="text-sm font-medium">1.2s avg</span>
                      </div>
                      <Badge variant="default">Excellent</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Usage Patterns</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Peak Usage Time</span>
                      <span className="text-sm">2:00 PM - 4:00 PM</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Most Common Type</span>
                      <span className="text-sm">Clinical Trials (42%)</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Avg File Size</span>
                      <span className="text-sm">3.2 MB</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Success Rate</span>
                      <span className="text-sm">98.7%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AnalyticsDashboard;
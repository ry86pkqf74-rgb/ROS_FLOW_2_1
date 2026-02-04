import React, { useState, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  Brain, 
  CheckCircle, 
  Info, 
  ArrowRight, 
  ArrowLeft,
  TrendingUp,
  Users,
  Target,
  Lightbulb,
  AlertTriangle
} from 'lucide-react';
import { StudyData, TestType } from '@/types/statistical-analysis';

interface TestRecommendation {
  testType: TestType;
  confidence: number;
  reasoning: string[];
  assumptions: string[];
  alternatives: TestType[];
  pros: string[];
  cons: string[];
  powerEstimate?: 'low' | 'medium' | 'high';
}

interface TestSelectionPanelProps {
  data: StudyData;
  onTestSelect: (test: TestType) => void;
  selectedTest?: TestType | null;
  onNext: () => void;
  onBack: () => void;
}

const TEST_DESCRIPTIONS = {
  [TestType.T_TEST_INDEPENDENT]: {
    name: 'Independent t-test',
    description: 'Compare means between two independent groups',
    icon: '👥',
    useCase: 'Two groups, continuous outcome, normal distribution'
  },
  [TestType.T_TEST_PAIRED]: {
    name: 'Paired t-test',
    description: 'Compare means within the same subjects (before/after)',
    icon: '🔄',
    useCase: 'Same subjects measured twice, continuous outcome'
  },
  [TestType.MANN_WHITNEY]: {
    name: 'Mann-Whitney U test',
    description: 'Non-parametric comparison of two groups',
    icon: '📊',
    useCase: 'Two groups, non-normal distribution or ordinal data'
  },
  [TestType.ANOVA_ONEWAY]: {
    name: 'One-way ANOVA',
    description: 'Compare means across multiple independent groups',
    icon: '📈',
    useCase: 'Three or more groups, continuous outcome, normal distribution'
  },
  [TestType.KRUSKAL_WALLIS]: {
    name: 'Kruskal-Wallis test',
    description: 'Non-parametric comparison of multiple groups',
    icon: '📉',
    useCase: 'Three or more groups, non-normal distribution'
  },
  [TestType.CHI_SQUARE]: {
    name: 'Chi-square test',
    description: 'Test association between categorical variables',
    icon: '🎯',
    useCase: 'Categorical outcomes, frequency data'
  },
  [TestType.FISHER_EXACT]: {
    name: 'Fisher\'s exact test',
    description: 'Exact test for small sample categorical data',
    icon: '🔍',
    useCase: 'Small samples, 2x2 contingency tables'
  },
  [TestType.CORRELATION_PEARSON]: {
    name: 'Pearson correlation',
    description: 'Linear relationship between continuous variables',
    icon: '↗️',
    useCase: 'Two continuous variables, linear relationship'
  },
  [TestType.CORRELATION_SPEARMAN]: {
    name: 'Spearman correlation',
    description: 'Monotonic relationship between variables',
    icon: '📋',
    useCase: 'Ordinal data or non-linear relationships'
  }
};

export function TestSelectionPanel({ 
  data, 
  onTestSelect, 
  selectedTest, 
  onNext, 
  onBack 
}: TestSelectionPanelProps) {
  const [showAllTests, setShowAllTests] = useState(false);

  const analyzeData = useMemo(() => {
    const analysis = {
      numObservations: 0,
      numGroups: 1,
      numOutcomes: 0,
      groupSizes: [] as number[],
      outcomeTypes: [] as ('continuous' | 'categorical')[],
      pairedDesign: false
    };

    if (data.outcomes) {
      const outcomeKeys = Object.keys(data.outcomes);
      analysis.numOutcomes = outcomeKeys.length;
      
      if (outcomeKeys.length > 0) {
        analysis.numObservations = data.outcomes[outcomeKeys[0]].length;
      }
    }

    if (data.groups) {
      const uniqueGroups = [...new Set(data.groups)];
      analysis.numGroups = uniqueGroups.length;
      analysis.groupSizes = uniqueGroups.map(group => 
        data.groups!.filter(g => g === group).length
      );
      
      // Detect paired design patterns
      if (uniqueGroups.length === 2) {
        const groupNames = uniqueGroups.map(g => g.toLowerCase());
        analysis.pairedDesign = 
          (groupNames.includes('pre') && groupNames.includes('post')) ||
          (groupNames.includes('before') && groupNames.includes('after')) ||
          analysis.groupSizes.every(size => size === analysis.groupSizes[0]);
      }
    }

    // Analyze outcome types (simplified - assume continuous for now)
    analysis.outcomeTypes = Array(analysis.numOutcomes).fill('continuous');

    return analysis;
  }, [data]);

  const generateRecommendations = useMemo((): TestRecommendation[] => {
    const recommendations: TestRecommendation[] = [];
    const { numGroups, numObservations, groupSizes, pairedDesign } = analyzeData;
    const minGroupSize = Math.min(...groupSizes);

    // Two-group comparisons
    if (numGroups === 2) {
      if (pairedDesign) {
        recommendations.push({
          testType: TestType.T_TEST_PAIRED,
          confidence: 90,
          reasoning: [
            'Detected paired/repeated measures design',
            'Same subjects measured under different conditions',
            'Controls for individual differences'
          ],
          assumptions: ['Normality of differences', 'Independence of pairs'],
          alternatives: [TestType.MANN_WHITNEY],
          pros: [
            'More powerful than independent t-test',
            'Controls for individual variation',
            'Smaller sample size requirements'
          ],
          cons: [
            'Requires normal distribution of differences',
            'Cannot handle missing pairs easily'
          ],
          powerEstimate: minGroupSize >= 15 ? 'high' : minGroupSize >= 8 ? 'medium' : 'low'
        });
      } else {
        // Independent t-test
        recommendations.push({
          testType: TestType.T_TEST_INDEPENDENT,
          confidence: 85,
          reasoning: [
            'Two independent groups detected',
            'Continuous outcome variable',
            'Assumes normal distribution'
          ],
          assumptions: ['Normality', 'Homogeneity of variance', 'Independence'],
          alternatives: [TestType.MANN_WHITNEY],
          pros: [
            'Well-established and widely accepted',
            'Provides confidence intervals',
            'Robust to moderate deviations from normality'
          ],
          cons: [
            'Sensitive to outliers',
            'Assumes equal variances (can use Welch correction)'
          ],
          powerEstimate: minGroupSize >= 30 ? 'high' : minGroupSize >= 15 ? 'medium' : 'low'
        });

        // Mann-Whitney as alternative
        recommendations.push({
          testType: TestType.MANN_WHITNEY,
          confidence: 75,
          reasoning: [
            'Non-parametric alternative for two groups',
            'Robust to outliers and non-normal distributions',
            'Based on ranks rather than actual values'
          ],
          assumptions: ['Independence', 'Similar distribution shapes'],
          alternatives: [TestType.T_TEST_INDEPENDENT],
          pros: [
            'No normality assumption',
            'Robust to outliers',
            'Works with ordinal data'
          ],
          cons: [
            'Less powerful than t-test when normality holds',
            'Harder to interpret effect size'
          ],
          powerEstimate: minGroupSize >= 20 ? 'medium' : 'low'
        });
      }
    }

    // Multiple group comparisons
    if (numGroups >= 3) {
      recommendations.push({
        testType: TestType.ANOVA_ONEWAY,
        confidence: 85,
        reasoning: [
          `${numGroups} groups detected`,
          'One-way ANOVA for multiple group comparison',
          'Post-hoc tests will identify specific differences'
        ],
        assumptions: ['Normality within groups', 'Homogeneity of variance', 'Independence'],
        alternatives: [TestType.KRUSKAL_WALLIS],
        pros: [
          'Controls family-wise error rate',
          'Provides overall F-test',
          'Post-hoc tests available (Tukey HSD)'
        ],
        cons: [
          'Requires normal distribution in all groups',
          'Sensitive to unequal variances'
        ],
        powerEstimate: minGroupSize >= 10 ? 'high' : minGroupSize >= 5 ? 'medium' : 'low'
      });

      recommendations.push({
        testType: TestType.KRUSKAL_WALLIS,
        confidence: 75,
        reasoning: [
          'Non-parametric alternative for multiple groups',
          'Robust to non-normal distributions',
          'Rank-based comparison'
        ],
        assumptions: ['Independence', 'Similar distribution shapes'],
        alternatives: [TestType.ANOVA_ONEWAY],
        pros: [
          'No normality assumption',
          'Works with ordinal data',
          'Post-hoc tests available (Dunn test)'
        ],
        cons: [
          'Less powerful when normality holds',
          'Effect size interpretation more complex'
        ],
        powerEstimate: minGroupSize >= 8 ? 'medium' : 'low'
      });
    }

    // Sort by confidence
    return recommendations.sort((a, b) => b.confidence - a.confidence);
  }, [analyzeData]);

  const recommendedTest = generateRecommendations[0];

  const handleTestSelect = useCallback((testType: TestType) => {
    onTestSelect(testType);
  }, [onTestSelect]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 80) return 'bg-green-100 text-green-800';
    if (confidence >= 60) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  const getPowerColor = (power?: 'low' | 'medium' | 'high') => {
    switch (power) {
      case 'high': return 'text-green-600';
      case 'medium': return 'text-yellow-600';
      case 'low': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className=\"space-y-6\">
      {/* Data Summary */}
      <Card>
        <CardHeader>
          <CardTitle className=\"flex items-center gap-2\">
            <Info className=\"h-5 w-5\" />
            Data Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className=\"grid grid-cols-2 md:grid-cols-4 gap-4 text-center\">
            <div className=\"p-3 bg-blue-50 rounded-lg\">
              <div className=\"text-2xl font-bold text-blue-900\">{analyzeData.numObservations}</div>
              <div className=\"text-sm text-blue-700\">Observations</div>
            </div>
            <div className=\"p-3 bg-green-50 rounded-lg\">
              <div className=\"text-2xl font-bold text-green-900\">{analyzeData.numGroups}</div>
              <div className=\"text-sm text-green-700\">Groups</div>
            </div>
            <div className=\"p-3 bg-purple-50 rounded-lg\">
              <div className=\"text-2xl font-bold text-purple-900\">{analyzeData.numOutcomes}</div>
              <div className=\"text-sm text-purple-700\">Outcomes</div>
            </div>
            <div className=\"p-3 bg-orange-50 rounded-lg\">
              <div className=\"text-2xl font-bold text-orange-900\">
                {Math.min(...analyzeData.groupSizes)}
              </div>
              <div className=\"text-sm text-orange-700\">Min Group Size</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* AI Recommendation */}
      {recommendedTest && (
        <Card className=\"border-2 border-blue-200 bg-blue-50\">
          <CardHeader>
            <CardTitle className=\"flex items-center gap-2\">
              <Brain className=\"h-5 w-5 text-blue-600\" />
              AI Recommendation
            </CardTitle>
          </CardHeader>
          <CardContent className=\"space-y-4\">
            <div className=\"flex items-center justify-between\">
              <div className=\"flex items-center gap-3\">
                <div className=\"text-2xl\">{TEST_DESCRIPTIONS[recommendedTest.testType].icon}</div>
                <div>
                  <h3 className=\"text-lg font-semibold\">{TEST_DESCRIPTIONS[recommendedTest.testType].name}</h3>
                  <p className=\"text-gray-600\">{TEST_DESCRIPTIONS[recommendedTest.testType].description}</p>
                </div>
              </div>
              <div className=\"text-right space-y-2\">
                <Badge className={getConfidenceColor(recommendedTest.confidence)}>
                  {recommendedTest.confidence}% Confidence
                </Badge>
                {recommendedTest.powerEstimate && (
                  <Badge variant=\"outline\" className={getPowerColor(recommendedTest.powerEstimate)}>
                    {recommendedTest.powerEstimate.toUpperCase()} Power
                  </Badge>
                )}
              </div>
            </div>

            <div className=\"grid md:grid-cols-2 gap-4\">
              <div>
                <h4 className=\"font-medium text-green-700 mb-2\">✅ Pros</h4>
                <ul className=\"space-y-1 text-sm\">
                  {recommendedTest.pros.map((pro, index) => (
                    <li key={index} className=\"flex items-start gap-2\">
                      <div className=\"h-1.5 w-1.5 bg-green-500 rounded-full mt-2 flex-shrink-0\" />
                      {pro}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className=\"font-medium text-orange-700 mb-2\">⚠️ Considerations</h4>
                <ul className=\"space-y-1 text-sm\">
                  {recommendedTest.cons.map((con, index) => (
                    <li key={index} className=\"flex items-start gap-2\">
                      <div className=\"h-1.5 w-1.5 bg-orange-500 rounded-full mt-2 flex-shrink-0\" />
                      {con}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <Alert>
              <Lightbulb className=\"h-4 w-4\" />
              <AlertDescription>
                <strong>Why this test?</strong>
                <ul className=\"mt-1 space-y-1\">
                  {recommendedTest.reasoning.map((reason, index) => (
                    <li key={index} className=\"text-sm\">• {reason}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>

            <Button
              onClick={() => handleTestSelect(recommendedTest.testType)}
              className=\"w-full\"
              variant={selectedTest === recommendedTest.testType ? \"default\" : \"outline\"}
            >
              {selectedTest === recommendedTest.testType ? (
                <>
                  <CheckCircle className=\"h-4 w-4 mr-2\" />
                  Selected
                </>
              ) : (
                'Use Recommended Test'
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Alternative Tests */}
      <Card>
        <CardHeader>
          <CardTitle className=\"flex items-center justify-between\">
            <span>All Available Tests</span>
            <Button
              variant=\"ghost\"
              size=\"sm\"
              onClick={() => setShowAllTests(!showAllTests)}
            >
              {showAllTests ? 'Show Less' : 'Show All'}
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className=\"grid gap-3\">
            {(showAllTests ? generateRecommendations : generateRecommendations.slice(0, 3)).map((rec) => (
              <Card
                key={rec.testType}
                className={`cursor-pointer transition-colors ${
                  selectedTest === rec.testType 
                    ? 'border-blue-500 bg-blue-50' 
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => handleTestSelect(rec.testType)}
              >
                <CardContent className=\"p-4\">
                  <div className=\"flex items-center justify-between\">
                    <div className=\"flex items-center gap-3\">
                      <div className=\"text-xl\">{TEST_DESCRIPTIONS[rec.testType].icon}</div>
                      <div>
                        <h4 className=\"font-medium\">{TEST_DESCRIPTIONS[rec.testType].name}</h4>
                        <p className=\"text-sm text-gray-600\">{TEST_DESCRIPTIONS[rec.testType].useCase}</p>
                      </div>
                    </div>
                    <div className=\"flex items-center gap-2\">
                      {rec.powerEstimate && (
                        <Badge variant=\"outline\" className={getPowerColor(rec.powerEstimate)}>
                          {rec.powerEstimate}
                        </Badge>
                      )}
                      <Badge className={getConfidenceColor(rec.confidence)}>
                        {rec.confidence}%
                      </Badge>
                      {selectedTest === rec.testType && (
                        <CheckCircle className=\"h-5 w-5 text-blue-600\" />
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className=\"flex justify-between\">
        <Button variant=\"outline\" onClick={onBack}>
          <ArrowLeft className=\"h-4 w-4 mr-2\" />
          Back to Data
        </Button>
        <Button onClick={onNext} disabled={!selectedTest}>
          Continue to Configuration
          <ArrowRight className=\"h-4 w-4 ml-2\" />
        </Button>
      </div>
    </div>
  );
}
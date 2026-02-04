/**
 * Stage 18 - Final Review (manuscript writing pipeline)
 * Final compliance check, PHI certification, author sign-off
 */

import * as React from 'react';
import { useState } from 'react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Shield, Check } from 'lucide-react';

interface StageProps {
  workflowId: string;
  manuscriptId?: string;
  onComplete: () => void;
}

const COMPLIANCE_ITEMS = [
  { id: 'ethics', label: 'Ethics approval and consent documented' },
  { id: 'data', label: 'Data availability statement included' },
  { id: 'conflict', label: 'Conflict of interest statement included' },
  { id: 'contrib', label: 'Author contributions stated' },
  { id: 'reporting', label: 'Reporting guideline checklist completed' },
];

export function Stage18FinalReview({
  workflowId,
  manuscriptId,
  onComplete,
}: StageProps) {
  const [compliance, setCompliance] = useState<Record<string, boolean>>(
    COMPLIANCE_ITEMS.reduce((acc, i) => ({ ...acc, [i.id]: false }), {})
  );
  const [phiCertified, setPhiCertified] = useState(false);
  const [signOff, setSignOff] = useState(false);
  const [signOffName, setSignOffName] = useState('');
  const [signOffDate, setSignOffDate] = useState('');

  const allComplianceChecked = COMPLIANCE_ITEMS.every((i) => compliance[i.id]);
  const canComplete = allComplianceChecked && phiCertified && signOff;

  const toggleCompliance = (id: string) => {
    setCompliance((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Final compliance check</CardTitle>
          <CardDescription>Confirm all compliance items before submission.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {COMPLIANCE_ITEMS.map((item) => (
            <div key={item.id} className="flex items-center space-x-2">
              <Checkbox
                id={item.id}
                checked={compliance[item.id]}
                onCheckedChange={() => toggleCompliance(item.id)}
              />
              <Label htmlFor={item.id}>{item.label}</Label>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            PHI certification
            <Badge variant={phiCertified ? 'default' : 'secondary'}>
              {phiCertified ? 'Certified' : 'Not certified'}
            </Badge>
          </CardTitle>
          <CardDescription>Certify that the manuscript has been scanned for PHI and is clear for submission.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="phi-cert"
              checked={phiCertified}
              onCheckedChange={(v) => setPhiCertified(v === true)}
            />
            <Label htmlFor="phi-cert">I certify that PHI has been reviewed and redacted as required.</Label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Author sign-off</CardTitle>
          <CardDescription>Confirm final approval before submission.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="signoff"
              checked={signOff}
              onCheckedChange={(v) => setSignOff(v === true)}
            />
            <Label htmlFor="signoff">I approve this manuscript for submission.</Label>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="signoff-name">Name</Label>
              <Input
                id="signoff-name"
                value={signOffName}
                onChange={(e) => setSignOffName(e.target.value)}
                placeholder="Author name"
              />
            </div>
            <div>
              <Label htmlFor="signoff-date">Date</Label>
              <Input
                id="signoff-date"
                type="date"
                value={signOffDate}
                onChange={(e) => setSignOffDate(e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button onClick={onComplete} disabled={!canComplete}>
          <Check className="h-4 w-4 mr-1" />
          Complete Stage
        </Button>
      </div>
    </div>
  );
}

export default Stage18FinalReview;

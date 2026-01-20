import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader } from '@/components/ui/loader';
import {
  getAnalytics,
  getUnusedDocuments,
  type Analytics,
  type Document,
} from '@/lib/api';

export function AnalyticsPage() {
  const { user, loading: authLoading } = useAuth();
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [unusedDocuments, setUnusedDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAnalytics = useCallback(async () => {
    try {
      const [analyticsData, unused] = await Promise.all([
        getAnalytics(),
        getUnusedDocuments(),
      ]);
      setAnalytics(analyticsData);
      setUnusedDocuments(unused);
    } catch (err) {
      console.error('Failed to load analytics:', err);
      setError('Failed to load analytics. You may not have permission to view this page.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.is_superuser) {
      loadAnalytics();
    } else if (!authLoading) {
      setIsLoading(false);
    }
  }, [user, authLoading, loadAnalytics]);

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <Loader variant="dots" size="lg" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-muted-foreground">Sign in to view analytics</p>
      </div>
    );
  }

  if (!user.is_superuser) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-muted-foreground">You don't have permission to view this page</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  if (!analytics) return null;

  const feedbackPercentage = analytics.feedback_statistics.positive_feedback_percentage;

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <h1 className="text-2xl font-semibold mb-6">Analytics Dashboard</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total Interactions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{analytics.total_interactions}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Avg Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{analytics.average_response_time_seconds.toFixed(2)}s</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Total Feedback</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{analytics.feedback_statistics.total_feedback_count}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Positive Feedback</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{feedbackPercentage.toFixed(0)}%</p>
            <div className="mt-2 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full"
                style={{ width: `${feedbackPercentage}%` }}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most Queried Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Most Queried Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics.most_frequently_queried_documents.length === 0 ? (
              <p className="text-muted-foreground text-sm">No data yet</p>
            ) : (
              <div className="space-y-3">
                {analytics.most_frequently_queried_documents.slice(0, 5).map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm truncate flex-1 mr-4">{doc.filename}</span>
                    <span className="text-sm font-medium">{doc.query_count} queries</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Weekly Queries per Document */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Weekly Document Usage</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics.weekly_queries_per_document.length === 0 ? (
              <p className="text-muted-foreground text-sm">No data this week</p>
            ) : (
              <div className="space-y-3">
                {analytics.weekly_queries_per_document.slice(0, 5).map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <span className="text-sm truncate flex-1 mr-4">{doc.filename}</span>
                    <span className="text-sm font-medium">{doc.weekly_query_count} queries</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Unused Documents */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Unused Documents</CardTitle>
          </CardHeader>
          <CardContent>
            {unusedDocuments.length === 0 ? (
              <p className="text-muted-foreground text-sm">All documents have been used</p>
            ) : (
              <div className="space-y-2">
                {unusedDocuments.slice(0, 5).map((doc) => (
                  <div key={doc.id} className="flex items-center gap-2">
                    <span className="text-sm truncate">{doc.filename}</span>
                  </div>
                ))}
                {unusedDocuments.length > 5 && (
                  <p className="text-xs text-muted-foreground">
                    +{unusedDocuments.length - 5} more
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Feedback Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Feedback Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics.feedback_statistics.total_feedback_count === 0 ? (
              <p className="text-muted-foreground text-sm">No feedback yet</p>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Positive</span>
                  <span className="text-sm font-medium text-green-600">
                    {analytics.feedback_statistics.positive_feedback_count}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Negative</span>
                  <span className="text-sm font-medium text-red-600">
                    {analytics.feedback_statistics.negative_feedback_count}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import { notFound } from "next/navigation";
import { getCampaignBySlug } from "@/lib/campaign-insights-data";
import { CampaignAnalyticsView } from "@/components/campaign/campaign-analytics-view";

type CampaignAnalyticsPageProps = {
  params: {
    slug: string;
  };
};

export default function CampaignAnalyticsPage({
  params,
}: CampaignAnalyticsPageProps) {
  const campaign = getCampaignBySlug(params.slug);

  if (!campaign) {
    notFound();
  }

  return <CampaignAnalyticsView campaign={campaign} />;
}


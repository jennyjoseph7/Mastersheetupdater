import { notFound } from "next/navigation";
import {
  getCampaignBySlug,
  campaignConversions,
} from "@/lib/campaign-insights-data";
import { CampaignAnalyticsView } from "@/components/campaign/campaign-analytics-view";

export async function generateStaticParams() {
  return campaignConversions.map((campaign) => ({
    slug: campaign.slug,
  }));
}

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

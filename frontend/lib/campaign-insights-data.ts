export type CampaignConversion = {
  slug: string;
  name: string;
  createdOn: string;
  channels: string[];
  status: "Live" | "Completed";
  analytics: {
    funnel: Array<{
      stage: string;
      count: number;
      percent: number;
    }>;
    conversionRate: number;
    totalReached: number;
    converted: number;
    sentiment: Array<{
      label: "Positive" | "Neutral" | "Negative";
      percent: number;
      count: number;
    }>;
    totalAnalyzed: number;
    satisfaction: number;
  };
};

export const campaignConversions: CampaignConversion[] = [
  {
    slug: "summer-insurance-promo-2024",
    name: "Summer Insurance Promo 2024",
    createdOn: "15/01/2024",
    channels: ["WhatsApp", "Email", "SMS"],
    status: "Live",
    analytics: {
      funnel: [
        { stage: "Sent/Called", count: 30000, percent: 100 },
        { stage: "Delivered/Answered", count: 26100, percent: 87 },
        { stage: "Read/Greeted", count: 18600, percent: 62 },
        { stage: "Interacted", count: 10200, percent: 34 },
        { stage: "Dropped-off", count: 7200, percent: 24 },
        { stage: "Converted", count: 2700, percent: 9 },
      ],
      conversionRate: 9,
      totalReached: 30000,
      converted: 2700,
      sentiment: [
        { label: "Positive", percent: 58, count: 10788 },
        { label: "Neutral", percent: 32, count: 5952 },
        { label: "Negative", percent: 10, count: 1860 },
      ],
      totalAnalyzed: 18600,
      satisfaction: 58,
    },
  },
  {
    slug: "health-coverage-campaign",
    name: "Health Coverage Campaign",
    createdOn: "10/01/2024",
    channels: ["Email", "Voice"],
    status: "Completed",
    analytics: {
      funnel: [
        { stage: "Sent/Called", count: 18500, percent: 100 },
        { stage: "Delivered/Answered", count: 15725, percent: 85 },
        { stage: "Read/Greeted", count: 12030, percent: 65 },
        { stage: "Interacted", count: 7025, percent: 38 },
        { stage: "Dropped-off", count: 4900, percent: 26 },
        { stage: "Converted", count: 1980, percent: 11 },
      ],
      conversionRate: 11,
      totalReached: 18500,
      converted: 1980,
      sentiment: [
        { label: "Positive", percent: 61, count: 7338 },
        { label: "Neutral", percent: 28, count: 3368 },
        { label: "Negative", percent: 11, count: 1168 },
      ],
      totalAnalyzed: 11874,
      satisfaction: 61,
    },
  },
  {
    slug: "life-insurance-awareness",
    name: "Life Insurance Awareness",
    createdOn: "20/01/2024",
    channels: ["Email", "WhatsApp", "Voice"],
    status: "Live",
    analytics: {
      funnel: [
        { stage: "Sent/Called", count: 32400, percent: 100 },
        { stage: "Delivered/Answered", count: 28512, percent: 88 },
        { stage: "Read/Greeted", count: 21096, percent: 65 },
        { stage: "Interacted", count: 12312, percent: 38 },
        { stage: "Dropped-off", count: 8748, percent: 27 },
        { stage: "Converted", count: 3240, percent: 10 },
      ],
      conversionRate: 10,
      totalReached: 32400,
      converted: 3240,
      sentiment: [
        { label: "Positive", percent: 55, count: 11603 },
        { label: "Neutral", percent: 34, count: 7198 },
        { label: "Negative", percent: 11, count: 2341 },
      ],
      totalAnalyzed: 21142,
      satisfaction: 55,
    },
  },
];

export const getCampaignBySlug = (slug: string) =>
  campaignConversions.find((campaign) => campaign.slug === slug);


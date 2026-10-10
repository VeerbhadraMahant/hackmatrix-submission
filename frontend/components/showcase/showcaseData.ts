export type FeatureId = "track" | "budget" | "collaborate" | "plan";

export interface FeatureItem {
  id: FeatureId;
  eyebrow: string;
  title: string;
  description: string;
  ctaText: string;
  position: "left-top" | "left-bottom" | "right-top" | "right-bottom";
}

export const SHOWCASE_HEADER = {
  title: "Your whole financial life, one co-pilot",
  subtitle:
    "Connect your accounts and FinPilot will do the heavy lifting to categorize your finances. From there, you can track, budget, collaborate, and set goals specific to you.",
};

export const SHOWCASE_FEATURES: FeatureItem[] = [
  {
    id: "track",
    eyebrow: "TRACK",
    title: "Know where you stand",
    description:
      "From your net worth to day-to-day spending and cash flow, feel confident about where you're at.",
    ctaText: "Learn more",
    position: "left-top",
  },
  {
    id: "budget",
    eyebrow: "BUDGET",
    title: "Budgeting that fits your life",
    description:
      "Create a budget that flexes to your needs — and not the other way around — so you can stay focused on the things that matter most.",
    ctaText: "Learn more",
    position: "left-bottom",
  },
  {
    id: "collaborate",
    eyebrow: "COLLABORATE",
    title: "Make smart money moves together",
    description:
      "Invite your partner to see your full picture, budget together, and reach your goals faster (and with more high fives).",
    ctaText: "Learn more",
    position: "right-top",
  },
  {
    id: "plan",
    eyebrow: "PLAN",
    title: "Set goals (and crush them)",
    description:
      "From planning a vacation to a home remodel — track your goals and adjust your cash flow to make sure you stick the landing.",
    ctaText: "Learn more",
    position: "right-bottom",
  },
];

export interface TrackTransaction {
  merchant: string;
  account: string;
  amount: string;
  category: "Shopping" | "Electronics" | "Miscellaneous" | "Business";
  tag: "Subscription" | "Home" | "Tax" | "Other";
  date: string;
  notePlaceholder: string;
  swipeType: "skip" | "reviewed";
}

export const TRACK_TRANSACTIONS: TrackTransaction[] = [
  {
    merchant: "Apex Cloud Services",
    account: "FinPilot Debit Card",
    amount: "$19.99",
    category: "Electronics",
    tag: "Subscription",
    date: "July 6",
    notePlaceholder: "Add notes...",
    swipeType: "skip",
  },
  {
    merchant: "Urban Provisions Market",
    account: "Primary Checking",
    amount: "$54.29",
    category: "Shopping",
    tag: "Home",
    date: "July 5",
    notePlaceholder: "Weekly organic refill",
    swipeType: "reviewed",
  },
  {
    merchant: "Horizon Fiber Internet",
    account: "FinPilot Corporate Card",
    amount: "$1,200.00",
    category: "Business",
    tag: "Tax",
    date: "July 2",
    notePlaceholder: "Annual fiber gigabit infrastructure",
    swipeType: "reviewed",
  },
];

export interface BudgetItem {
  id: string;
  name: string;
  spent: string;
  total: string;
  percent: number;
  colorClass: string;
  iconType: "grocery" | "dining" | "shopping" | "fitness";
}

export const BUDGET_ITEMS: BudgetItem[] = [
  {
    id: "grocery",
    name: "Grocery Budget",
    spent: "$145.89",
    total: "$600.00",
    percent: 24.3,
    colorClass: "#10B981", // vibrant emerald green
    iconType: "grocery",
  },
  {
    id: "dining",
    name: "Restaurants",
    spent: "$30.60",
    total: "$300.00",
    percent: 10.2,
    colorClass: "#0D9488", // teal
    iconType: "dining",
  },
  {
    id: "shopping",
    name: "Shopping",
    spent: "$267.99",
    total: "$300.00",
    percent: 89.3,
    colorClass: "#D946EF", // magenta/fuchsia
    iconType: "shopping",
  },
  {
    id: "fitness",
    name: "Fitness",
    spent: "$44.50",
    total: "$50.00",
    percent: 89.0,
    colorClass: "#EAB308", // warm yellow
    iconType: "fitness",
  },
];

export interface CollabAccount {
  name: string;
  institution: string;
  balance: string;
  updated: string;
  iconBg: string;
  iconColor: string;
}

export interface CollaborateUser {
  name: string;
  initials: string;
  gradient?: string;
  avatarSrc?: string;
}

export interface CollaborateData {
  users: CollaborateUser[];
  netWorth: string;
  accounts: CollabAccount[];
}

export const COLLABORATE_DATA: CollaborateData = {
  users: [

    {
      name: "Jessie",
      initials: "J",
      gradient: "from-amber-400 via-orange-400 to-rose-400",
      avatarSrc: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
    },
    {
      name: "Dylan",
      initials: "D",
      gradient: "from-blue-500 via-indigo-500 to-cyan-400",
      avatarSrc: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
    },
  ],
  netWorth: "$568,356.49",
  accounts: [
    {
      name: "Joint Checking",
      institution: "Apex Direct •• 4912",
      balance: "$24,850.12",
      updated: "2 minutes ago",
      iconBg: "bg-emerald-50 text-emerald-600",
      iconColor: "#059669",
    },
    {
      name: "Checking",
      institution: "Metro Reserve •• 1083",
      balance: "$12,410.80",
      updated: "14 minutes ago",
      iconBg: "bg-sky-50 text-sky-600",
      iconColor: "#0284c7",
    },
    {
      name: "401k / Index Vault",
      institution: "FinPilot Horizon •• 8820",
      balance: "$531,095.57",
      updated: "1 hour ago",
      iconBg: "bg-purple-50 text-purple-600",
      iconColor: "#7c3aed",
    },
  ],
};

export interface PlanGoal {
  id: string;
  title: string;
  current: string;
  target: string;
  percent: number;
  institution: string;
  tag: string;
  image: string;
}

export const PLAN_GOALS: PlanGoal[] = [
  {
    id: "emergency",
    title: "Emergency Fund",
    current: "$30,294.09",
    target: "$40,000.00",
    percent: 75.7,
    institution: "Apex Treasury",
    tag: "High-Yield Reserve",
    image: "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=600&auto=format&fit=crop&q=80",
  },
  {
    id: "vacation",
    title: "Vacation",
    current: "$6,589.69",
    target: "$10,000.00",
    percent: 65.8,
    institution: "Horizon Savings",
    tag: "Mediterranean Summer",
    image: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600&auto=format&fit=crop&q=80",
  },
  {
    id: "car",
    title: "Car",
    current: "$4,231.33",
    target: "$5,000.00",
    percent: 84.6,
    institution: "Auto Fund",
    tag: "Electric Sedan",
    image: "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&auto=format&fit=crop&q=80",
  },
];

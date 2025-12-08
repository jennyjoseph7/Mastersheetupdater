"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { QuickConnectCard } from "@/components/connection/quick-connect-card";
import { ConnectionsTable } from "@/components/connection/connections-table";
import { RegisterNumberDialog } from "@/components/connection/register-number-dialog";
import { EmailConnectCard } from "@/components/connection/email-connect-card";
import { EmailConnectionsTable } from "@/components/connection/email-connections-table";
import { VoiceQuickConnectCard } from "@/components/connection/voice-quick-connect-card";
import { VoiceConnectionsTable } from "@/components/connection/voice-connections-table";
import { RegisterVoiceNumberDialog } from "@/components/connection/register-voice-number-dialog";

export interface Connection {
  id: string;
  senderName: string;
  registeredNumber: string;
  provider: string;
  status: "Connected" | "Under Review" | "Error";
  channel: "WhatsApp" | "Email" | "Voice";
}

export interface EmailConnection {
  id: string;
  senderName: string;
  emailAddress: string;
  domain: string;
  type: "OAuth" | "SMTP";
  status: "Connected" | "Under Review" | "Error";
}

export interface VoiceConnection {
  id: string;
  name: string;
  number?: string;
  provider: string | string[];
  type: "Single Number" | "Number Pool";
  status: "Connected" | "Under Review" | "Error";
  poolNumbers?: string[];
}

// Mock data for demonstration
const mockConnections: Connection[] = [
  {
    id: "1",
    senderName: "InsureCorp Support",
    registeredNumber: "+91-9876543210",
    provider: "Meta",
    status: "Connected",
    channel: "WhatsApp",
  },
  {
    id: "2",
    senderName: "InsureCorp Sales",
    registeredNumber: "+91-9876543211",
    provider: "Twilio",
    status: "Under Review",
    channel: "WhatsApp",
  },
  {
    id: "3",
    senderName: "InsureCorp Alerts",
    registeredNumber: "+91-9876543212",
    provider: "Airtel",
    status: "Error",
    channel: "WhatsApp",
  },
];

const mockEmailConnections: EmailConnection[] = [
  {
    id: "1",
    senderName: "InsureCorp Support",
    emailAddress: "support@insurecorp.com",
    domain: "insurecorp.com",
    type: "OAuth",
    status: "Connected",
  },
  {
    id: "2",
    senderName: "InsureCorp Sales",
    emailAddress: "sales@insurecorp.com",
    domain: "insurecorp.com",
    type: "SMTP",
    status: "Connected",
  },
  {
    id: "3",
    senderName: "InsureCorp Marketing",
    emailAddress: "marketing@insurecorp.com",
    domain: "insurecorp.com",
    type: "OAuth",
    status: "Under Review",
  },
];

const mockVoiceConnections: VoiceConnection[] = [
  {
    id: "1",
    name: "InsureCorp Support",
    number: "+91-9876543210",
    provider: "Twilio",
    type: "Single Number",
    status: "Connected",
  },
  {
    id: "2",
    name: "Sales Team Pool",
    provider: ["Twilio", "Airtel IQ"],
    type: "Number Pool",
    status: "Connected",
    poolNumbers: ["+91-9876543215", "+91-9876543216"],
  },
  {
    id: "3",
    name: "InsureCorp Alerts",
    number: "+91-9876543217",
    provider: "Exotel",
    type: "Single Number",
    status: "Under Review",
  },
];

export default function ConnectionPage() {
  const [connections, setConnections] = useState<Connection[]>(mockConnections);
  const [emailConnections, setEmailConnections] =
    useState<EmailConnection[]>(mockEmailConnections);
  const [voiceConnections, setVoiceConnections] =
    useState<VoiceConnection[]>(mockVoiceConnections);
  const [isRegisterDialogOpen, setIsRegisterDialogOpen] = useState(false);
  const [isRegisterVoiceDialogOpen, setIsRegisterVoiceDialogOpen] =
    useState(false);
  const [activeTab, setActiveTab] = useState("whatsapp");

  const handleQuickConnect = (data: {
    number: string;
    provider: string;
    senderName: string;
  }) => {
    const newConnection: Connection = {
      id: Date.now().toString(),
      senderName: data.senderName,
      registeredNumber: data.number,
      provider: data.provider,
      status: "Under Review",
      channel: "WhatsApp",
    };
    setConnections([...connections, newConnection]);
  };

  const handleFullRegister = (data: any) => {
    const newConnection: Connection = {
      id: Date.now().toString(),
      senderName: data.displayName,
      registeredNumber: data.mobileNumber,
      provider: data.provider,
      status: "Under Review",
      channel: "WhatsApp",
    };
    setConnections([...connections, newConnection]);
    setIsRegisterDialogOpen(false);
  };

  const handleEdit = (id: string) => {
    console.log("Edit connection:", id);
  };

  const handleRemove = (id: string) => {
    setConnections(connections.filter((c) => c.id !== id));
  };

  const handleEmailConnect = (data: any) => {
    const newConnection: EmailConnection = {
      id: Date.now().toString(),
      senderName: data.fromName,
      emailAddress: data.fromEmail,
      domain: data.fromEmail.split("@")[1],
      type: "SMTP",
      status: "Under Review",
    };
    setEmailConnections([...emailConnections, newConnection]);
  };

  const handleEmailEdit = (id: string) => {
    console.log("Edit email connection:", id);
  };

  const handleEmailRemove = (id: string) => {
    setEmailConnections(emailConnections.filter((c) => c.id !== id));
  };

  const handleVoiceConnect = (data: any) => {
    const newConnection: VoiceConnection = {
      id: Date.now().toString(),
      name: data.callerName,
      number: data.phoneNumber,
      provider: data.provider,
      type: "Single Number",
      status: "Under Review",
    };
    setVoiceConnections([...voiceConnections, newConnection]);
  };

  const handleVoiceRegister = (data: any) => {
    const newConnection: VoiceConnection = {
      id: Date.now().toString(),
      name: data.callerName,
      number: data.phoneNumber,
      provider: data.provider,
      type: "Single Number",
      status: "Under Review",
    };
    setVoiceConnections([...voiceConnections, newConnection]);
    setIsRegisterVoiceDialogOpen(false);
  };

  const handleCreatePool = (data: any) => {
    const newPool: VoiceConnection = {
      id: Date.now().toString(),
      name: data.poolName,
      provider: data.selectedNumbers.map((n: any) => n.provider),
      type: "Number Pool",
      status: "Connected",
      poolNumbers: data.selectedNumbers.map((n: any) => n.number),
    };
    setVoiceConnections([...voiceConnections, newPool]);
  };

  const handleVoiceEdit = (id: string) => {
    console.log("Edit voice connection:", id);
  };

  const handleVoiceRemove = (id: string) => {
    setVoiceConnections(voiceConnections.filter((c) => c.id !== id));
  };

  const filteredConnections = connections.filter((c) => {
    if (activeTab === "whatsapp") return c.channel === "WhatsApp";
    if (activeTab === "email") return c.channel === "Email";
    if (activeTab === "voice") return c.channel === "Voice";
    return true;
  });

  return (
    <div className="flex min-h-screen flex-col">
      <div>
        <div className="flex h-20 items-center px-6 md:px-8">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Connections
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Manage your channel connections and sender IDs for WhatsApp,
              Email, SMS, and Voice campaigns.
            </p>
          </div>
        </div>
      </div>

      <main className="flex-1 p-6 md:p-8 space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-3">
            <TabsTrigger value="whatsapp">WhatsApp</TabsTrigger>
            <TabsTrigger value="email">Email</TabsTrigger>
            <TabsTrigger value="voice">Voice</TabsTrigger>
          </TabsList>

          <TabsContent value="whatsapp" className="space-y-6 mt-6">
            <QuickConnectCard onConnect={handleQuickConnect} />

            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Registered Connections</h2>
              <Button
                onClick={() => setIsRegisterDialogOpen(true)}
                className="hover:bg-purple-700 bg-primary"
              >
                <Plus className="h-4 w-4 mr-2" />
                Register New Number
              </Button>
            </div>

            <ConnectionsTable
              connections={filteredConnections}
              onEdit={handleEdit}
              onRemove={handleRemove}
            />
          </TabsContent>

          <TabsContent value="email" className="space-y-6 mt-6">
            <EmailConnectCard onConnect={handleEmailConnect} />

            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">
                Connected Email Accounts
              </h2>
            </div>

            <EmailConnectionsTable
              connections={emailConnections}
              onEdit={handleEmailEdit}
              onRemove={handleEmailRemove}
            />
          </TabsContent>

          <TabsContent value="voice" className="space-y-6 mt-6">
            <VoiceQuickConnectCard
              onConnect={handleVoiceConnect}
              onCreatePool={handleCreatePool}
              existingNumbers={voiceConnections.filter(
                (c) => c.type === "Single Number",
              )}
            />

            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Registered Connections</h2>
              <Button
                onClick={() => setIsRegisterVoiceDialogOpen(true)}
                className="hover:bg-purple-700 bg-primary"
              >
                <Plus className="h-4 w-4 mr-2" />
                Register New Number
              </Button>
            </div>

            <VoiceConnectionsTable
              connections={voiceConnections}
              onEdit={handleVoiceEdit}
              onRemove={handleVoiceRemove}
            />
          </TabsContent>
        </Tabs>
      </main>

      <RegisterNumberDialog
        open={isRegisterDialogOpen}
        onOpenChange={setIsRegisterDialogOpen}
        onSubmit={handleFullRegister}
      />

      <RegisterVoiceNumberDialog
        open={isRegisterVoiceDialogOpen}
        onOpenChange={setIsRegisterVoiceDialogOpen}
        onSubmit={handleVoiceRegister}
      />
    </div>
  );
}

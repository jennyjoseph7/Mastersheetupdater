"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Eye, Trash2, Mail, MessageSquare, Info } from "lucide-react"
import type { Template } from "@/app/template/page"
import { TemplateViewDialog } from "./template-view-dialog"
import { epochToIST, capitalize } from "@/utils/api";
interface TemplateStatusTableProps {
  templates: Template[]
  onDelete: (id: string) => void
}

export function TemplateStatusTable({ templates, onDelete }: TemplateStatusTableProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [templateToDelete, setTemplateToDelete] = useState<string | null>(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [templateToView, setTemplateToView] = useState<Template | null>(null)

  const handleDeleteClick = (id: string) => {
    setTemplateToDelete(id)
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = () => {
    if (templateToDelete) {
      onDelete(templateToDelete)
      setTemplateToDelete(null)
    }
    setDeleteDialogOpen(false)
  }

  const handleViewClick = (template: Template) => {
    setTemplateToView(template)
    setViewDialogOpen(true)
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date)
  }

  

  const getStatusBadge = (status: Template["status"]) => {
    switch (status) {
      case "Approved":
        return (
          <Badge className="bg-green-100 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400">
            Approved
          </Badge>
        )
      case "Pending":
        return (
          <Badge className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-400">
            Pending
          </Badge>
        )
      case "Rejected":
        return (
          <Badge className="bg-red-100 text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400">
            Rejected
          </Badge>
        )
    }
  }

  if (templates.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <p className="text-muted-foreground">No templates found matching your filters</p>
        </CardContent>
      </Card>
    )
  }


  return (
    <>
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Template Name / ID</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Language</TableHead>

                  <TableHead>Provider Name</TableHead>
                  {/* <TableHead>Campaign Name</TableHead> */}
                  <TableHead>Status</TableHead>
                  <TableHead>Last Updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.template_id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{template.template_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {template.template_id}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {template.channel === "WhatsApp" ? (
                          <MessageSquare className="h-4 w-4 text-green-600" />
                        ) : (
                          <Mail className="h-4 w-4 text-blue-600" />
                        )}
                        <span>{template.channel}</span>
                      </div>
                    </TableCell>
                    <TableCell>{capitalize(template.language)}</TableCell>

                    <TableCell>{capitalize(template.provider_name)}</TableCell>

                    {/* <TableCell>{template.campaignName}</TableCell> */}
                    <TableCell>
                      {(()=>{
                        const status = capitalize(template.status[0])
                        return (
                          <div className="flex items-center gap-2">
                            {getStatusBadge(status)}

                            {template.status.includes("Rejected") &&
                              template.rejectionReason && (
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-xs">
                                      <p className="text-sm">
                                        {template.rejectionReason}
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              )}
                          </div>
                        );
                      })()}
                     
                    </TableCell>

                    <TableCell className="text-muted-foreground">
                      {epochToIST(template.updated)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewClick(template)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            handleDeleteClick(template.template_id)
                          }
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Template</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this template? This action cannot
              be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {templateToView && (
        <TemplateViewDialog
          template={templateToView}
          isOpen={viewDialogOpen}
          onClose={() => {
            setViewDialogOpen(false);
            setTemplateToView(null);
          }}
        />
      )}
    </>
  );
}

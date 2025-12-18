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
import { Eye, Trash2, Mail, MessageSquare, Info, AlertCircle } from "lucide-react"
import type { Template } from "@/app/template/page"
import { TemplateViewDialog } from "./template-view-dialog"
import { epochToIST, capitalize } from "@/utils/api"

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

  const getStatusBadge = (statusInput: string | string[]) => {
    // Handle potential array or string input safely
    const status = Array.isArray(statusInput) ? statusInput[0] : statusInput;
    const normalizedStatus = capitalize(status || "");

    switch (normalizedStatus) {
      case "Approved":
        return (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 hover:bg-green-50">
            Approved
          </Badge>
        )
      case "Pending":
        return (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200 hover:bg-yellow-50">
            Pending
          </Badge>
        )
      case "Rejected":
        return (
          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 hover:bg-red-50">
            Rejected
          </Badge>
        )
      default:
        return <Badge variant="outline">{normalizedStatus}</Badge>
    }
  }

  if (templates.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <div className="rounded-full bg-muted p-4 mb-4">
            <AlertCircle className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No templates found</h3>
          <p className="text-muted-foreground max-w-sm mt-2">
            Try adjusting your search or filters, or create a new template to get started.
          </p>
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
                  <TableHead className="w-[250px]">Template Name / ID</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Language</TableHead>
                  <TableHead>Provider</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.template_id}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="font-medium truncate max-w-[200px]" title={template.template_name}>
                            {template.template_name}
                        </span>
                        <span className="text-xs text-muted-foreground font-mono truncate max-w-[200px] bg-muted px-1.5 py-0.5 rounded w-fit" title={template.template_id}>
                          {template.template_id}
                        </span>
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
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(template.status)}
                        
                        {/* Check for rejection reason */}
                        {(JSON.stringify(template.status).toLowerCase().includes("rejected") || template.status === "Rejected") &&
                          (template.rejectionReason) && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Info className="h-4 w-4 text-red-400 cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent className="max-w-xs bg-red-950 text-white border-red-800">
                                  <p className="text-xs">
                                    {template.rejectionReason}
                                  </p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
                      </div>
                    </TableCell>

                    <TableCell className="text-muted-foreground text-sm">
                      {epochToIST(template.updated)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-blue-600"
                          onClick={() => handleViewClick(template)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 hover:text-red-600"
                          onClick={() => handleDeleteClick(template.template_id)}
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
              Are you sure you want to delete <strong>{templateToDelete}</strong>? 
              This action cannot be undone and may affect active campaigns.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
            >
              Delete Template
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
  )
}